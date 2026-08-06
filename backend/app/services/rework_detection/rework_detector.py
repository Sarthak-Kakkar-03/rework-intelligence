from app.api.models import PullRequest, PullRequestFile
from app.services.rework_detection.models import ReworkCandidate
from app.services.rework_detection.estimates import (
    build_summary,
    estimate_confidence,
    estimate_days_after_merge,
    estimate_human_hours_spent,
    estimate_severity,
)
from app.services.rework_detection.features import (
    compute_rework_features,
    has_explicit_pr_reference,
    has_revert_signal,
    high_risk_file_overlap,
    references_same_issue,
    test_file_overlap,
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
    get_author_historical_rework_rate,
    get_global_rework_rate,
    get_rework_events,
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

    # File overlap is intentionally just one of several qualifying signals
    # below (alongside revert language, PR/issue references, and test-file
    # overlap), not a mandatory prerequisite — a pair can still be a rework
    # candidate purely on structural/textual evidence with zero file overlap.
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
    if has_revert_signal(followup_pr):
        signals.append("Followup contains revert language")
    if has_explicit_pr_reference(source_pr=source_pr, followup_pr=followup_pr):
        signals.append("Followup references source PR")
    if references_same_issue(source_pr=source_pr, followup_pr=followup_pr):
        signals.append("Source and followup reference the same issue")
    if test_file_overlap(source_files=source_files, followup_files=followup_files):
        signals.append("Detected overlapping test files")
    if high_risk_file_overlap(source_files=source_files, followup_files=followup_files):
        signals.append("Overlapping high-risk file (api/migration/config/model/service)")
    return signals


def _find_all_candidate_pairs(
    pr_list: list[PullRequest],
    already_used_pr_ids: set[int],
) -> list[dict]:
    """
    Finds every (source, followup) pair that qualifies as a rework
    candidate, without assigning/consuming PRs yet. A PR can appear in
    multiple candidate pairs here — deduplication happens in a separate
    pass so the best match wins, not just the chronologically nearest one.
    """
    files_by_pr_id: dict[int, list[PullRequestFile]] = {}

    def get_files(pr_id: int) -> list[PullRequestFile]:
        if pr_id not in files_by_pr_id:
            files_by_pr_id[pr_id] = get_pull_request_files_by_pr_id(pr_id)
        return files_by_pr_id[pr_id]

    candidates: list[dict] = []
    for followup_idx, followup_pr in enumerate(pr_list):
        if followup_pr.id in already_used_pr_ids:
            continue

        for source_idx in range(followup_idx - 1, -1, -1):
            source_pr = pr_list[source_idx]
            if source_pr.id in already_used_pr_ids:
                continue
            if not is_possible_rework_candidate(
                source_pr=source_pr, followup_pr=followup_pr
            ):
                continue

            source_files = get_files(source_pr.id)
            followup_files = get_files(followup_pr.id)
            matched_signals = get_rework_signals(
                source_pr=source_pr,
                followup_pr=followup_pr,
                followup_files=followup_files,
                source_files=source_files,
            )
            if not is_rework_candidate(
                source_pr=source_pr,
                followup_pr=followup_pr,
                followup_files=followup_files,
                source_files=source_files,
            ):
                continue

            candidates.append(
                {
                    "source_pr": source_pr,
                    "followup_pr": followup_pr,
                    "source_files": source_files,
                    "followup_files": followup_files,
                    "matched_signals": matched_signals,
                    "is_override": has_rework_override(followup_pr=followup_pr),
                }
            )

    return candidates


def _candidate_priority(candidate: dict) -> tuple[int, int, int]:
    # Sorted ascending, so: overrides first, then most matched signals,
    # then the smallest time gap as a tiebreaker (the nearer-in-time match
    # is the safer default when two candidates are otherwise equally strong).
    days_after_merge = estimate_days_after_merge(
        source_pr=candidate["source_pr"], followup_pr=candidate["followup_pr"]
    )
    return (
        0 if candidate["is_override"] else 1,
        -len(candidate["matched_signals"]),
        days_after_merge,
    )


def generate_rework_candidates() -> list[ReworkCandidate]:
    pr_list: list[PullRequest] = get_pull_requests_ordered_by_closed_at()
    used_pr_ids: set[int] = set()
    for rework_event in get_rework_events():
        used_pr_ids.add(rework_event.source_pr_id)
        used_pr_ids.add(rework_event.followup_pr_id)

    candidates = _find_all_candidate_pairs(pr_list, used_pr_ids)
    # Global greedy-by-best-match assignment: a PR that's a plausible match
    # for several others should go to its STRONGEST match, not whichever
    # candidate happens to be scanned first chronologically.
    candidates.sort(key=_candidate_priority)

    global_rework_rate = get_global_rework_rate()
    result: list[ReworkCandidate] = []
    for candidate in candidates:
        source_pr = candidate["source_pr"]
        followup_pr = candidate["followup_pr"]
        if source_pr.id in used_pr_ids or followup_pr.id in used_pr_ids:
            continue

        source_files = candidate["source_files"]
        followup_files = candidate["followup_files"]
        matched_signals = candidate["matched_signals"]

        overlapping_files = get_overlapping_files(
            source_files=source_files,
            followup_files=followup_files,
        )
        human_hours_spent = estimate_human_hours_spent(
            followup_pr=followup_pr,
            overlapping_files=overlapping_files,
        )
        author_historical_rework_rate = get_author_historical_rework_rate(
            author_login=source_pr.author_login,
            before=source_pr.closed_at,
            prior=global_rework_rate,
        )
        features = compute_rework_features(
            source_pr=source_pr,
            followup_pr=followup_pr,
            source_files=source_files,
            followup_files=followup_files,
            overlapping_files=overlapping_files,
            author_historical_rework_rate=author_historical_rework_rate,
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
                overlapping_files=[file.file_path for file in overlapping_files],
                matched_signals=matched_signals,
                confidence=estimate_confidence(matched_signals=matched_signals),
                severity=estimate_severity(human_hours_spent=human_hours_spent),
                human_hours_spent=human_hours_spent,
                root_cause_label="placeholder",
                features=features,
                summary=build_summary(
                    source_pr=source_pr,
                    followup_pr=followup_pr,
                    matched_signals=matched_signals,
                ),
            )
        )
        used_pr_ids.add(source_pr.id)
        used_pr_ids.add(followup_pr.id)

    return result
