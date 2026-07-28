"""Validate a registered external-model run without making network calls."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

from dotenv import load_dotenv

from src.evaluation.preflight import preflight


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight an external RAG experiment.")
    parser.add_argument("--qac", required=True)
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--budget-usd", type=float, default=None)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    load_dotenv(PROJECT_ROOT / ".env")
    errors = preflight(os.environ, Path(args.qac), Path(args.corpus), args.run_id, args.budget_usd)
    report = {
        "run_id": args.run_id,
        "qac": args.qac,
        "corpus": args.corpus,
        "budget_usd": args.budget_usd,
        "ready": not errors,
        "errors": errors,
    }
    Path(args.report).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
