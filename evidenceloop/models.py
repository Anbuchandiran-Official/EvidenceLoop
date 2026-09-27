from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, model_validator


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ResearchRequest(BaseModel):
    question: str = Field(min_length=8, max_length=2000)
    start_date: date = Field(default_factory=date.today)
    end_date: date = Field(default_factory=date.today)
    memory_enabled: bool = True

    @model_validator(mode="after")
    def ordered_dates(self):
        if self.start_date > self.end_date:
            raise ValueError("Start date must precede end date")
        return self


class Plan(BaseModel):
    entities: list[str]
    subquestions: list[str]
    date_range: str
    metric_definitions: list[str]
    required_evidence: list[str]
    parallel_tasks: list[str] = Field(min_length=1, max_length=4)
    stopping_conditions: list[str]
    memory_checks: list[str] = Field(default_factory=list)


class Source(BaseModel):
    id: str
    url: str
    title: str = ""
    retrieved_at: str = Field(default_factory=now)
    published_at: str | None = None
    text: str = ""
    status: Literal["OK", "FETCH_FAILED", "BLOCKED", "UNSUPPORTED_FORMAT"] = "OK"
    error: str | None = None
    content_hash: str | None = None
    truncated: bool = False


class Calculation(BaseModel):
    operation: Literal["sum", "difference", "percent_change", "ratio"]
    inputs: list[float] = Field(min_length=2, max_length=10)
    input_source_ids: list[str] = Field(min_length=1)
    input_descriptions: list[str] = Field(min_length=2)
    result: float


class Claim(BaseModel):
    id: str
    text: str
    entity: str
    metric: str
    value: str
    unit: str
    period: str
    source_ids: list[str]
    calculation: Calculation | None = None
    importance: Literal["normal", "high"] = "normal"


class Draft(BaseModel):
    claims: list[Claim] = Field(max_length=8)
    evidence_gaps: list[str]
    coverage: str


class Judgment(BaseModel):
    verdict: Literal["SUPPORTED", "UNSUPPORTED", "CONTRADICTED"]
    source_id: str
    passage: str
    explanation: str
    mistake_type: Literal["none", "amount", "date", "entity", "citation", "stale_evidence", "metric", "unit", "calculation", "other"]
    checked_dimensions: list[str]


class Audit(BaseModel):
    claim_id: str
    verdict: Literal["SUPPORTED", "UNSUPPORTED", "CONTRADICTED"] | None = None
    verification_status: str = "VERIFIED"
    source_id: str | None = None
    passage: str = ""
    quote_verified: bool = False
    explanation: str
    mistake_type: str = "none"
    checked_dimensions: list[str] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)


class Repair(BaseModel):
    claim: Claim | None
    explanation: str
