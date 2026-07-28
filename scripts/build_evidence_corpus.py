"""Backward-compatible launcher for :mod:`src.cli.build_evidence_corpus`."""

from _bootstrap import ensure_project_root

ensure_project_root()
from src.cli.build_evidence_corpus import main

if __name__ == "__main__":
    raise SystemExit(main())
