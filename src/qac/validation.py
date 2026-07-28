"""Deterministic validation for evidence-grounded QAC records."""

from __future__ import annotations

import hashlib
from typing import Any

REQUIRED_FIELDS = frozenset(
    {
        "question",
        "answer",
        "context",
        "doc_id",
        "evidence_unit_id",
        "context_start",
        "context_end",
        "evidence_span",
        "evidence_start",
        "evidence_end",
        "source_sha256",
    }
)


def validate_record(record: dict[str, Any], source_text: str) -> list[str]:
    """Return deterministic provenance errors for one QAC record."""
    errors = [f"missing:{name}" for name in sorted(REQUIRED_FIELDS - record.keys())]
    if errors:
        return errors

    if hashlib.sha256(source_text.encode("utf-8")).hexdigest() != record["source_sha256"]:
        errors.append("source_sha256")

    context_start, context_end = record["context_start"], record["context_end"]
    evidence_start, evidence_end = record["evidence_start"], record["evidence_end"]
    if not (0 <= context_start <= context_end <= len(source_text)):
        errors.append("context_offsets")
    elif source_text[context_start:context_end] != record["context"]:
        errors.append("context_text")

    if not (0 <= evidence_start <= evidence_end <= len(source_text)):
        errors.append("evidence_offsets")
    elif source_text[evidence_start:evidence_end] != record["evidence_span"]:
        errors.append("evidence_text")
    elif not (context_start <= evidence_start <= evidence_end <= context_end):
        errors.append("evidence_outside_context")
    return errors
