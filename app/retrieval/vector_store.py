"""A brute-force, in-process vector store.

This is the storage-agnostic interface the RAG chat chain depends on.
Swapping it for one backed by Postgres + pgvector — an indexed ANN search
instead of a Python loop over every row — does not require changing any code
above this boundary; see the note at the top of app/models.py.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise ValueError(f"Vectors must be the same length (got {len(a)} and {len(b)}).")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


@dataclass(frozen=True)
class ScoredChunk:
    chunk_id: str
    loan_id: str
    page: int
    text: str
    score: float


class InMemoryVectorStore:
    def __init__(self) -> None:
        self._rows: list[tuple[str, str, int, str, list[float]]] = []

    def add(self, chunk_id: str, loan_id: str, page: int, text: str, embedding: list[float]) -> None:
        self._rows.append((chunk_id, loan_id, page, text, embedding))

    def similarity_search(
        self, query_embedding: list[float], k: int = 4, loan_id: str | None = None
    ) -> list[ScoredChunk]:
        candidates = self._rows if loan_id is None else [r for r in self._rows if r[1] == loan_id]
        scored = [
            ScoredChunk(
                chunk_id=cid,
                loan_id=lid,
                page=page,
                text=text,
                score=cosine_similarity(query_embedding, embedding),
            )
            for cid, lid, page, text, embedding in candidates
        ]
        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[:k]
