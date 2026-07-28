"""Build the frozen full-corpus evidence index used by retrieval baselines."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.corpus.evidence import build_evidence_corpus


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an evidence corpus from cleaned Markdown.")
    parser.add_argument("--cleaned-dir", default="data/cleaned")
    parser.add_argument("--output", default="outputs/evidence_corpus.jsonl")
    parser.add_argument("--min-chars", type=int, default=200)
    parser.add_argument("--max-chars", type=int, default=1500)
    args = parser.parse_args()
    records = build_evidence_corpus(Path(args.cleaned_dir), args.min_chars, args.max_chars)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    print(json.dumps({"documents": len({r['doc_id'] for r in records}), "evidence_units": len(records)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
