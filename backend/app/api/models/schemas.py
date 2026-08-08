from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ReworkDispositionValue = Literal[
    "unreviewed",
    "confirmed_rework",
    "partial_rework",
    "related_expected",
    "unrelated",
]


class Repo(BaseModel):
    id: str
    name: str
    team_id: str


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
    closed_at: datetime
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
    ai_generated: bool = False


class PullRequestFile(BaseModel):
    id: str
    pull_request_id: int
    file_path: str
    additions: int = Field(default=0, ge=0)
    deletions: int = Field(default=0, ge=0)


class PullRequestFilesCreate(BaseModel):
    file_paths: list[str]


class PullRequestCreate(BaseModel):
    title: str
    body: str
    author_login: str
    merged_by_login: str
    head_branch: str
    ai_generated: bool
    repo_id: str
    closed_at: datetime | None = None


class PullRequestWithFilesCreate(BaseModel):
    pull_request: PullRequestCreate
    file_paths: list[str]


class ReworkEvent(BaseModel):
    id: str
    source_pr_id: int
    followup_pr_id: int
    detected_from: str
    rework_type: str
    severity: str
    days_after_merge: int = Field(ge=0)
    human_hours_spent: float = Field(ge=0)
    root_cause_label: str
    disposition: ReworkDispositionValue = "unreviewed"
    summary: str


class ContextArtifact(BaseModel):
    id: str
    rework_event_id: str
    name: str
    artifact_type: str
    repo_id: str
    team_id: str
    last_updated_at: datetime | None = None
    summary: str


class ContextArtifactCreate(BaseModel):
    name: str
    artifact_type: str
    summary: str


class AutopsySummary(BaseModel):
    team_count: int = Field(ge=0)
    repo_count: int = Field(ge=0)
    pull_request_count: int = Field(ge=0)
    rework_event_count: int = Field(ge=0)
    context_artifact_count: int = Field(ge=0)
    ai_generated_pr_count: int = Field(ge=0)
    total_rework_hours: float = Field(ge=0)
    avg_days_after_merge: float = Field(ge=0)


class ReworkEventDetailEvent(BaseModel):
    id: str
    severity: str
    root_cause_label: str
    disposition: ReworkDispositionValue = "unreviewed"
    days_after_merge: int = Field(ge=0)
    human_hours_spent: float = Field(ge=0)
    summary: str


class ReworkEventDetailPullRequest(BaseModel):
    id: int
    number: int
    title: str
    repo_name: str
    ai_generated: bool | None = None


class ReworkEventDetailContextArtifact(BaseModel):
    id: str
    name: str
    artifact_type: str
    summary: str


class ReworkEventDetail(BaseModel):
    rework_event: ReworkEventDetailEvent
    source_pr: ReworkEventDetailPullRequest
    followup_pr: ReworkEventDetailPullRequest
    context_artifacts: list[ReworkEventDetailContextArtifact] = []


class ReworkRecomputeResult(BaseModel):
    rework_event_count: int = Field(ge=0)
    message: str


class ReworkRootCause(BaseModel):
    root_cause: str


class ReworkDisposition(BaseModel):
    disposition: ReworkDispositionValue


class ReworkFeatures(BaseModel):
    shared_file_count: int
    source_file_overlap_ratio: float
    followup_file_overlap_ratio: float
    semantic_similarity: float
    has_revert_signal: bool
    has_test_file_overlap: bool
    has_high_risk_file_overlap: bool
    has_explicit_pr_reference: bool
    references_same_issue: bool
    hours_between_merges: float
    same_author: bool
    source_ai_generated: bool
    author_historical_rework_rate: float
