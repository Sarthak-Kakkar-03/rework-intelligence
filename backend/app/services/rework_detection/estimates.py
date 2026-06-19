from app.api.models import PullRequest, PullRequestFile


def estimate_days_after_merge(source_pr: PullRequest, followup_pr: PullRequest) -> int:
    return (followup_pr.closed_at - source_pr.closed_at).days


def estimate_human_hours_spent(
    followup_pr: PullRequest,
    overlapping_files: list[PullRequestFile],
) -> float:
    base_hours = 1.0
    changed_file_hours = followup_pr.changed_files * 0.5
    overlap_hours = len(overlapping_files) * 0.5
    review_hours = min(followup_pr.review_comments, 10) * 0.1

    return round(base_hours + changed_file_hours + overlap_hours + review_hours, 1)


def estimate_severity(human_hours_spent: float) -> str:
    if human_hours_spent >= 6:
        return "high"
    if human_hours_spent >= 3:
        return "medium"
    return "low"


def estimate_confidence(matched_signals: list[str]) -> str:
    if "Rework Override Indicated" in matched_signals:
        return "high"
    if len(matched_signals) >= 3:
        return "high"
    return "medium"


def build_summary(
    source_pr: PullRequest,
    followup_pr: PullRequest,
    matched_signals: list[str],
) -> str:
    signal_text = ", ".join(matched_signals)
    return (
        f"PR {source_pr.number} was followed by PR {followup_pr.number} "
        f"in {source_pr.repo_id}; matched signals: {signal_text}."
    )
