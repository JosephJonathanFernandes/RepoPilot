"""Architecture detection — classifies repository structure, components, and relations."""

from __future__ import annotations

import ast
import re
from collections import defaultdict
from pathlib import Path
from typing import Optional

from repopilot.models import (
    Architecture,
    ArchitecturePattern,
    Component,
    DirectoryInfo,
    EntryPoint,
    ModuleRelation,
    RepositoryFacts,
    RepositoryInventory,
    RunInstructions,
)

PURPOSE_MAP = {
    "tests": "tests",
    "test": "tests",
    "docs": "documentation",
    "doc": "documentation",
    "services": "service",
    "service": "service",
    "api": "api",
    "routes": "routing",
    "controllers": "controller",
    "models": "model",
    "views": "view",
    "repositories": "repository",
    "utils": "utility",
    "config": "configuration",
    "components": "component",
    "pages": "page",
    "middleware": "middleware",
    "schemas": "schema",
    "database": "database",
    "db": "database",
    "store": "store",
    "hooks": "hook",
    "packages": "package",
    "apps": "app",
    "examples": "example",
    "example": "example",
    "scripts": "script",
    "script": "script",
    "tools": "tool",
    "tool": "tool",
    "benchmarks": "benchmark",
    "benchmark": "benchmark",
    ".github": "ci_config",
    "src": "source",
    "lib": "source",
    "core": "source",
}

MAX_FILE_SIZE_BYTES = 200 * 1024


def detect_architecture(
    inventory: RepositoryInventory,
    facts: RepositoryFacts,
    entrypoints: list[EntryPoint],
    run_insts: RunInstructions,
) -> Architecture:
    root = Path(inventory.root)

    # --- 1. Directory structure analysis ---
    dir_files: dict[str, list] = defaultdict(list)
    dir_source_files: dict[str, list] = defaultdict(list)

    for f in inventory.files:
        dirname = str(Path(f.path).parent).replace("\\", "/")
        if dirname == ".":
            continue
        parts = dirname.split("/")
        current = ""
        for p in parts:
            current = f"{current}/{p}" if current else p
            dir_files[current].append(f)
            if f.path in set(inventory.source_files):
                dir_source_files[current].append(f)

    directories_info = []
    for dpath, files in dir_files.items():
        basename = dpath.split("/")[-1].lower()
        purpose = PURPOSE_MAP.get(basename, "")
        directories_info.append(DirectoryInfo(
            path=dpath + "/",
            file_count=len(files),
            source_file_count=len(dir_source_files[dpath]),
            purpose_hint=purpose,
        ))

    # --- 2 & 3. Module analysis and import graph ---
    relations: list[ModuleRelation] = []
    source_file_set = set(inventory.source_files)

    for path_str in inventory.source_files:
        filepath = root / path_str
        try:
            stat = filepath.stat()
            if stat.st_size > MAX_FILE_SIZE_BYTES:
                continue
            content = filepath.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        ext = filepath.suffix

        if ext == ".py":
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            relations.append(ModuleRelation(
                                source=path_str, target=alias.name,
                                relation="imports", evidence=f"import {alias.name}",
                            ))
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            relations.append(ModuleRelation(
                                source=path_str, target=node.module,
                                relation="imports", evidence=f"from {node.module} import ...",
                            ))
            except SyntaxError:
                pass

        elif ext in (".js", ".ts", ".jsx", ".tsx"):
            import_re = re.compile(r"import\s+.*?from\s+([\"'])(.*?)\1")
            require_re = re.compile(r"require\(([\"'])(.*?)\1\)")
            for m in import_re.finditer(content):
                relations.append(ModuleRelation(
                    source=path_str, target=m.group(2), relation="imports",
                    evidence=m.group(0).strip(),
                ))
            for m in require_re.finditer(content):
                relations.append(ModuleRelation(
                    source=path_str, target=m.group(2), relation="requires",
                    evidence=m.group(0).strip(),
                ))

        elif ext == ".go":
            import_block = re.compile(r"import\s+\((.*?)\)", re.DOTALL)
            single_import = re.compile(r'import\s+"([^"]+)"')
            for m in import_block.finditer(content):
                block = m.group(1)
                for line in block.splitlines():
                    line = line.strip().strip('"')
                    if line:
                        relations.append(ModuleRelation(
                            source=path_str, target=line, relation="imports",
                            evidence=f'import "{line}"',
                        ))
            for m in single_import.finditer(content):
                relations.append(ModuleRelation(
                    source=path_str, target=m.group(1), relation="imports",
                    evidence=m.group(0).strip(),
                ))

    # Map import targets to physical file paths.
    path_map = {f.path: f.path for f in inventory.files}
    path_stem_map: dict[str, str] = {}
    for f in inventory.files:
        stem = f.path[: -len(f.extension)] if f.extension else f.path
        path_stem_map[stem.replace("/", ".")] = f.path
        path_stem_map[stem.replace("/", "/")] = f.path

    mapped_relations: list[ModuleRelation] = []
    for r in relations:
        target_path: str | None = None
        if r.target in path_stem_map:
            target_path = path_stem_map[r.target]
        elif r.target.startswith(("./", "../")):
            try:
                src_dir = root / Path(r.source).parent
                resolved = (src_dir / r.target).resolve()
                rel = resolved.relative_to(root.resolve()).as_posix()
                if rel in path_stem_map:
                    target_path = path_stem_map[rel]
                elif f"{rel}.js" in path_map:
                    target_path = f"{rel}.js"
                elif f"{rel}.ts" in path_map:
                    target_path = f"{rel}.ts"
                elif f"{rel}.py" in path_map:
                    target_path = f"{rel}.py"
            except ValueError:
                pass

        if target_path and target_path in path_map:
            mapped_relations.append(ModuleRelation(
                source=r.source, target=target_path,
                relation=r.relation, evidence=r.evidence,
            ))

    # --- 4. Component identification ---
    components: list[Component] = []
    categories_found: set[str] = set()

    for d in directories_info:
        parts = d.path.strip("/").split("/")
        if len(parts) <= 2:
            basename = parts[-1].lower()
            if basename in PURPOSE_MAP and basename not in ("src", "lib", "core"):
                purpose = PURPOSE_MAP[basename]
                components.append(Component(
                    path=d.path,
                    category=purpose,
                    confidence="MEDIUM",
                    evidence=f"Directory naming convention ('{basename}')",
                ))
                categories_found.add(basename)

    # --- 5. Architecture pattern detection ---
    patterns: list[ArchitecturePattern] = []

    is_monorepo = "packages" in categories_found or "apps" in categories_found
    if is_monorepo:
        patterns.append(ArchitecturePattern(
            name="MONOREPO", confidence="HIGH",
            evidence=["Contains packages/ or apps/ directories"],
        ))

    is_frontend = (
        ("components" in categories_found or "pages" in categories_found)
        and any(fw in facts.frameworks for fw in ("React", "Vue.js", "Angular", "Svelte", "Next.js"))
    )
    if is_frontend and not is_monorepo:
        patterns.append(ArchitecturePattern(
            name="FRONTEND",
            confidence="HIGH" if facts.frameworks else "MEDIUM",
            evidence=["Contains frontend structure and/or framework"],
        ))

    is_backend = any(cat in categories_found for cat in ("api", "routes", "controllers", "services", "models", "repositories"))
    if is_backend and not is_monorepo:
        patterns.append(ArchitecturePattern(
            name="BACKEND_API", confidence="HIGH",
            evidence=["Contains backend routing/service directories"],
        ))

    has_cli = any(
        ep.confidence == "HIGH" and ep.type in ("cli_entry", "python_script", "python_module", "go_main", "cpp_main", "java_main", "csharp_main", "rust_main")
        for ep in entrypoints
    )
    if has_cli:
        patterns.append(ArchitecturePattern(
            name="CLI_SCRIPT", confidence="HIGH",
            evidence=["Entry point analysis identified executable scripts or binaries"],
        ))

    has_lib_entry = any(ep.type == "package_entry" for ep in entrypoints)
    is_lib_manifest = ("setup.py" in facts.manifests or "Cargo.toml" in facts.manifests or "pom.xml" in facts.manifests)
    is_app_pattern = any(p.name in ("BACKEND_API", "FRONTEND") for p in patterns)
    if (has_lib_entry or (is_lib_manifest and not has_cli)) and not is_app_pattern:
        patterns.append(ArchitecturePattern(
            name="LIBRARY", confidence="MEDIUM",
            evidence=["Contains library-oriented manifest or package entry"],
        ))

    if not patterns:
        patterns.append(ArchitecturePattern(
            name="AMBIGUOUS", confidence="LOW",
            evidence=["No definitive architectural markers found"],
        ))

    return Architecture(
        directories=sorted(directories_info, key=lambda x: x.path),
        components=sorted(components, key=lambda x: x.path),
        relations=mapped_relations,
        patterns=patterns,
    )
