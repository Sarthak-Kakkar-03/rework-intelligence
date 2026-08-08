from pydantic import BaseModel

from app.api.models import ReworkFeatures


class ReworkCandidate(BaseModel):
    source_pr_id: int
    followup_pr_id: int
    repo_id: str
    days_after_merge: int
    overlapping_files: list[str]
    matched_signals: list[str]
    confidence: str
    severity: str
    human_hours_spent: float
    root_cause_label: str = "Placeholder Root Cause Label"
    summary: str
    features: ReworkFeatures
