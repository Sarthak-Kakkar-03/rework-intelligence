from app.api.models import PullRequest, PullRequestFile

def has_same_repo(source_pr: PullRequest, followup_pr: PullRequest) -> bool:
    return source_pr.repo_id == followup_pr.repo_id

def is_followup_after_source(source_pr: PullRequest, followup_pr: PullRequest) -> bool:
    return followup_pr.closed_at > source_pr.closed_at