"""Tests for the frozen evidence-corpus builder."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.corpus.evidence import build_evidence_corpus


def test_build_evidence_corpus_keeps_source_provenance(tmp_path: Path) -> None:
    source = tmp_path / "0001_cleaned.md"
    source.write_text("# Results\n\n" + "PHIP produces enhanced NMR signals. " * 12, encoding="utf-8")
    records = build_evidence_corpus(tmp_path, min_chars=50, max_chars=1000)
    assert len(records) == 1
    assert records[0]["evidence_unit_id"] == "0001:unit:0001"
    assert records[0]["context"] in source.read_text(encoding="utf-8")
    assert len(str(records[0]["source_sha256"])) == 64


if __name__ == "__main__":
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as temp_dir:
        test_build_evidence_corpus_keeps_source_provenance(Path(temp_dir))
    print("PASS test_build_evidence_corpus_keeps_source_provenance")
