from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class EvidenceStatus(str, Enum):
    EVIDENCE_BACKED = "evidence-backed"
    INFERRED = "inferred"
    NEEDS_CONFIRMATION = "needs confirmation"


class ReadinessStatus(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class EvidenceReference(BaseModel):
    source_type: str = Field(description="e.g., confluence, jira, roadmap")
    source_id: str = Field(description="Document/page/ticket identifier")
    excerpt: str = Field(min_length=5)


class Concern(BaseModel):
    team: str
    statement: str = Field(min_length=10)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_status: EvidenceStatus
    evidence: list[EvidenceReference] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_evidence_for_status(self) -> "Concern":
        if self.evidence_status == EvidenceStatus.EVIDENCE_BACKED and not self.evidence:
            raise ValueError(
                "evidence-backed concerns require at least one evidence reference"
            )
        return self


class AgentReview(BaseModel):
    team: str
    readiness: ReadinessStatus
    concerns: list[Concern] = Field(default_factory=list)


class ModeratorSummary(BaseModel):
    overall_readiness: ReadinessStatus
    blockers: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    questions_to_resolve: list[str] = Field(default_factory=list)
    suggested_owners: list[str] = Field(default_factory=list)
    kickoff_agenda: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ReviewRun(BaseModel):
    run_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    initiative_title: str
    requester: str | None = None
    channel_id: str | None = None
    thread_ts: str | None = None
    team_reviews: list[AgentReview] = Field(default_factory=list)
    moderator_summary: ModeratorSummary
