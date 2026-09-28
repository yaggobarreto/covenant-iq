from __future__ import annotations

from dataclasses import dataclass

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from app.extraction.llm import get_chat_model
from app.retrieval.embeddings import embed_text
from app.retrieval.vector_store import InMemoryVectorStore, ScoredChunk

ANSWER_SYSTEM = """\
You are a credit portfolio assistant. Answer the user's question using ONLY \
the excerpts below, drawn from the loan agreements in the portfolio. Every \
factual claim you make about a specific loan or covenant must cite the \
excerpt it came from, in the form (Loan {{loan_id}}, p.{{page}}).

If the excerpts don't contain enough information to answer, say so plainly \
instead of guessing.

Excerpts:
{context}
"""

ANSWER_PROMPT = ChatPromptTemplate.from_messages([("system", ANSWER_SYSTEM), ("human", "{question}")])


@dataclass(frozen=True)
class PortfolioAnswer:
    answer: str
    sources: list[ScoredChunk]


def _format_context(chunks: list[ScoredChunk]) -> str:
    if not chunks:
        return "(no matching excerpts found)"
    return "\n\n".join(f"[Loan {c.loan_id}, p.{c.page}] {c.text}" for c in chunks)


def build_answer_chain(llm: BaseChatModel):
    return ANSWER_PROMPT | llm


def answer_portfolio_question(
    question: str,
    store: InMemoryVectorStore,
    llm: BaseChatModel | None = None,
    k: int = 4,
) -> PortfolioAnswer:
    """Retrieval-augmented answer over the portfolio's document chunks.

    Retrieval and generation are split on purpose: `store.similarity_search`
    is pure and independently tested (test_vector_store.py); this function's
    own test injects a fake `llm` and asserts the retrieved chunks are
    threaded into the prompt and returned as citable sources — it does not
    (and shouldn't need to) exercise real embedding or generation quality.
    """
    query_embedding = embed_text(question)
    chunks = store.similarity_search(query_embedding, k=k)

    model = llm or get_chat_model()
    chain = build_answer_chain(model)
    response = chain.invoke({"question": question, "context": _format_context(chunks)})
    text = response.content if hasattr(response, "content") else str(response)
    return PortfolioAnswer(answer=text, sources=chunks)
