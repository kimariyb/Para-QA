"""Tests for the conservative local source manifest builder."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.cli.build_source_manifest import build_record, license_status


def test_license_status_is_conservative() -> None:
    assert license_status("Open access under CC BY license.", "")[0] == "open_license"
    assert license_status("Copyright 2020 Example Publisher.", "")[0] == "restricted_or_unknown"
    assert license_status("No rights statement here.", "")[0] == "rights_unknown"


def test_record_keeps_provenance(tmp_path: Path) -> None:
    raw = tmp_path / "0001.md"
    cleaned = tmp_path / "0001_cleaned.md"
    raw.write_text("# A PHIP paper\n\nDOI: 10.1000/example.1\nCC BY 4.0", encoding="utf-8")
    cleaned.write_text("# A PHIP paper\n\nEvidence text.", encoding="utf-8")

    record = build_record(raw, cleaned)
    assert record["doi"] == "10.1000/example.1"
    assert record["title"] == "A PHIP paper"
    assert record["eligible_for_development"] is True
    assert record["eligible_for_context_release"] is True
    assert len(str(record["raw_sha256"])) == 64
    assert len(str(record["cleaned_sha256"])) == 64


if __name__ == "__main__":
    test_license_status_is_conservative()
    print("PASS test_license_status_is_conservative")
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as temp_dir:
        test_record_keeps_provenance(Path(temp_dir))
    print("PASS test_record_keeps_provenance")
