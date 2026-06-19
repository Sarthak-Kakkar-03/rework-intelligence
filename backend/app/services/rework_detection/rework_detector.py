from app.services.rework_detection.signals import *
from app.api.models import PullRequest, PullRequestFile

def is_rework_candidate(source_pr: PullRequest,
                        followup_pr: PullRequest,
                        source_files: list[PullRequestFile],
                        followup_files: list[PullRequestFile]) -> bool:
    if not (has_same_repo(source_pr=source_pr, followup_pr=followup_pr) and is_followup_after_source(source_pr=source_pr, followup_pr=followup_pr)):
        return False
    signal_score = 0
    if has_rework_override(followup_pr=followup_pr):
        return True
    if is_ai_to_non_ai_within_14_days(source_pr=source_pr, followup_pr=followup_pr):
        signal_score += 1
    if get_overlapping_files(source_files=source_files, followup_files=followup_files):
        signal_score += 1
    if has_followup_rework_language(followup_pr=followup_pr):
        signal_score += 1
    return signal_score >= 2
    
