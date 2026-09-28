from __future__ import annotations

from app.retrieval import chat_chain
from app.retrieval.vector_store import InMemoryVectorStore
from tests.fakes import FakeInvokable, FakeMessage


def test_answer_grounds_in_the_top_retrieved_chunk_only(monkeypatch):
    store = InMemoryVectorStore()
    store.add("c1", "loan-1", 2, "DSCR covenant is 1.20x with a 30-day cure period.", [1.0, 0.0])
    store.add("c2", "loan-1", 5, "Unrelated clause about insurance requirements.", [0.0, 1.0])

    # The query embedding always matches c1 exactly — a real embedder would
    # do this based on meaning; here it's just wired for a deterministic test.
    monkeypatch.setattr(chat_chain, "embed_text", lambda text, use_real_model=False: [1.0, 0.0])

    fake_chain = FakeInvokable(FakeMessage("The DSCR covenant is 1.20x. (Loan loan-1, p.2)"))
    monkeypatch.setattr(chat_chain, "build_answer_chain", lambda llm: fake_chain)

    result = chat_chain.answer_portfolio_question("What is the DSCR covenant?", store, llm=object(), k=1)

    assert result.answer == "The DSCR covenant is 1.20x. (Loan loan-1, p.2)"
    assert [s.chunk_id for s in result.sources] == ["c1"]
    assert "DSCR covenant is 1.20x" in fake_chain.last_inputs["context"]
    assert "insurance" not in fake_chain.last_inputs["context"]


def test_answer_reports_no_excerpts_when_store_is_empty(monkeypatch):
    store = InMemoryVectorStore()
    monkeypatch.setattr(chat_chain, "embed_text", lambda text, use_real_model=False: [1.0, 0.0])

    fake_chain = FakeInvokable(FakeMessage("I don't have enough information to answer that."))
    monkeypatch.setattr(chat_chain, "build_answer_chain", lambda llm: fake_chain)

    result = chat_chain.answer_portfolio_question("Anything about Loan X?", store, llm=object())

    assert result.sources == []
    assert "no matching excerpts" in fake_chain.last_inputs["context"]
