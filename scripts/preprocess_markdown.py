"""Backward-compatible launcher for :mod:`src.cli.preprocess_markdown`."""

from _bootstrap import ensure_project_root

ensure_project_root()
from src.cli.preprocess_markdown import main

if __name__ == "__main__":
    raise SystemExit(main())
