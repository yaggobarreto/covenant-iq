from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from app.extraction.llm import get_chat_model
from app.extraction.prompts import FINANCIAL_EXTRACTION_PROMPT
from app.extraction.schemas import FinancialFigures


def build_financials_chain(llm: BaseChatModel):
    return FINANCIAL_EXTRACTION_PROMPT | llm.with_structured_output(FinancialFigures)


def extract_financial_figures(
    statement_text: str,
    active_metrics: list[str],
    llm: BaseChatModel | None = None,
) -> FinancialFigures:
    """Extract only the figures the loan's currently active covenants need.

    Asking an LLM for a short, specific list of metrics is materially more
    accurate than asking it to pull "everything" out of a financial
    statement — statements vary widely in layout and language, but a metric
    the caller didn't ask for is one the model can't get wrong.
    """
    model = llm or get_chat_model()
    chain = build_financials_chain(model)
    result = chain.invoke({"statement_text": statement_text, "active_metrics": ", ".join(active_metrics)})
    if not isinstance(result, FinancialFigures):
        result = FinancialFigures.model_validate(result)
    return result
