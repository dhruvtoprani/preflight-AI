from pydantic import BaseModel, Field


class InitiativeBrief(BaseModel):
    title: str = Field(min_length=5, max_length=200)
    problem_statement: str = Field(min_length=20)
    proposed_solution: str = Field(min_length=20)
    target_timeline: str = Field(min_length=2, max_length=100)
    affected_teams: list[str] = Field(default_factory=list)
    success_metric: str = Field(min_length=5)
    known_constraints: list[str] = Field(default_factory=list)
    requester: str | None = None
    channel_id: str | None = None
    thread_ts: str | None = None
