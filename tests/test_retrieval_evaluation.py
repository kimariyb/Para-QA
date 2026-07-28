"""Tests for reference-evidence retrieval metrics."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.retrieval.metrics import evaluate_bm25


def test_evaluation_reports_perfect_retrieval() -> None:
    records = [
        {"question": "What PHIP enhancement was measured?", "evidence_unit_id": "a", "context": "PHIP enhancement was 760-fold."},
        {"question": "What does SABRE use?", "evidence_unit_id": "b", "context": "SABRE uses reversible exchange."},
    ]
    report = evaluate_bm25(records)
    assert report["queries"] == 2
    assert report["evidence_recall_at_1"] == 1.0
    assert report["mrr"] == 1.0
    assert report["ndcg"] == 1.0


def test_evaluation_accepts_separate_corpus() -> None:
    query = [{"question": "What PHIP enhancement was measured?", "evidence_unit_id": "a", "context": "PHIP enhancement was 760-fold."}]
    corpus = query + [{"question": "unused", "evidence_unit_id": "b", "context": "SABRE uses reversible exchange."}]
    report = evaluate_bm25(query, corpus)
    assert report["corpus_units"] == 2
    assert report["evidence_recall_at_1"] == 1.0


if __name__ == "__main__":
    test_evaluation_reports_perfect_retrieval()
    print("PASS test_evaluation_reports_perfect_retrieval")
    test_evaluation_accepts_separate_corpus()
    print("PASS test_evaluation_accepts_separate_corpus")
