from pydantic import BaseModel, Field


class ReviewObservabilityEvent(BaseModel):
    event_type: str = Field(default="review_run_completed")
    run_id: str
    initiative_title: str
    overall_readiness: str
    elapsed_ms: int = Field(ge=0)
    team_count: int = Field(ge=0)
    concern_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    evidence_coverage: float = Field(ge=0.0, le=1.0)
    avg_confidence: float = Field(ge=0.0, le=1.0)
