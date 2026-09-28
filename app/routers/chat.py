from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import DocumentChunk
from app.retrieval.chat_chain import answer_portfolio_question
from app.retrieval.vector_store import InMemoryVectorStore
from app.schemas import ChatRequest, ChatResponse, ChatSourceOut

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    store = InMemoryVectorStore()
    for chunk in db.query(DocumentChunk).all():
        store.add(chunk.id, chunk.loan_id, chunk.page, chunk.text, chunk.embedding)

    result = answer_portfolio_question(payload.question, store)
    return ChatResponse(
        answer=result.answer,
        sources=[ChatSourceOut(loan_id=c.loan_id, page=c.page, score=c.score) for c in result.sources],
    )
