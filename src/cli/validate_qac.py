"""Validate QAC JSONL provenance against frozen cleaned source files."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from src.qac.validation import validate_record


def validate_dataset(qac_path: Path, cleaned_dir: Path) -> dict[str, object]:
    errors: Counter[str] = Counter()
    total = valid = 0
    with qac_path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            total += 1
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                errors["invalid_json"] += 1
                continue
            source_path = cleaned_dir / f"{record.get('doc_id', '')}_cleaned.md"
            if not source_path.is_file():
                errors["missing_source"] += 1
                continue
            record_errors = validate_record(record, source_path.read_text(encoding="utf-8"))
            if record_errors:
                errors.update(record_errors)
            else:
                valid += 1
    return {"total": total, "valid": valid, "invalid": total - valid, "errors": dict(errors)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate QAC provenance JSONL.")
    parser.add_argument("qac_jsonl")
    parser.add_argument("--cleaned-dir", default="data/cleaned")
    parser.add_argument("--report", default=None)
    args = parser.parse_args()
    report = validate_dataset(Path(args.qac_jsonl), Path(args.cleaned_dir))
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    if args.report:
        Path(args.report).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report["invalid"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
