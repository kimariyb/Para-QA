"""Build a provenance-preserving retrieval corpus from cleaned literature."""

from __future__ import annotations

import hashlib
from pathlib import Path

from src.qac.generation import extract_evidence_units


def build_evidence_corpus(
    cleaned_dir: Path, min_chars: int = 200, max_chars: int = 1500
) -> list[dict[str, object]]:
    """Return deterministic evidence units for every cleaned Markdown paper."""
    records: list[dict[str, object]] = []
    for path in sorted(cleaned_dir.glob("*_cleaned.md")):
        doc_id = path.stem.removesuffix("_cleaned")
        source_text = path.read_text(encoding="utf-8")
        source_sha256 = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
        for unit in extract_evidence_units(source_text, doc_id, min_chars, max_chars):
            records.append(
                {
                    "evidence_unit_id": unit.unit_id,
                    "doc_id": unit.doc_id,
                    "section": unit.section,
                    "context": unit.text,
                    "context_start": unit.source_start,
                    "context_end": unit.source_end,
                    "source_sha256": source_sha256,
                }
            )
    return records
