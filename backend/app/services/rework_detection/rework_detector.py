from app.api.models import PullRequest, PullRequestFile
from app.services.rework_detection.models import ReworkCandidate
from app.services.rework_detection.estimates import (
    build_summary,
    estimate_confidence,
    estimate_days_after_merge,
    estimate_human_hours_spent,
    estimate_severity,
)
from app.services.rework_detection.signals import (
    get_overlapping_files,
    has_followup_rework_language,
    has_rework_override,
    has_same_repo,
    is_ai_to_non_ai_within_14_days,
    is_followup_after_source,
)
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
    if not get_overlapping_files(
        source_files=source_files,
        followup_files=followup_files,
    ):
        return False

    return (
        len(
            get_rework_signals(
                source_pr=source_pr,
                followup_pr=followup_pr,
                source_files=source_files,
                followup_files=followup_files,
            )
        )
        >= 2
    )


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
    files_by_pr_id: dict[int, list[PullRequestFile]] = {}
    used_source_pr_ids: set[int] = set()
    result: list[ReworkCandidate] = []
    for followup_idx, followup_pr in enumerate(pr_list):
        for source_idx in range(followup_idx - 1, -1, -1):
            source_pr = pr_list[source_idx]
            if source_pr.id in used_source_pr_ids:
                continue
            if is_possible_rework_candidate(
                source_pr=source_pr, followup_pr=followup_pr
            ):
                if source_pr.id not in files_by_pr_id:
                    files_by_pr_id[source_pr.id] = get_pull_request_files_by_pr_id(
                        source_pr.id
                    )
                if followup_pr.id not in files_by_pr_id:
                    files_by_pr_id[followup_pr.id] = get_pull_request_files_by_pr_id(
                        followup_pr.id
                    )

                source_files = files_by_pr_id[source_pr.id]
                followup_files = files_by_pr_id[followup_pr.id]
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
                    overlapping_files = get_overlapping_files(
                        source_files=source_files,
                        followup_files=followup_files,
                    )
                    human_hours_spent = estimate_human_hours_spent(
                        followup_pr=followup_pr,
                        overlapping_files=overlapping_files,
                    )
                    result.append(
                        ReworkCandidate(
                            source_pr_id=source_pr.id,
                            followup_pr_id=followup_pr.id,
                            repo_id=source_pr.repo_id,
                            days_after_merge=estimate_days_after_merge(
                                source_pr=source_pr,
                                followup_pr=followup_pr,
                            ),
                            overlapping_files=[
                                file.file_path for file in overlapping_files
                            ],
                            matched_signals=matched_signals,
                            confidence=estimate_confidence(
                                matched_signals=matched_signals,
                            ),
                            severity=estimate_severity(
                                human_hours_spent=human_hours_spent,
                            ),
                            human_hours_spent=human_hours_spent,
                            root_cause_label="placeholder",
                            summary=build_summary(
                                source_pr=source_pr,
                                followup_pr=followup_pr,
                                matched_signals=matched_signals,
                            ),
                        )
                    )
                    used_source_pr_ids.add(source_pr.id)
                    break
    return result
