"""Unit tests for the QAC v2 pipeline. Run: python tests/test_qacgen.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import ValidationError

from src.qac.generation import (
    Pipeline,
    QACandidate,
    QACConfig,
    extract_evidence_units,
    grounding_ratio,
    hygiene_errors,
    _looks_like_author_block,
)

PASSAGE = (
    "The highest experimentally obtained PH-INEPT 14N NMR signal enhancement "
    "factor for ETMA was 760, corresponding to 0.15% 14N polarization. "
    "The efficiency strongly depends on the choice of interpulse delays."
)


def test_grounding() -> None:
    verbatim = "signal enhancement factor for ETMA was 760, corresponding to 0.15% 14N polarization."
    assert grounding_ratio(verbatim, PASSAGE) >= 0.85
    paraphrase = "ETMA reached an enhancement of about seven hundred fold in the NMR experiment."
    assert grounding_ratio(paraphrase, PASSAGE) < 0.85
    assert grounding_ratio("", PASSAGE) == 0.0


def test_hygiene_rejects_old_dataset_flaws() -> None:
    # Self-reference patterns found in the v1 dataset.
    assert "self-reference" in hygiene_errors(
        "What do the authors report about the enhancement in this study?", "760-fold."
    )
    assert "self-reference" in hygiene_errors(
        "What is shown in Figure 3 of the paper?", "The pulse sequence."
    )
    assert "self-reference" in hygiene_errors(
        "What is given in Table S2?", "Concentration values."
    )
    # Non-self-contained / language / trivial-answer checks.
    assert "non-English" in hygiene_errors("什么是 PHIP 技术的主要优势？", "提高灵敏度。")
    assert "question length" in hygiene_errors("Why?", "Because.")
    assert "question mark" in hygiene_errors(
        "What is the enhancement factor for ETMA", "760."
    )
    assert "trivial answer" in hygiene_errors(
        "Is 760 the highest enhancement factor reported for ETMA?", "Yes."
    )
    # A clean pair passes.
    assert hygiene_errors(
        "What signal enhancement factor was obtained for ETMA using PH-INEPT?",
        "An enhancement factor of 760, corresponding to 0.15% 14N polarization.",
    ) == []


def test_candidate_schema() -> None:
    # Pydantic enforces the schema: missing fields and bad labels are rejected.
    try:
        QACandidate(question="q", answer="a")  # type: ignore[call-arg]
        raise AssertionError("expected ValidationError for missing fields")
    except ValidationError:
        pass
    try:
        QACandidate(
            question="q", answer="a", evidence_span="e",
            qtype="other", difficulty="easy",  # type: ignore[arg-type]
        )
        raise AssertionError("expected ValidationError for bad qtype")
    except ValidationError:
        pass
    ok = QACandidate(
        question="q", answer="a", evidence_span="e",
        qtype="factoid", difficulty="easy",
    )
    assert ok.qtype == "factoid"


def test_dedup() -> None:
    pipeline = Pipeline(model=None, config=QACConfig())
    records = [
        {"question": "What enhancement factor was obtained for ETMA?", "doc_id": "1"},
        {"question": "What enhancement factor was obtained for ETMA?", "doc_id": "2"},
        {"question": "What enhancement factor was obtained for ETMA in the study?",
         "doc_id": "3"},
        {"question": "Which catalyst gave the best polarization of ETMA?", "doc_id": "4"},
    ]
    kept = pipeline.deduplicate(records)
    questions = [r["question"] for r in kept]
    # Exact duplicate and 0.8-Jaccard near-duplicate both removed.
    assert len(kept) == 2
    assert questions[-1].startswith("Which catalyst")


def test_split_is_document_disjoint() -> None:
    pipeline = Pipeline(model=None, config=QACConfig(seed=7))
    records = [
        {"question": f"Question number {i} about topic {i % 5}?", "doc_id": f"doc{i % 6}"}
        for i in range(60)
    ]
    splits = pipeline.split_by_document(records)
    doc_sets = {name: {r["doc_id"] for r in recs} for name, recs in splits.items()}
    assert not (doc_sets["train"] & doc_sets["test"])
    assert not (doc_sets["train"] & doc_sets["dev"])
    assert not (doc_sets["dev"] & doc_sets["test"])
    assert sum(len(v) for v in splits.values()) == 60


def test_evidence_units() -> None:
    md = (
        "# A Great Paper Title\n\n"
        "Claudia Ulrich,[a] Alexei Permin,[b] Valery Petrosyan,[b] and Joachim Bargon\\*\n\n"
        "# Introduction\n\n"
        + ("Parahydrogen induced polarization enhances NMR signals dramatically. "
           "It relies on the singlet spin isomer of molecular hydrogen. " * 6)
        + "\n\n# Results\n\n"
        + ("The enhancement factor reached 760 for ETMA at 7.05 T. "
           "This corresponds to 0.15 percent polarization. " * 6)
    )
    units = extract_evidence_units(md, "0001", min_chars=200, max_chars=1500)
    assert units, "expected at least one unit"
    assert not any("Claudia Ulrich" in u.text for u in units), "author block leaked"
    sections = {u.section for u in units}
    assert "Introduction" in sections or "Results" in sections
    # Units are verbatim substrings of the source (modulo blank lines).
    for u in units:
        assert u.text.replace("\n\n", "\n")[:80].split("\n")[0][:40] in md
        assert u.unit_id.startswith("0001:unit:")
        assert md[u.source_start:u.source_end] == u.text
    assert _looks_like_author_block(
        "Claudia Ulrich,[a] Alexei Permin,[b] and Joachim Bargon\\*"
    )


def test_evidence_units_do_not_merge_across_sections() -> None:
    md = "# A\n\n" + ("First section text. " * 20) + "\n\n# B\n\n" + ("Second section text. " * 20)
    units = extract_evidence_units(md, "0002", min_chars=400, max_chars=2000)
    assert all(md[unit.source_start:unit.source_end] == unit.text for unit in units)
    assert "B" in {unit.section for unit in units}


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(tests)} tests passed.")
