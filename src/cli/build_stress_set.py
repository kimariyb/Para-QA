"""Build deterministic stress-set JSONL from a frozen QAC JSONL split."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from src.qac.stress import (
    distractor_evidence_fixture,
    entity_perturbation,
    numeric_perturbation,
    unanswerable_fixture,
)


def build_fixtures(records: list[dict[str, object]]) -> list[dict[str, object]]:
    fixtures: list[dict[str, object]] = []
    for record in records:
        numeric = numeric_perturbation(record)
        if numeric:
            fixtures.append(numeric)
        entity = entity_perturbation(record)
        if entity:
            fixtures.append(entity)
        for distractor in records:
            fixture = distractor_evidence_fixture(record, distractor)
            if fixture:
                fixtures.append(fixture)
                break
        fixtures.append(unanswerable_fixture(record))
    return fixtures


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic QAC stress fixtures.")
    parser.add_argument("qac_jsonl")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    records = [json.loads(line) for line in Path(args.qac_jsonl).read_text(encoding="utf-8").splitlines() if line]
    fixtures = build_fixtures(records)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for fixture in fixtures:
            handle.write(json.dumps(fixture, ensure_ascii=False) + "\n")
    print(f"Wrote {len(fixtures)} fixtures to {output}")
    print(f"By type: {dict(Counter(item['fixture_type'] for item in fixtures))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
