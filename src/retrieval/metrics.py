"""Reference-evidence metrics for deterministic retrieval baselines."""

from __future__ import annotations

import math
from typing import Any

from src.retrieval.bm25 import BM25Index, RetrievalDocument


def evaluate_bm25(
    records: list[dict[str, Any]],
    corpus_records: list[dict[str, Any]] | None = None,
    ks: tuple[int, ...] = (1, 3, 5),
) -> dict[str, float | int]:
    corpus_records = corpus_records or records
    documents = {
        record["evidence_unit_id"]: RetrievalDocument(record["evidence_unit_id"], record["context"])
        for record in corpus_records
    }
    index = BM25Index(list(documents.values()))
    hits = {k: 0 for k in ks}
    reciprocal_ranks: list[float] = []
    ndcgs: list[float] = []
    for record in records:
        ranking = [document.unit_id for document, _ in index.search(record["question"], k=len(documents))]
        truth = record["evidence_unit_id"]
        rank = ranking.index(truth) + 1 if truth in ranking else None
        reciprocal_ranks.append(1 / rank if rank else 0.0)
        ndcgs.append(1 / math.log2(rank + 1) if rank else 0.0)
        for k in ks:
            hits[k] += int(rank is not None and rank <= k)
    total = len(records)
    report: dict[str, float | int] = {"queries": total, "corpus_units": len(documents), "mrr": sum(reciprocal_ranks) / max(total, 1), "ndcg": sum(ndcgs) / max(total, 1)}
    report.update({f"evidence_recall_at_{k}": hits[k] / max(total, 1) for k in ks})
    return report
