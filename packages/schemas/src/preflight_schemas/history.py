from datetime import datetime

from pydantic import BaseModel, Field

from .review import ReadinessStatus


class ReviewRunListItem(BaseModel):
    run_id: str
    created_at: datetime
    initiative_title: str
    overall_readiness: ReadinessStatus
    teams: list[str] = Field(default_factory=list)
    blocker_count: int = 0
    warning_count: int = 0
    requester: str | None = None
    channel_id: str | None = None
    thread_ts: str | None = None


class ReviewRunHistoryResponse(BaseModel):
    total: int
    runs: list[ReviewRunListItem] = Field(default_factory=list)


class DashboardReadinessBreakdown(BaseModel):
    green: int = 0
    yellow: int = 0
    red: int = 0


class ReviewRunDashboardResponse(BaseModel):
    total_runs: int
    readiness: DashboardReadinessBreakdown
    top_blockers: list[str] = Field(default_factory=list)
    recent_runs: list[ReviewRunListItem] = Field(default_factory=list)
