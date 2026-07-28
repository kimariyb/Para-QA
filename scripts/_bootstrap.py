"""Make the repository package importable from legacy script entry points."""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_project_root() -> None:
    """Prepend the repository root when a wrapper is executed directly."""
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
