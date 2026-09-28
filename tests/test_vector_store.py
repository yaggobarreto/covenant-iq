from __future__ import annotations

import pytest

from app.retrieval.vector_store import InMemoryVectorStore, cosine_similarity


def test_cosine_similarity_identical_vectors():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_vectors():
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosine_similarity_opposite_vectors():
    assert cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)


def test_cosine_similarity_zero_vector_is_safe_not_a_div_by_zero():
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_cosine_similarity_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        cosine_similarity([1.0], [1.0, 2.0])


def test_similarity_search_ranks_closest_first():
    store = InMemoryVectorStore()
    store.add("a", "loan-1", 1, "chunk a", [1.0, 0.0])
    store.add("b", "loan-1", 2, "chunk b", [0.0, 1.0])
    store.add("c", "loan-1", 3, "chunk c", [0.9, 0.1])

    results = store.similarity_search([1.0, 0.0], k=2)

    assert [r.chunk_id for r in results] == ["a", "c"]


def test_similarity_search_respects_k():
    store = InMemoryVectorStore()
    for i in range(5):
        store.add(f"c{i}", "loan-1", i, f"chunk {i}", [1.0, 0.0])

    assert len(store.similarity_search([1.0, 0.0], k=2)) == 2


def test_similarity_search_filters_by_loan_id():
    store = InMemoryVectorStore()
    store.add("a", "loan-1", 1, "chunk a", [1.0, 0.0])
    store.add("b", "loan-2", 1, "chunk b", [1.0, 0.0])

    results = store.similarity_search([1.0, 0.0], loan_id="loan-2")

    assert [r.chunk_id for r in results] == ["b"]


def test_similarity_search_on_empty_store_returns_empty_list():
    store = InMemoryVectorStore()
    assert store.similarity_search([1.0, 0.0]) == []
