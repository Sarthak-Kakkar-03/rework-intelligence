from app.services.rework_detection.signals import *
from app.api.models import PullRequest, PullRequestFile
from app.services.rework_detection.models import ReworkCandidate
from app.queries import (
    get_pull_requests_ordered_by_closed_at,
    get_pull_request_files_by_pr_id,
)


def is_possible_rework_candidate(
    source_pr: PullRequest, followup_pr: PullRequest
) -> bool:
    if not (
        has_same_repo(source_pr=source_pr, followup_pr=followup_pr)
        and is_followup_after_source(source_pr=source_pr, followup_pr=followup_pr)
    ):
        return False
    return True


def is_rework_candidate(
    source_pr: PullRequest,
    followup_pr: PullRequest,
    source_files: list[PullRequestFile],
    followup_files: list[PullRequestFile],
) -> bool:
    if not is_possible_rework_candidate(source_pr=source_pr, followup_pr=followup_pr):
        return False
    if has_rework_override(followup_pr=followup_pr):
        return True

    return len(
        get_rework_signals(
            source_pr=source_pr,
            followup_pr=followup_pr,
            source_files=source_files,
            followup_files=followup_files,
        )
    ) >= 2


def get_rework_signals(
    source_pr: PullRequest,
    followup_pr: PullRequest,
    source_files: list[PullRequestFile],
    followup_files: list[PullRequestFile],
) -> list[str]:
    if not is_possible_rework_candidate(source_pr=source_pr, followup_pr=followup_pr):
        return []
    if has_rework_override(followup_pr=followup_pr):
        return ["Rework Override Indicated"]

    signals = []

    if is_ai_to_non_ai_within_14_days(source_pr=source_pr, followup_pr=followup_pr):
        signals.append("Non AI PR within 2 weeks")
    if get_overlapping_files(source_files=source_files, followup_files=followup_files):
        signals.append("Detected Overlapping files")
    if has_followup_rework_language(followup_pr=followup_pr):
        signals.append("Followup has rework language")
    return signals


def generate_rework_candidates() -> list[ReworkCandidate]:
    pr_list: list[PullRequest] = get_pull_requests_ordered_by_closed_at()
    result: list[ReworkCandidate] = []
    for source_idx, source_pr in enumerate(pr_list):
        for followup_idx in range(source_idx + 1, len(pr_list)):
            followup_pr = pr_list[followup_idx]
            if is_possible_rework_candidate(
                source_pr=source_pr, followup_pr=followup_pr
            ):
                source_files = get_pull_request_files_by_pr_id(source_pr.id)
                followup_files = get_pull_request_files_by_pr_id(followup_pr.id)
                rework_candidate_bool = is_rework_candidate(
                    source_pr=source_pr,
                    followup_pr=followup_pr,
                    followup_files=followup_files,
                    source_files=source_files,
                )
                if rework_candidate_bool:
                    matched_signals = get_rework_signals(
                        source_pr=source_pr,
                        followup_pr=followup_pr,
                        followup_files=followup_files,
                        source_files=source_files,
                    )
                    result.append(
                        ReworkCandidate(
                            source_pr_id=source_pr.id,
                            followup_pr_id=followup_pr.id,
                            repo_id=source_pr.repo_id,
                            days_after_merge=1,  # placeholder
                            overlapping_files=[
                                file.file_path
                                for file in get_overlapping_files(
                                    source_files=source_files, followup_files=followup_files
                                )
                            ],
                            matched_signals=matched_signals,
                            confidence="placeholder",
                            severity="placeholder",
                            human_hours_spent=1.0,
                            root_cause_label="placeholder",
                            summary="placeholder",
                        )
                    )
                    break
    return result
