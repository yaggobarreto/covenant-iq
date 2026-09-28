from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from app.extraction.llm import get_chat_model
from app.extraction.prompts import COVENANT_EXTRACTION_PROMPT
from app.extraction.schemas import CovenantExtractionResult


def build_covenant_chain(llm: BaseChatModel):
    return COVENANT_EXTRACTION_PROMPT | llm.with_structured_output(CovenantExtractionResult)


def extract_covenants(document_text: str, llm: BaseChatModel | None = None) -> CovenantExtractionResult:
    """Run the covenant-extraction chain over a credit agreement's text.

    `llm` is injectable so callers — and the test suite — can swap in a fake
    model without touching this function's logic. The API layer is the only
    caller that lets it default to a real one (see app/extraction/llm.py).
    """
    model = llm or get_chat_model()
    chain = build_covenant_chain(model)
    result = chain.invoke({"document_text": document_text})
    if not isinstance(result, CovenantExtractionResult):
        result = CovenantExtractionResult.model_validate(result)
    return result
