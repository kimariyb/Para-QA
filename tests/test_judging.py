"""Tests for the independent judge output contract."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import ValidationError

from src.evaluation.judging import JudgeVerdict


def test_accept_requires_all_evidence_dimensions() -> None:
    verdict = JudgeVerdict(
        answerable=True,
        evidence_supported=True,
        citation_valid=True,
        verdict="accept",
        cited_evidence_unit_ids=["0001:unit:0001"],
        reason="All answer claims occur in the cited evidence.",
    )
    assert verdict.verdict == "accept"
    try:
        JudgeVerdict(
            answerable=True, evidence_supported=False, citation_valid=True,
            verdict="accept", reason="Unsupported."
        )
        raise AssertionError("expected ValidationError")
    except ValidationError:
        pass


def test_abstain_requires_unanswerable() -> None:
    verdict = JudgeVerdict(
        answerable=False, evidence_supported=False, citation_valid=False,
        verdict="abstain", reason="The required value is absent from context."
    )
    assert verdict.verdict == "abstain"


if __name__ == "__main__":
    test_accept_requires_all_evidence_dimensions()
    print("PASS test_accept_requires_all_evidence_dimensions")
    test_abstain_requires_unanswerable()
    print("PASS test_abstain_requires_unanswerable")
