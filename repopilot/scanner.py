"""Repository scanner — builds a structured file inventory from a repository root."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Set

from repopilot.models import RepositoryInventory, FileInfo

DEFAULT_IGNORED_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".env",
    ".clean_venv",
    ".mypy_cache",
    ".pytest_cache",
    ".tox",
    "dist",
    "build",
    ".idea",
    ".vscode",
    "benchmark_corpus",
    ".clean_venv",
}

DEFAULT_IGNORED_FILES = {
    ".DS_Store",
    "Thumbs.db",
    "*.pyc",
    "*.pyo",
    "*.pyd",
}

IMPORTANT_FILES = {
    "README.md",
    "README.rst",
    "README.txt",
    "CONTRIBUTING.md",
    "LICENSE",
    "LICENSE.txt",
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "package.json",
    "package-lock.json",
    "Dockerfile",
    "docker-compose.yml",
    "compose.yml",
    ".env.example",
    "Makefile",
    "CMakeLists.txt",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "setup.py",
    "setup.cfg",
    "Pipfile",
    "poetry.lock",
    "uv.lock",
    "yarn.lock",
    "pnpm-lock.yaml",
    "bun.lockb",
}

SOURCE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".go",
    ".rs",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".java",
    ".rb",
    ".php",
    ".cs",
    ".kt",
    ".swift",
}

CONFIG_EXTENSIONS = {".json", ".yaml", ".yml", ".toml", ".ini", ".xml", ".cfg"}

TEST_DIR_NAMES = {"test", "tests", "testing", "__tests__", "__test__"}


def _matches_ignore_pattern(name: str, patterns: Set[str]) -> bool:
    """Check a filename against glob-style ignore patterns (suffix or exact match)."""
    for pat in patterns:
        if pat.startswith("*") and name.endswith(pat[1:]):
            return True
        if name == pat:
            return True
    return False


def count_lines(filepath: Path) -> Optional[int]:
    """Count physical lines in a text file. Returns None for binary/unreadable files."""
    try:
        if filepath.is_symlink() or not filepath.is_file():
            return None

        # Read once: check for NUL bytes (binary) and count lines in one pass.
        with open(filepath, "rb") as f:
            raw = f.read()

        if b"\x00" in raw:
            return None

        text = raw.decode("utf-8", errors="replace")
        return text.count("\n") + (1 if text and not text.endswith("\n") else 0)
    except (OSError, ValueError):
        return None


def scan_repository(
    root_path: str,
    ignored_dirs: Optional[Set[str]] = None,
    ignored_files: Optional[Set[str]] = None,
) -> RepositoryInventory:
    """Scan a repository and return a structured inventory.

    Parameters
    ----------
    root_path:
        Path to the repository root.
    ignored_dirs:
        Directory names to skip (default: DEFAULT_IGNORED_DIRS).
    ignored_files:
        File names / glob patterns to skip (default: DEFAULT_IGNORED_FILES).
    """
    if ignored_dirs is None:
        ignored_dirs = DEFAULT_IGNORED_DIRS
    if ignored_files is None:
        ignored_files = DEFAULT_IGNORED_FILES

    root = Path(root_path).resolve()

    all_files: List[Path] = []
    all_dirs: List[Path] = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune ignored directories in-place so os.walk does not descend into them.
        dirnames[:] = [d for d in dirnames if d not in ignored_dirs]

        dp = Path(dirpath)
        if dp != root:
            all_dirs.append(dp)

        for f in filenames:
            if _matches_ignore_pattern(f, ignored_files):
                continue
            all_files.append(dp / f)

    # Deterministic ordering.
    all_dirs.sort()
    all_files.sort()

    dirs_rel = [d.relative_to(root).as_posix() for d in all_dirs]

    file_infos: List[FileInfo] = []
    stats: dict[str, int] = {}
    important_files: List[str] = []
    source_files: List[str] = []
    test_files: List[str] = []
    config_files: List[str] = []

    for file_path in all_files:
        rel_path_obj = file_path.relative_to(root)
        rel_path_str = rel_path_obj.as_posix()

        ext = file_path.suffix.lower()
        stats[ext] = stats.get(ext, 0) + 1

        name = file_path.name
        is_important = name in IMPORTANT_FILES
        is_source = ext in SOURCE_EXTENSIONS
        is_config = ext in CONFIG_EXTENSIONS

        name_lower = name.lower()
        is_test = (
            name_lower.startswith("test_")
            or ".test." in name_lower
            or name_lower.endswith("_test.go")
            or any(part in TEST_DIR_NAMES for part in rel_path_obj.parts)
        )

        line_count = count_lines(file_path)

        file_info = FileInfo(
            path=rel_path_str,
            extension=ext,
            is_source=is_source,
            is_test=is_test,
            is_config=is_config,
            is_important=is_important,
            line_count=line_count,
        )

        file_infos.append(file_info)

        if is_important:
            important_files.append(rel_path_str)
        if is_source:
            source_files.append(rel_path_str)
        if is_test:
            test_files.append(rel_path_str)
        if is_config:
            config_files.append(rel_path_str)

    return RepositoryInventory(
        root=str(root),
        files=file_infos,
        directories=dirs_rel,
        file_statistics=stats,
        important_files=important_files,
        source_files=source_files,
        test_files=test_files,
        config_files=config_files,
    )
