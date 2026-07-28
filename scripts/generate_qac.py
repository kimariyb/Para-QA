"""Backward-compatible launcher for :mod:`src.cli.generate_qac`."""

from _bootstrap import ensure_project_root

ensure_project_root()
from src.cli.generate_qac import main

if __name__ == "__main__":
    raise SystemExit(main())
