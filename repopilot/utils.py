"""Shared utilities for RepoPilot."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Iterable

CONFIDENCE_ORDER = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "UNKNOWN": 0}

logger = logging.getLogger("repopilot")


def setup_logging(verbose: bool = False) -> None:
    """Configure package-wide logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )


def confidence_sort_key(item: Any) -> tuple[int, str]:
    """Sort key that orders items by confidence (HIGH first) then by name/path."""
    confidence = getattr(item, "confidence", "UNKNOWN")
    name = getattr(item, "path", getattr(item, "name", str(item)))
    return (-CONFIDENCE_ORDER.get(confidence, 0), str(name))


def sort_by_confidence(items: Iterable[Any]) -> list[Any]:
    """Return items sorted by confidence (HIGH first), then by path/name."""
    return sorted(items, key=confidence_sort_key)


def top_by_confidence(items: Iterable[Any], count: int = 1) -> list[Any]:
    """Return the top N items by confidence."""
    return sort_by_confidence(items)[:count]


def relative_path(path: str | Path, root: str | Path) -> str:
    """Return a POSIX-style path relative to root, best-effort."""
    try:
        return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return str(path)


def ensure_posix(path: str) -> str:
    """Normalize a path to POSIX-style separators."""
    return path.replace("\\", "/")
