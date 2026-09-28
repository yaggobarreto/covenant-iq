from __future__ import annotations

import app.routers.chat as chat_router
from app.retrieval.chat_chain import PortfolioAnswer
from app.retrieval.vector_store import ScoredChunk


def test_chat_endpoint_returns_answer_and_sources(client, monkeypatch):
    fake_answer = PortfolioAnswer(
        answer="The DSCR covenant is 1.20x. (Loan loan-1, p.2)",
        sources=[ScoredChunk(chunk_id="c1", loan_id="loan-1", page=2, text="...", score=0.93)],
    )
    monkeypatch.setattr(chat_router, "answer_portfolio_question", lambda question, store: fake_answer)

    response = client.post("/chat", json={"question": "What is the DSCR covenant?"})

    assert response.status_code == 200
    body = response.json()
    assert "DSCR" in body["answer"]
    assert body["sources"] == [{"loan_id": "loan-1", "page": 2, "score": 0.93}]


def test_chat_endpoint_with_no_documents_yet(client, monkeypatch):
    fake_answer = PortfolioAnswer(answer="I don't have any agreements to search yet.", sources=[])
    monkeypatch.setattr(chat_router, "answer_portfolio_question", lambda question, store: fake_answer)

    response = client.post("/chat", json={"question": "Anything on Loan X?"})

    assert response.status_code == 200
    assert response.json()["sources"] == []
