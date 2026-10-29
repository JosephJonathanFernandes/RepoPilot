"""Fact extraction — derives languages, manifests, package managers, frameworks,
and dependencies from a repository inventory."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - fallback for Python < 3.11
    tomllib = None

try:
    import tomli as tomllib_fallback  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    tomllib_fallback = None

from repopilot.models import Dependency, RepositoryFacts

_TOML_LOADERS = tuple(x for x in (tomllib, tomllib_fallback) if x is not None)


def _load_toml(filepath: Path) -> dict[str, Any] | None:
    """Load a TOML file using the best available parser."""
    for loader in _TOML_LOADERS:
        try:
            with open(filepath, "rb") as f:
                return loader.load(f)
        except Exception:
            continue
    return None


def _parse_version_spec(version_raw: Any) -> str:
    """Normalize a version specifier from various manifest formats."""
    if version_raw is None:
        return ""
    if isinstance(version_raw, dict):
        return version_raw.get("version", "")
    return str(version_raw).strip()


def _parse_requirements_txt(filepath: Path, dependencies: list[Dependency], frameworks: set[str]) -> None:
    """Parse a pip requirements.txt file."""
    try:
        content = filepath.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.split("#")[0].strip()
            if not line or line.startswith(("-r", "--requirement", "-c", "--constraint")):
                continue
            # Strip environment markers and extras for the package name.
            name_part = re.split(r"[;\[\s<>=!]", line, maxsplit=1)[0].strip()
            name = name_part.lower().strip('"\'')
            if not name:
                continue
            version = line[len(name_part):].strip()
            dependencies.append(Dependency(name=name, version=version))

            if name == "fastapi":
                frameworks.add("FastAPI")
            elif name == "django":
                frameworks.add("Django")
            elif name == "flask":
                frameworks.add("Flask")
            elif name == "click":
                frameworks.add("Click")
            elif name == "pytest":
                frameworks.add("pytest")
    except OSError:
        pass


def _parse_pyproject_toml(
    filepath: Path, dependencies: list[Dependency], frameworks: set[str], package_managers: set[str]
) -> None:
    """Parse a pyproject.toml file (PEP 621 + Poetry)."""
    data = _load_toml(filepath)
    if not data:
        return

    # Poetry.
    tool = data.get("tool", {})
    if isinstance(tool, dict) and "poetry" in tool:
        package_managers.add("poetry")
        poetry = tool["poetry"]
        if isinstance(poetry, dict):
            deps = poetry.get("dependencies", {})
            for name, version in deps.items():
                if name.lower() == "python":
                    continue
                dependencies.append(Dependency(name=name.lower(), version=_parse_version_spec(version)))
                _register_framework(name.lower(), frameworks)

    # PEP 621 project.dependencies.
    project = data.get("project", {})
    if isinstance(project, dict):
        deps = project.get("dependencies", [])
        for dep_str in deps:
            match = re.match(r"^([a-zA-Z0-9.\-_]+)(.*)$", dep_str)
            if match:
                name = match.group(1).lower()
                dependencies.append(Dependency(name=name, version=match.group(2).strip()))
                _register_framework(name, frameworks)

    # PEP 621 project.scripts (used by entrypoints elsewhere).
    scripts = project.get("scripts", {})
    if isinstance(scripts, dict) and scripts:
        package_managers.add("pip")


def _parse_package_json(filepath: Path, dependencies: list[Dependency], frameworks: set[str]) -> None:
    """Parse a package.json file."""
    try:
        content = filepath.read_text(encoding="utf-8")
        data = json.loads(content)
    except (OSError, json.JSONDecodeError):
        return

    all_deps: dict[str, str] = {}
    all_deps.update(data.get("dependencies", {}))
    all_deps.update(data.get("devDependencies", {}))
    all_deps.update(data.get("peerDependencies", {}))

    for name, version in all_deps.items():
        name_lower = name.lower()
        dependencies.append(Dependency(name=name_lower, version=str(version)))
        _register_framework(name_lower, frameworks)


def _parse_cargo_toml(filepath: Path, dependencies: list[Dependency], frameworks: set[str]) -> None:
    """Parse a Cargo.toml file."""
    data = _load_toml(filepath)
    if not data:
        return
    deps = data.get("dependencies", {})
    if isinstance(deps, dict):
        for name, version in deps.items():
            dependencies.append(Dependency(name=name.lower(), version=_parse_version_spec(version)))
    frameworks.add("Rust/Cargo")


def _parse_go_mod(filepath: Path, dependencies: list[Dependency], frameworks: set[str]) -> None:
    """Parse a go.mod file (module name + require directives)."""
    try:
        content = filepath.read_text(encoding="utf-8")
    except OSError:
        return

    frameworks.add("Go modules")
    # Capture require blocks.
    require_block = re.compile(r"require\s*\((.*?)\)", re.DOTALL)
    single_require = re.compile(r"require\s+([^\s(]+)\s+([^\s]+)")
    for block in require_block.finditer(content):
        for line in block.group(1).splitlines():
            line = line.strip().strip("\t")
            m = re.match(r"^([^\s]+)\s+([^\s]+)", line)
            if m:
                dependencies.append(Dependency(name=m.group(1).lower(), version=m.group(2)))
    for m in single_require.finditer(content):
        dependencies.append(Dependency(name=m.group(1).lower(), version=m.group(2)))


def _parse_pipfile(filepath: Path, dependencies: list[Dependency], frameworks: set[str], package_managers: set[str]) -> None:
    """Parse a Pipfile (pipenv)."""
    data = _load_toml(filepath)
    if not data:
        return
    package_managers.add("pipenv")
    for section in ("packages", "dev-packages"):
        deps = data.get(section, {})
        if isinstance(deps, dict):
            for name, version in deps.items():
                dependencies.append(Dependency(name=name.lower(), version=_parse_version_spec(version)))


def _parse_setup_cfg(filepath: Path, dependencies: list[Dependency], frameworks: set[str]) -> None:
    """Parse setup.cfg for install_requires (best effort via ini-style parsing)."""
    try:
        import configparser

        parser = configparser.ConfigParser()
        parser.read(filepath, encoding="utf-8")
        if parser.has_option("options", "install_requires"):
            raw = parser.get("options", "install_requires")
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                match = re.match(r"^([a-zA-Z0-9.\-_]+)(.*)$", line)
                if match:
                    dependencies.append(Dependency(name=match.group(1).lower(), version=match.group(2).strip()))
    except Exception:
        pass


def _register_framework(name: str, frameworks: set[str]) -> None:
    """Map a dependency name to a known framework when applicable."""
    mapping = {
        "fastapi": "FastAPI",
        "django": "Django",
        "flask": "Flask",
        "click": "Click",
        "pytest": "pytest",
        "react": "React",
        "express": "Express",
        "next": "Next.js",
        "vue": "Vue.js",
        "@angular/core": "Angular",
        "svelte": "Svelte",
        "gin": "Gin",
        "cobra": "Cobra",
        "spring-boot": "Spring Boot",
        "tokio": "Tokio",
    }
    fw = mapping.get(name)
    if fw:
        frameworks.add(fw)


def extract_facts(inventory) -> RepositoryFacts:  # type: ignore[valid-type]
    """Extract ground-truth facts from a repository inventory."""
    from repopilot.models import RepositoryInventory

    inventory: RepositoryInventory
    languages: dict[str, int] = {}
    manifests: list[str] = []
    package_managers: set[str] = set()
    frameworks: set[str] = set()
    dependencies: list[Dependency] = []

    # --- 1. Languages ---
    lang_map = {
        ".py": "Python",
        ".js": "JavaScript",
        ".jsx": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".java": "Java",
        ".c": "C",
        ".cpp": "C++",
        ".cc": "C++",
        ".cxx": "C++",
        ".h": "C/C++",
        ".hpp": "C/C++",
        ".cs": "C#",
        ".go": "Go",
        ".rs": "Rust",
        ".rb": "Ruby",
        ".php": "PHP",
        ".kt": "Kotlin",
        ".swift": "Swift",
    }

    for ext, count in inventory.file_statistics.items():
        if ext in lang_map:
            lang = lang_map[ext]
            languages[lang] = languages.get(lang, 0) + count

    # --- 2. Manifests & package managers ---
    root_path = Path(inventory.root)
    root_files = {f.path for f in inventory.files if "/" not in f.path}

    def _add_manifest(name: str) -> None:
        if name not in manifests:
            manifests.append(name)

    # Python.
    if "requirements.txt" in root_files:
        _add_manifest("requirements.txt")
        package_managers.add("pip")
        _parse_requirements_txt(root_path / "requirements.txt", dependencies, frameworks)
    if "requirements-dev.txt" in root_files:
        _add_manifest("requirements-dev.txt")
        package_managers.add("pip")
    if "pyproject.toml" in root_files:
        _add_manifest("pyproject.toml")
        _parse_pyproject_toml(root_path / "pyproject.toml", dependencies, frameworks, package_managers)
    if "setup.py" in root_files:
        _add_manifest("setup.py")
        package_managers.add("pip")
    if "setup.cfg" in root_files:
        _add_manifest("setup.cfg")
        package_managers.add("pip")
        _parse_setup_cfg(root_path / "setup.cfg", dependencies, frameworks)
    if "Pipfile" in root_files:
        _add_manifest("Pipfile")
        _parse_pipfile(root_path / "Pipfile", dependencies, frameworks, package_managers)
    if "poetry.lock" in root_files:
        _add_manifest("poetry.lock")
        package_managers.add("poetry")
    if "uv.lock" in root_files:
        _add_manifest("uv.lock")
        package_managers.add("uv")

    # JavaScript / TypeScript.
    if "package.json" in root_files:
        _add_manifest("package.json")
        package_managers.add("npm")
        _parse_package_json(root_path / "package.json", dependencies, frameworks)
    if "package-lock.json" in root_files:
        _add_manifest("package-lock.json")
        package_managers.add("npm")
    if "yarn.lock" in root_files:
        _add_manifest("yarn.lock")
        package_managers.add("yarn")
    if "pnpm-lock.yaml" in root_files:
        _add_manifest("pnpm-lock.yaml")
        package_managers.add("pnpm")
    if "bun.lockb" in root_files:
        _add_manifest("bun.lockb")
        package_managers.add("bun")

    # Go.
    if "go.mod" in root_files:
        _add_manifest("go.mod")
        package_managers.add("go modules")
        _parse_go_mod(root_path / "go.mod", dependencies, frameworks)

    # Rust.
    if "Cargo.toml" in root_files:
        _add_manifest("Cargo.toml")
        package_managers.add("cargo")
        frameworks.add("Rust/Cargo")
        _parse_cargo_toml(root_path / "Cargo.toml", dependencies, frameworks)

    # Java / Maven.
    if "pom.xml" in root_files:
        _add_manifest("pom.xml")
        package_managers.add("maven")
        frameworks.add("Spring Boot")  # heuristic; refined elsewhere if needed

    # C / C++.
    if "CMakeLists.txt" in root_files:
        _add_manifest("CMakeLists.txt")

    return RepositoryFacts(
        languages=languages,
        manifests=sorted(manifests),
        package_managers=sorted(package_managers),
        frameworks=sorted(frameworks),
        dependencies=dependencies,
    )
