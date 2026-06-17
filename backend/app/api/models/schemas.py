from datetime import datetime

from pydantic import BaseModel, Field


class PullRequest(BaseModel):
    id: int
    number: int
    repo_id: str
    title: str
    body: str | None = None
    state: str
    draft: bool = False
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None
    merged_at: datetime | None = None
    merged: bool = False
    author_login: str
    merged_by_login: str | None = None
    base_branch: str
    head_branch: str
    additions: int = Field(default=0, ge=0)
    deletions: int = Field(default=0, ge=0)
    changed_files: int = Field(default=0, ge=0)
    commits: int = Field(default=0, ge=0)
    comments: int = Field(default=0, ge=0)
    review_comments: int = Field(default=0, ge=0)
    linked_issue_key: str | None = None
    ai_assisted: bool = False
    ai_tool: str | None = None
    work_type: str


class ReworkEvent(BaseModel):
    id: str
    source_pr_id: int
    followup_pr_id: int | None = None
    issue_key: str | None = None
    detected_from: str
    rework_type: str
    severity: str
    days_after_merge: int = Field(ge=0)
    human_hours_spent: float = Field(ge=0)
    root_cause_label: str
    summary: str


class ContextRecommendation(BaseModel):
    id: str
    rework_event_id: str
    recommended_artifact_id: str | None = None
    missing_context_type: str
    priority: str
    recommendation: str
    reason: str


class AutopsySummary(BaseModel):
    team_count: int = Field(ge=0)
    repo_count: int = Field(ge=0)
    issue_count: int = Field(ge=0)
    pull_request_count: int = Field(ge=0)
    rework_event_count: int = Field(ge=0)
    context_artifact_count: int = Field(ge=0)
    context_recommendation_count: int = Field(ge=0)
    ai_assisted_pr_count: int = Field(ge=0)
    total_rework_hours: float = Field(ge=0)
    avg_days_after_merge: float = Field(ge=0)


class ReworkEventDetailEvent(BaseModel):
    id: str
    severity: str
    root_cause_label: str
    days_after_merge: int = Field(ge=0)
    human_hours_spent: float = Field(ge=0)
    summary: str


class ReworkEventDetailPullRequest(BaseModel):
    id: int
    number: int
    title: str
    repo_name: str
    ai_assisted: bool | None = None
    ai_tool: str | None = None


class ReworkEventDetailRecommendation(BaseModel):
    id: str
    priority: str
    missing_context_type: str
    recommendation: str
    reason: str


class ReworkEventDetailContextArtifact(BaseModel):
    id: str
    name: str
    artifact_type: str
    freshness: str


class ReworkEventDetail(BaseModel):
    rework_event: ReworkEventDetailEvent
    source_pr: ReworkEventDetailPullRequest
    followup_pr: ReworkEventDetailPullRequest | None = None
    recommendation: ReworkEventDetailRecommendation | None = None
    context_artifact: ReworkEventDetailContextArtifact | None = None
