"""Text-embedding helper, with a dependency-free fallback.

`hash_embedding` has none of a real embedding model's semantics — it exists
so the vector-store and RAG-chain plumbing can run and be tested without an
API key. It is the default. Pass `use_real_model=True` (wired to
OPENAI_API_KEY) for retrieval quality that actually reflects meaning.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache

from app.config import settings

EMBEDDING_DIM = 256


def hash_embedding(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    vector = [0.0] * dim
    for token in text.lower().split():
        idx = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16) % dim
        vector[idx] += 1.0
    return vector


@lru_cache
def get_embeddings_model():
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set; cannot build a real embeddings model.")
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(api_key=settings.openai_api_key)


def embed_text(text: str, use_real_model: bool = False) -> list[float]:
    if use_real_model:
        return get_embeddings_model().embed_query(text)
    return hash_embedding(text)
