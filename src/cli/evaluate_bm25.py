"""Evaluate the deterministic BM25 baseline on a frozen QAC JSONL split."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.retrieval.metrics import evaluate_bm25


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate BM25 evidence retrieval.")
    parser.add_argument("qac_jsonl")
    parser.add_argument("--corpus", default=None,
                        help="JSONL whose contexts form the retrieval corpus; defaults to qac_jsonl.")
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    records = [json.loads(line) for line in Path(args.qac_jsonl).read_text(encoding="utf-8").splitlines() if line]
    corpus_path = Path(args.corpus) if args.corpus else Path(args.qac_jsonl)
    corpus_records = [json.loads(line) for line in corpus_path.read_text(encoding="utf-8").splitlines() if line]
    report = evaluate_bm25(records, corpus_records)
    Path(args.report).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
