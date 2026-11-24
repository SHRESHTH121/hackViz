"""Pydantic request/response schemas."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EMPLOYEE_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{1,31}$")
DOMAIN_RE = re.compile(r"^[a-z0-9.-]{1,255}$")
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")
LIVE_EVENT_TYPES = {"navigation", "download", "tab_activated"}
MAX_URL = 2048
MAX_META_KEYS = 20
MAX_META_VALUE = 300


def normalize_employee_id(v: str) -> str:
    v = (v or "").strip().upper()
    if not EMPLOYEE_ID_RE.match(v):
        raise ValueError("employee_id must be 2-32 chars: letters, digits, '-' or '_' (e.g. EMP011)")
    return v


def strip_url(url: str) -> str:
    """Keep scheme://host/path only - query strings and fragments can carry tokens."""
    parts = urlsplit(url.strip())
    if parts.scheme not in ("http", "https"):
        raise ValueError("only http(s) URLs are accepted")
    return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path or "/", "", ""))[:MAX_URL]


# ------------------------------------------------------------------ employees
class EmployeeCreate(BaseModel):
    employee_id: str
    name: str = Field(min_length=2, max_length=120)
    role: str = Field(min_length=2, max_length=120)
    department: str = Field(min_length=2, max_length=120)
    email: str | None = Field(default=None, max_length=254)

    @field_validator("employee_id")
    @classmethod
    def _eid(cls, v: str) -> str:
        return normalize_employee_id(v)

    @field_validator("name", "role", "department")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = " ".join(v.split())
        if len(v) < 2:
            raise ValueError("must be at least 2 characters")
        return v

    @field_validator("email", mode="before")
    @classmethod
    def _empty_email(cls, v):
        if v is None or str(v).strip() == "":
            return None
        v = str(v).strip()
        if not EMAIL_RE.match(v):
            raise ValueError("invalid email address")
        return v.lower()


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    employee_id: str
    name: str
    role: str
    department: str
    email: str | None
    profile: dict | None = None
    is_synthetic: bool
    created_at: datetime


# ------------------------------------------------------------------ activity
class ActivityIn(BaseModel):
    employee_id: str
    event_type: Literal["navigation", "download", "tab_activated"]
    url: str = Field(max_length=8192)
    domain: str | None = Field(default=None, max_length=255)
    filename: str | None = Field(default=None, max_length=1024)
    timestamp: datetime
    source: Literal["chrome_extension"] = "chrome_extension"
    client_event_id: str | None = Field(default=None, max_length=64)
    session_token: str | None = Field(default=None, max_length=64)
    metadata: dict[str, Any] | None = None

    @field_validator("employee_id")
    @classmethod
    def _eid(cls, v: str) -> str:
        return normalize_employee_id(v)

    @field_validator("url")
    @classmethod
    def _url(cls, v: str) -> str:
        return strip_url(v)

    @field_validator("filename")
    @classmethod
    def _fn(cls, v: str | None) -> str | None:
        if not v:
            return None
        base = re.split(r"[\\/]", v)[-1].strip()  # never store local directory paths
        return base[:255] or None

    @field_validator("timestamp")
    @classmethod
    def _ts(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        if (v - now).total_seconds() > 300:
            raise ValueError("timestamp is in the future")
        if (now - v).days > 30:
            raise ValueError("timestamp is older than 30 days")
        return v

    @field_validator("metadata")
    @classmethod
    def _meta(cls, v: dict | None) -> dict | None:
        if not v:
            return None
        allowed = (str, int, float, bool)
        clean: dict[str, Any] = {}
        for k, val in list(v.items())[:MAX_META_KEYS]:
            k = str(k)[:40]
            if val is None or isinstance(val, allowed):
                clean[k] = val[:MAX_META_VALUE] if isinstance(val, str) else val
            elif isinstance(val, list):
                clean[k] = [str(x)[:60] for x in val[:10]]
        return clean

    @model_validator(mode="after")
    def _domain(self):
        host = (urlsplit(self.url).hostname or "").lower()
        self.domain = (self.domain or host).lower().strip()[:255]
        if not self.domain or not DOMAIN_RE.match(self.domain):
            self.domain = host[:255] or None
        return self


class ActivityBatchIn(BaseModel):
    # Validated one by one in the route so a single malformed event cannot reject the whole batch.
    events: list[dict[str, Any]] = Field(min_length=1, max_length=100)


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    employee_id: str
    employee_name: str | None = None
    event_type: str
    domain: str | None
    url: str | None
    filename: str | None
    timestamp: datetime
    source: str
    safe_metadata: dict | None
    dataset_record_id: str | None = None
    received_at: datetime | None = None


# ------------------------------------------------------------------ anomalies
class LLMAssessment(BaseModel):
    """Exact structure required from the model. Anything else is rejected."""
    model_config = ConfigDict(extra="ignore")
    is_anomaly: bool
    risk_level: Literal["low", "medium", "high"]
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=10, max_length=4000)
    evidence_event_ids: list[int] = Field(default_factory=list, max_length=60)
    recommended_action: str = Field(min_length=5, max_length=2000)

    @field_validator("risk_level", mode="before")
    @classmethod
    def _lower(cls, v):
        return v.strip().lower() if isinstance(v, str) else v

    @model_validator(mode="after")
    def _consistent(self):
        if not self.is_anomaly and self.risk_level != "low":
            raise ValueError("is_anomaly=false requires risk_level='low'")
        if self.is_anomaly and self.risk_level == "low":
            raise ValueError("is_anomaly=true requires risk_level 'medium' or 'high'")
        return self


class AnomalyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    employee_id: str
    employee_name: str | None = None
    role: str | None = None
    department: str | None = None
    is_anomaly: bool
    risk_level: str
    confidence: float
    reason: str
    evidence_event_ids: list[int]
    recommended_action: str
    analysis_source: str
    batch_id: str
    batch_start_event_id: int | None
    batch_end_event_id: int | None
    analyzed_event_ids: list[int]
    live_events_in_batch: int
    indicators: list[dict]
    model_name: str
    validation_notes: list[str]
    duration_ms: int | None
    created_at: datetime


class PairIn(BaseModel):
    employee_id: str
    extension_version: str | None = Field(default=None, max_length=32)

    @field_validator("employee_id")
    @classmethod
    def _eid(cls, v: str) -> str:
        return normalize_employee_id(v)


class TokenIn(BaseModel):
    session_token: str = Field(min_length=8, max_length=64)
