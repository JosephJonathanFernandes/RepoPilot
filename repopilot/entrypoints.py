"""Entry-point detection — locates the true starting points of an application."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None

try:
    import tomli as tomllib_fallback  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    tomllib_fallback = None

from repopilot.models import EntryPoint, RepositoryFacts
from repopilot.scanner import RepositoryInventory
from repopilot.utils import ensure_posix

_TOML_LOADERS = tuple(x for x in (tomllib, tomllib_fallback) if x is not None)


def _load_toml(filepath: Path) -> dict[str, Any] | None:
    for loader in _TOML_LOADERS:
        try:
            with open(filepath, "rb") as f:
                return loader.load(f)
        except Exception:
            continue
    return None


def _is_test_or_example(path_str: str) -> bool:
    """Return True if the path implies a test, example, or docs directory/file."""
    parts = path_str.lower().split("/")
    skip = {
        "test", "tests", "testing", "__tests__", "__test__",
        "example", "examples", "demo", "demos",
        "doc", "docs", "tutorial", "tutorials",
        "node_modules", ".venv", "venv",
    }
    return any(p in skip for p in parts)


def _resolve_python_module(module_str: str, inventory: RepositoryInventory) -> str | None:
    """Attempt to resolve a Python module string (e.g. 'black', 'black.cli:main') to a file."""
    if not module_str:
        return None

    base_module = module_str.split(":")[0].split(".")[0]

    candidates = [
        f"src/{base_module}/__init__.py",
        f"src/{base_module}/__main__.py",
        f"{base_module}/__init__.py",
        f"{base_module}/__main__.py",
        f"src/{base_module}.py",
        f"{base_module}.py",
    ]

    inventory_paths = {f.path for f in inventory.files}
    for cand in candidates:
        if cand in inventory_paths:
            return cand
    return None


def _inspect_python_file(path_str: str, filepath: Path) -> list[EntryPoint]:
    eps: list[EntryPoint] = []

    if _is_test_or_example(path_str):
        return eps

    name = filepath.name

    if name in ("main.py", "app.py", "run.py", "cli.py", "__main__.py"):
        eps.append(EntryPoint(
            path=path_str,
            type="python_script",
            confidence="MEDIUM",
            reason=f"Conventional Python entry-point filename ({name})",
        ))

    try:
        content = filepath.read_text(encoding="utf-8")
        normalized = content.replace(" ", "").replace("\t", "")
        if ("if__name__=='__main__':" in normalized) or ('if__name__=="__main__":' in normalized):
            eps.append(EntryPoint(
                path=path_str,
                type="python_module",
                confidence="HIGH",
                reason="Contains __main__ execution entry point",
            ))
    except OSError:
        pass

    return eps


def _inspect_go_file(path_str: str, filepath: Path) -> list[EntryPoint]:
    if _is_test_or_example(path_str):
        return []
    try:
        content = filepath.read_text(encoding="utf-8")
        if "package main" in content and "func main(" in content:
            return [EntryPoint(
                path=path_str,
                type="go_main",
                confidence="HIGH",
                reason="Go file with package main and func main()",
            )]
    except OSError:
        pass
    return []


def _inspect_c_cpp_file(path_str: str, filepath: Path) -> list[EntryPoint]:
    if _is_test_or_example(path_str):
        return []
    try:
        content = filepath.read_text(encoding="utf-8")
        if re_contains_main(content):
            return [EntryPoint(
                path=path_str,
                type="cpp_main",
                confidence="HIGH",
                reason="C/C++ file containing int main()",
            )]
    except OSError:
        pass
    return []


def re_contains_main(content: str) -> bool:
    return "int main(" in content


def _inspect_java_file(path_str: str, filepath: Path) -> list[EntryPoint]:
    if _is_test_or_example(path_str):
        return []
    try:
        content = filepath.read_text(encoding="utf-8")
        if "public static void main(" in content:
            return [EntryPoint(
                path=path_str,
                type="java_main",
                confidence="HIGH",
                reason="Java file containing public static void main()",
            )]
    except OSError:
        pass
    return []


def _inspect_csharp_file(path_str: str, filepath: Path) -> list[EntryPoint]:
    if _is_test_or_example(path_str):
        return []
    try:
        content = filepath.read_text(encoding="utf-8")
        if "static void Main(" in content or "static int Main(" in content:
            return [EntryPoint(
                path=path_str,
                type="csharp_main",
                confidence="HIGH",
                reason="C# file containing Main()",
            )]
    except OSError:
        pass
    return []


def _inspect_rust_file(path_str: str, filepath: Path) -> list[EntryPoint]:
    if _is_test_or_example(path_str):
        return []
    try:
        content = filepath.read_text(encoding="utf-8")
        if "fn main(" in content:
            return [EntryPoint(
                path=path_str,
                type="rust_main",
                confidence="HIGH",
                reason="Rust file containing fn main()",
            )]
    except OSError:
        pass
    return []


def detect_entrypoints(inventory: RepositoryInventory, facts: RepositoryFacts) -> list[EntryPoint]:
    entrypoints: list[EntryPoint] = []
    root_path = Path(inventory.root)

    # --- 1. Manifest-based entry points ---
    if "package.json" in facts.manifests:
        pkg_path = root_path / "package.json"
        if pkg_path.exists():
            try:
                data = json.loads(pkg_path.read_text(encoding="utf-8"))

                def _add_pkg_entry(rel_path: str, ep_type: str, reason: str) -> None:
                    if rel_path.startswith("./"):
                        rel_path = rel_path[2:]
                    rel_path = ensure_posix(rel_path)
                    is_observed = (root_path / rel_path).is_file()
                    entrypoints.append(EntryPoint(
                        path=rel_path,
                        type=ep_type,
                        confidence="HIGH",
                        reason=reason,
                        existence="OBSERVED" if is_observed else "REFERENCED",
                    ))
                    if not is_observed and any(rel_path.startswith(p) for p in ("dist/", "build/", "lib/")):
                        base_name = rel_path.split("/")[-1]
                        if base_name.endswith(".js"):
                            base_no_ext = base_name[:-3]
                            for src_cand in (f"src/{base_no_ext}.ts", f"src/{base_no_ext}.js"):
                                if (root_path / src_cand).is_file():
                                    entrypoints.append(EntryPoint(
                                        path=src_cand,
                                        type="source_entry",
                                        confidence="HIGH",
                                        reason=f"Resolved source file for built artifact {rel_path}",
                                        existence="OBSERVED",
                                    ))
                                    break

                if "main" in data and isinstance(data["main"], str):
                    _add_pkg_entry(data["main"], "package_entry", 'package.json specifies "main" entry point')
                if "bin" in data:
                    bin_data = data["bin"]
                    if isinstance(bin_data, str):
                        _add_pkg_entry(bin_data, "cli_entry", 'package.json specifies "bin" CLI entry point')
                    elif isinstance(bin_data, dict):
                        for bin_path in bin_data.values():
                            if isinstance(bin_path, str):
                                _add_pkg_entry(bin_path, "cli_entry", 'package.json specifies "bin" CLI entry point')
            except (OSError, json.JSONDecodeError):
                pass

    if "pyproject.toml" in facts.manifests:
        pyproj_path = root_path / "pyproject.toml"
        if pyproj_path.exists():
            try:
                data = _load_toml(pyproj_path)
                if not data:
                    raise ValueError("empty pyproject.toml")

                script_pointers: list[str] = []
                project = data.get("project", {})
                if isinstance(project, dict):
                    scripts = project.get("scripts", {})
                    if isinstance(scripts, dict):
                        script_pointers.extend(str(v) for v in scripts.values())

                tool = data.get("tool", {})
                if isinstance(tool, dict):
                    poetry = tool.get("poetry", {})
                    if isinstance(poetry, dict):
                        poetry_scripts = poetry.get("scripts", {})
                        if isinstance(poetry_scripts, dict):
                            script_pointers.extend(str(v) for v in poetry_scripts.values())

                if script_pointers:
                    resolved_any = False
                    for pointer in script_pointers:
                        resolved_path = _resolve_python_module(pointer, inventory)
                        if resolved_path:
                            resolved_any = True
                            entrypoints.append(EntryPoint(
                                path=resolved_path,
                                type="python_script",
                                confidence="HIGH",
                                reason=f"Resolved pyproject.toml script pointer ({pointer})",
                            ))
                    if not resolved_any:
                        entrypoints.append(EntryPoint(
                            path="pyproject.toml",
                            type="cli_entry",
                            confidence="HIGH",
                            reason='pyproject.toml defines console scripts',
                        ))
            except Exception:
                pass

    # --- 2. File-based entry points ---
    for file_info in inventory.files:
        path_str = file_info.path
        filepath = root_path / path_str
        ext = file_info.extension
        name = filepath.name

        if name == "Dockerfile":
            try:
                content = filepath.read_text(encoding="utf-8")
                if "ENTRYPOINT" in content or "CMD" in content:
                    entrypoints.append(EntryPoint(
                        path=path_str,
                        type="docker_entrypoint",
                        confidence="HIGH",
                        reason="Dockerfile contains ENTRYPOINT or CMD instruction",
                    ))
            except OSError:
                pass

        elif ext == ".py":
            entrypoints.extend(_inspect_python_file(path_str, filepath))

        elif ext in (".js", ".ts"):
            if not _is_test_or_example(path_str):
                if path_str in ("index.js", "index.ts", "src/index.js", "src/index.ts"):
                    entrypoints.append(EntryPoint(
                        path=path_str,
                        type=f"{'javascript' if ext == '.js' else 'typescript'}_entry",
                        confidence="MEDIUM",
                        reason="Conventional JS/TS entry-point filename",
                    ))

        elif ext == ".go":
            entrypoints.extend(_inspect_go_file(path_str, filepath))

        elif ext == ".rs":
            entrypoints.extend(_inspect_rust_file(path_str, filepath))

        elif ext in (".c", ".cpp", ".cc", ".cxx"):
            entrypoints.extend(_inspect_c_cpp_file(path_str, filepath))

        elif ext == ".java":
            entrypoints.extend(_inspect_java_file(path_str, filepath))

        elif ext == ".cs":
            entrypoints.extend(_inspect_csharp_file(path_str, filepath))

    # --- Deduplicate: prefer HIGH confidence ---
    final_eps: dict[tuple[str, str], EntryPoint] = {}
    for ep in entrypoints:
        key = (ep.path, ep.type)
        existing = final_eps.get(key)
        if not existing:
            final_eps[key] = ep
        elif existing.confidence != "HIGH" and ep.confidence == "HIGH":
            final_eps[key] = ep

    return sorted(list(final_eps.values()), key=lambda e: (e.confidence, e.path, e.type))
