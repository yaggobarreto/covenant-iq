from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_db
from app.routers import chat, compliance, documents, loans


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(
    title="CovenantIQ",
    description="AI-powered covenant compliance & credit portfolio intelligence.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(loans.router)
app.include_router(documents.router)
app.include_router(compliance.router)
app.include_router(chat.router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}
