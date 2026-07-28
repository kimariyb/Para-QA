"""Deterministic stress fixtures for evidence-grounded QAC evaluation."""

from __future__ import annotations

import hashlib
import re
from typing import Any

NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")
ENTITY_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9-]{2,}\b")


def numeric_perturbation(record: dict[str, Any]) -> dict[str, Any] | None:
    """Create a wrong numeric answer with a rule-defined reject outcome."""
    match = NUMBER_RE.search(str(record.get("answer", "")))
    if not match:
        return None
    value = match.group(0)
    replacement = str(float(value) + 1).rstrip("0").rstrip(".")
    wrong_answer = f"{record['answer'][:match.start()]}{replacement}{record['answer'][match.end():]}"
    return {
        "fixture_id": f"{record.get('id', 'unknown')}:numeric",
        "fixture_type": "numeric_perturbation",
        "source_qac_id": record.get("id"),
        "question": record["question"],
        "context": record["context"],
        "candidate_answer": wrong_answer,
        "expected_outcome": "reject",
        "rule": f"replaced answer number {value} with {replacement}",
    }


def unanswerable_fixture(record: dict[str, Any]) -> dict[str, Any]:
    """Create a nonce question whose answer is provably absent from its context."""
    digest = hashlib.sha256(str(record.get("id", record["question"])).encode()).hexdigest()[:12]
    nonce = f"PHIP-CONTROL-{digest}"
    if nonce in record["context"]:
        raise ValueError("Generated nonce unexpectedly occurs in context")
    return {
        "fixture_id": f"{record.get('id', 'unknown')}:unanswerable",
        "fixture_type": "unanswerable_nonce",
        "source_qac_id": record.get("id"),
        "question": f"What value is assigned to {nonce} in the source?",
        "context": record["context"],
        "candidate_answer": None,
        "expected_outcome": "abstain",
        "rule": "question contains a deterministic nonce absent from context",
    }


def entity_perturbation(record: dict[str, Any]) -> dict[str, Any] | None:
    """Replace an answer entity found in context with a source-absent nonce."""
    context = record["context"]
    for match in ENTITY_RE.finditer(record["answer"]):
        entity = match.group(0)
        if entity.lower() in {"the", "and", "was", "with", "for"} or entity not in context:
            continue
        nonce = f"PHIP-ENTITY-{hashlib.sha256(entity.encode()).hexdigest()[:8]}"
        if nonce in context:
            raise ValueError("Generated entity nonce unexpectedly occurs in context")
        answer = f"{record['answer'][:match.start()]}{nonce}{record['answer'][match.end():]}"
        return {
            "fixture_id": f"{record.get('id', 'unknown')}:entity",
            "fixture_type": "entity_perturbation",
            "source_qac_id": record.get("id"),
            "question": record["question"],
            "context": context,
            "candidate_answer": answer,
            "expected_outcome": "reject",
            "rule": f"replaced evidence entity {entity} with source-absent nonce",
        }
    return None


def distractor_evidence_fixture(
    record: dict[str, Any], distractor: dict[str, Any]
) -> dict[str, Any] | None:
    """Replace source evidence with another document's non-supporting context."""
    context = str(distractor.get("context", ""))
    span = str(record.get("evidence_span", record.get("answer", "")))
    if not context or record.get("doc_id") == distractor.get("doc_id") or span in context:
        return None
    return {
        "fixture_id": f"{record.get('id', 'unknown')}:distractor:{distractor.get('id', 'unknown')}",
        "fixture_type": "distractor_evidence",
        "source_qac_id": record.get("id"),
        "distractor_qac_id": distractor.get("id"),
        "question": record["question"],
        "context": context,
        "candidate_answer": None,
        "expected_outcome": "abstain",
        "rule": "source evidence span is absent from an unrelated document context",
    }
