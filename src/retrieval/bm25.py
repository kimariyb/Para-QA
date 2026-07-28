"""Dependency-free BM25 baseline for frozen evidence units."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


@dataclass(frozen=True)
class RetrievalDocument:
    unit_id: str
    text: str


class BM25Index:
    def __init__(self, documents: list[RetrievalDocument], k1: float = 1.5, b: float = 0.75) -> None:
        self.documents = documents
        self.k1 = k1
        self.b = b
        self.term_counts = [Counter(tokenize(document.text)) for document in documents]
        self.lengths = [sum(counts.values()) for counts in self.term_counts]
        self.avg_length = sum(self.lengths) / max(len(self.lengths), 1)
        self.doc_frequency = Counter(
            term for counts in self.term_counts for term in counts
        )

    def search(self, query: str, k: int = 5) -> list[tuple[RetrievalDocument, float]]:
        terms = set(tokenize(query))
        total = len(self.documents)
        scored = []
        for document, counts, length in zip(self.documents, self.term_counts, self.lengths):
            score = 0.0
            for term in terms:
                frequency = counts[term]
                if not frequency:
                    continue
                idf = math.log(1 + (total - self.doc_frequency[term] + 0.5) / (self.doc_frequency[term] + 0.5))
                denominator = frequency + self.k1 * (1 - self.b + self.b * length / max(self.avg_length, 1))
                score += idf * frequency * (self.k1 + 1) / denominator
            scored.append((document, score))
        return sorted(scored, key=lambda item: (-item[1], item[0].unit_id))[:k]
