"""Tests for deterministic QAC provenance validation."""

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.qac.validation import validate_record


SOURCE = "Title\n\nThe enhancement was 760-fold at 7 T.\n"
START = SOURCE.index("The enhancement")
END = START + len("The enhancement was 760-fold at 7 T.")
SPAN = "760-fold"
SPAN_START = SOURCE.index(SPAN)


def record() -> dict[str, object]:
    return {
        "question": "What enhancement was reported?",
        "answer": "760-fold.",
        "context": SOURCE[START:END],
        "doc_id": "0001",
        "evidence_unit_id": "0001:unit:0001",
        "context_start": START,
        "context_end": END,
        "evidence_span": SPAN,
        "evidence_start": SPAN_START,
        "evidence_end": SPAN_START + len(SPAN),
        "source_sha256": hashlib.sha256(SOURCE.encode("utf-8")).hexdigest(),
    }


def test_valid_record() -> None:
    assert validate_record(record(), SOURCE) == []


def test_detects_tampered_evidence() -> None:
    candidate = record()
    candidate["evidence_span"] = "700-fold"
    assert "evidence_text" in validate_record(candidate, SOURCE)


def test_detects_missing_provenance() -> None:
    candidate = record()
    del candidate["source_sha256"]
    assert validate_record(candidate, SOURCE) == ["missing:source_sha256"]


if __name__ == "__main__":
    for name, value in sorted(globals().items()):
        if name.startswith("test_"):
            value()
            print(f"PASS {name}")
