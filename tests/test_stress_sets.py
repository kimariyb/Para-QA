"""Tests for deterministic automated stress fixtures."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.qac.stress import (
    distractor_evidence_fixture,
    entity_perturbation,
    numeric_perturbation,
    unanswerable_fixture,
)
from src.cli.build_stress_set import build_fixtures

RECORD = {
    "id": "qac-test-00001",
    "question": "What enhancement was measured?",
    "answer": "The enhancement was 760-fold.",
    "context": "The enhancement was 760-fold at 7 T.",
}


def test_numeric_perturbation_is_wrong() -> None:
    fixture = numeric_perturbation(RECORD)
    assert fixture is not None
    assert fixture["expected_outcome"] == "reject"
    assert fixture["candidate_answer"] == "The enhancement was 761-fold."


def test_unanswerable_nonce_is_absent() -> None:
    fixture = unanswerable_fixture(RECORD)
    assert fixture["expected_outcome"] == "abstain"
    assert fixture["question"].split()[4] not in fixture["context"]


def test_entity_perturbation_is_absent_from_context() -> None:
    fixture = entity_perturbation(RECORD)
    assert fixture is not None
    assert fixture["expected_outcome"] == "reject"
    assert "PHIP-ENTITY-" in fixture["candidate_answer"]
    assert "PHIP-ENTITY-" not in fixture["context"]


def test_distractor_evidence_requires_abstention() -> None:
    distractor = {"id": "qac-test-00002", "doc_id": "0002", "context": "A catalyst was tested at 298 K."}
    fixture = distractor_evidence_fixture({**RECORD, "doc_id": "0001", "evidence_span": "760-fold"}, distractor)
    assert fixture is not None
    assert fixture["expected_outcome"] == "abstain"
    assert fixture["distractor_qac_id"] == "qac-test-00002"


def test_build_fixtures_preserves_source_ids() -> None:
    fixtures = build_fixtures([RECORD])
    assert {fixture["fixture_type"] for fixture in fixtures} == {
        "numeric_perturbation", "entity_perturbation", "unanswerable_nonce"
    }
    assert all(fixture["source_qac_id"] == RECORD["id"] for fixture in fixtures)


if __name__ == "__main__":
    test_numeric_perturbation_is_wrong()
    print("PASS test_numeric_perturbation_is_wrong")
    test_unanswerable_nonce_is_absent()
    print("PASS test_unanswerable_nonce_is_absent")
    test_entity_perturbation_is_absent_from_context()
    print("PASS test_entity_perturbation_is_absent_from_context")
    test_distractor_evidence_requires_abstention()
    print("PASS test_distractor_evidence_requires_abstention")
    test_build_fixtures_preserves_source_ids()
    print("PASS test_build_fixtures_preserves_source_ids")
