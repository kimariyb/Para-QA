"""Backward-compatible launcher for :mod:`src.cli.mineru_batch`."""

from _bootstrap import ensure_project_root

ensure_project_root()
from src.cli.mineru_batch import main

if __name__ == "__main__":
    raise SystemExit(main())
