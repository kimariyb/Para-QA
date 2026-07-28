"""Tests for the deterministic BM25 baseline."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.retrieval.bm25 import BM25Index, RetrievalDocument, tokenize


def test_tokenize() -> None:
    assert tokenize("PHIP at 7 T") == ["phip", "at", "7", "t"]


def test_bm25_prefers_matching_evidence() -> None:
    index = BM25Index([
        RetrievalDocument("a", "PHIP enhancement was measured at 7 T."),
        RetrievalDocument("b", "SABRE transfers polarization through reversible exchange."),
    ])
    result = index.search("What PHIP enhancement was measured?", k=1)
    assert result[0][0].unit_id == "a"
    assert result[0][1] > 0


if __name__ == "__main__":
    test_tokenize()
    print("PASS test_tokenize")
    test_bm25_prefers_matching_evidence()
    print("PASS test_bm25_prefers_matching_evidence")
