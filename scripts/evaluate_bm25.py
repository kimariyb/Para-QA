"""Backward-compatible launcher for :mod:`src.cli.evaluate_bm25`."""

from _bootstrap import ensure_project_root

ensure_project_root()
from src.cli.evaluate_bm25 import main

if __name__ == "__main__":
    raise SystemExit(main())
