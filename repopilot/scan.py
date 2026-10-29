"""Backwards-compatible entry point that delegates to the unified CLI."""

from __future__ import annotations

import sys

from repopilot.cli import main

if __name__ == "__main__":
    sys.exit(main())
