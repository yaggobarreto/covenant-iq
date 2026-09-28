"""SQLAlchemy ORM models.

DocumentChunk.embedding is stored as a JSON list of floats. On SQLite (the
default, used for local dev and the test suite) similarity search runs in
Python over these lists — see app/retrieval/vector_store.py. Pointing
DATABASE_URL at Postgres with the pgvector extension lets the same schema
back a real `vector` column without changing any application code above the
storage boundary; swapping in pgvector's indexed search there is a follow-up,
not a rewrite.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    # A Python-side, microsecond-resolution default. SQLite's own
    # CURRENT_TIMESTAMP only has 1-second resolution, which is too coarse to
    # reliably order two ComplianceResult rows written a few milliseconds
    # apart — and "which snapshot is latest" is exactly what the portfolio
    # summary and trend detector depend on.
    return datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC, matching the DateTime column


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    borrower_name: Mapped[str] = mapped_column(String(255))
    sector: Mapped[str | None] = mapped_column(String(120), nullable=True)
    principal: Mapped[float] = mapped_column(Float)
    interest_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    maturity_date: Mapped[str | None] = mapped_column(String(10), nullable=True)  # ISO date
    agreement_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    instrument_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    covenants: Mapped[list["Covenant"]] = relationship(back_populates="loan", cascade="all, delete-orphan")
    snapshots: Mapped[list["FinancialSnapshot"]] = relationship(back_populates="loan", cascade="all, delete-orphan")
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="loan", cascade="all, delete-orphan")


class Covenant(Base):
    __tablename__ = "covenants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    loan_id: Mapped[str] = mapped_column(ForeignKey("loans.id"))
    name: Mapped[str] = mapped_column(String(255))
    metric: Mapped[str] = mapped_column(String(60))
    operator: Mapped[str] = mapped_column(String(3))  # "lte" or "gte"
    threshold: Mapped[float] = mapped_column(Float)
    test_frequency: Mapped[str] = mapped_column(String(20), default="quarterly")
    cure_period_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_clause: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed: Mapped[bool] = mapped_column(default=False)

    loan: Mapped[Loan] = relationship(back_populates="covenants")
    results: Mapped[list["ComplianceResult"]] = relationship(back_populates="covenant", cascade="all, delete-orphan")


class FinancialSnapshot(Base):
    __tablename__ = "financial_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    loan_id: Mapped[str] = mapped_column(ForeignKey("loans.id"))
    period_label: Mapped[str] = mapped_column(String(20))  # e.g. "2026-Q2"
    figures: Mapped[dict] = mapped_column(JSON)  # {"net_debt_ebitda": 2.41, ...}
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    loan: Mapped[Loan] = relationship(back_populates="snapshots")


class ComplianceResult(Base):
    """Append-only: never update a row after it's written, only add new ones."""

    __tablename__ = "compliance_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    covenant_id: Mapped[str] = mapped_column(ForeignKey("covenants.id"))
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("financial_snapshots.id"))
    actual_value: Mapped[float] = mapped_column(Float)
    headroom_pct: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20))  # compliant | warning | breach
    trend: Mapped[str | None] = mapped_column(String(20), nullable=True)  # improving | stable | shrinking
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    covenant: Mapped[Covenant] = relationship(back_populates="results")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    loan_id: Mapped[str] = mapped_column(ForeignKey("loans.id"))
    page: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list] = mapped_column(JSON)  # list[float]

    loan: Mapped[Loan] = relationship(back_populates="chunks")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    covenant_id: Mapped[str] = mapped_column(ForeignKey("covenants.id"))
    compliance_result_id: Mapped[str] = mapped_column(ForeignKey("compliance_results.id"))
    trigger_reason: Mapped[str] = mapped_column(String(255))
    fired_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    acknowledged_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
