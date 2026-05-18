from pydantic import BaseModel, Field


class SourceDocument(BaseModel):
    source_id: str = Field(min_length=2)
    source_type: str = Field(min_length=2)
    title: str = Field(min_length=2)
    body: str = Field(min_length=10)
    team_scope: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class RetrievedSnippet(BaseModel):
    team: str
    source_id: str
    source_type: str
    title: str
    excerpt: str = Field(min_length=5)
    score: float = Field(ge=0.0)
