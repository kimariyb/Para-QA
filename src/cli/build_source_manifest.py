"""Build a conservative provenance manifest for the PHIP/SABRE corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:a-z0-9]+", re.IGNORECASE)
CC_BY_RE = re.compile(
    r"(?:creative\s+commons|open\s+access)\s+(?:under\s+)?cc\s*by"
    r"|cc\s*by(?:[- ](?:nc|sa|nd))*", re.IGNORECASE
)
COPYRIGHT_RE = re.compile(r"\bcopyright\b|\ball rights reserved\b|\b©\b", re.IGNORECASE)
HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def first_match(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    return match.group(0).strip() if match else None


def title_from_markdown(text: str) -> str | None:
    match = HEADING_RE.search(text)
    return match.group(1).strip() if match else None


def license_status(raw_text: str, cleaned_text: str) -> tuple[str, str | None]:
    text = f"{raw_text}\n{cleaned_text}"
    license_evidence = first_match(CC_BY_RE, text)
    if license_evidence:
        return "open_license", license_evidence
    copyright_evidence = first_match(COPYRIGHT_RE, text)
    if copyright_evidence:
        return "restricted_or_unknown", copyright_evidence
    return "rights_unknown", None


def build_record(raw_path: Path, cleaned_path: Path | None) -> dict[str, object]:
    raw_text = raw_path.read_text(encoding="utf-8")
    cleaned_text = cleaned_path.read_text(encoding="utf-8") if cleaned_path else ""
    status, evidence = license_status(raw_text, cleaned_text)
    return {
        "doc_id": raw_path.stem,
        "title": title_from_markdown(cleaned_text or raw_text),
        "doi": first_match(DOI_RE, raw_text) or first_match(DOI_RE, cleaned_text),
        "raw_path": str(raw_path),
        "cleaned_path": str(cleaned_path) if cleaned_path else None,
        "raw_sha256": sha256(raw_path),
        "cleaned_sha256": sha256(cleaned_path) if cleaned_path else None,
        "license_status": status,
        "license_evidence": evidence,
        "eligible_for_development": cleaned_path is not None,
        "eligible_for_context_release": status == "open_license" and cleaned_path is not None,
        "discipline_tags": [],
        "review_status": "needs_source_metadata",
    }


def build_manifest(raw_dir: Path, cleaned_dir: Path) -> list[dict[str, object]]:
    records = []
    for raw_path in sorted(raw_dir.glob("*.md")):
        cleaned_path = cleaned_dir / f"{raw_path.stem}_cleaned.md"
        records.append(build_record(raw_path, cleaned_path if cleaned_path.exists() else None))
    return records


def write_jsonl(records: list[dict[str, object]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a conservative source and rights manifest from Markdown files."
    )
    parser.add_argument("--raw-dir", default="data/markdown")
    parser.add_argument("--cleaned-dir", default="data/cleaned")
    parser.add_argument("--output", default="outputs/source_manifest.jsonl")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    records = build_manifest(Path(args.raw_dir), Path(args.cleaned_dir))
    write_jsonl(records, Path(args.output))
    summary = Counter(record["license_status"] for record in records)
    development = sum(bool(record["eligible_for_development"]) for record in records)
    eligible = sum(bool(record["eligible_for_context_release"]) for record in records)
    print(f"Wrote {len(records)} records to {args.output}")
    print(f"License status: {dict(summary)}")
    print(f"Eligible for internal development: {development}")
    print(f"Eligible for context release: {eligible}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
