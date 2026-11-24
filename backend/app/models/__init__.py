"""SQLAlchemy ORM models."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text,
                        UniqueConstraint)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

SOURCE_HISTORICAL = "historical_cert"
SOURCE_LIVE = "chrome_extension"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(120), nullable=False)
    department: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    profile: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    activities = relationship("ActivityLog", back_populates="employee", lazy="noload")


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    __table_args__ = (
        Index("ix_activity_emp_ts", "employee_id", "timestamp"),
        Index("ix_activity_emp_source_id", "employee_id", "source", "id"),
        UniqueConstraint("client_event_id", name="uq_activity_client_event_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.employee_id", ondelete="CASCADE"),
                                             nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    safe_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # extension-generated UUID used to drop duplicate transmissions (NULL for historical rows)
    client_event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # stable identifier of the synthetic record (e.g. H000123) for historical rows
    dataset_record_id: Mapped[str | None] = mapped_column(String(16), nullable=True, unique=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    employee = relationship("Employee", back_populates="activities", lazy="noload")


class Anomaly(Base):
    """One saved LLM assessment (anomalous or not) of a batch of activity."""
    __tablename__ = "anomalies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.employee_id", ondelete="CASCADE"),
                                             nullable=False, index=True)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(8), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_event_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    analysis_source: Mapped[str] = mapped_column(String(16), nullable=False)  # auto_batch | manual
    batch_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    batch_start_event_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    batch_end_event_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    analyzed_event_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    live_events_in_batch: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    indicators: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_notes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False,
                                                 index=True)


class AnalysisState(Base):
    """Per-employee analysis cursor. Only advanced after a successful, saved analysis."""
    __tablename__ = "analysis_state"

    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.employee_id", ondelete="CASCADE"),
                                             primary_key=True)
    last_analyzed_event_id: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ExtensionSession(Base):
    """A Chrome extension pairing. Pairing is tracked separately from event transmission."""
    __tablename__ = "extension_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.employee_id", ondelete="CASCADE"),
                                             nullable=False, index=True)
    paired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    events_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extension_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    disconnected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
