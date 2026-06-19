from app.api.models import PullRequest, PullRequestFile
from datetime import timedelta
import re

REWORK_LANGUAGE_PATTERN = re.compile(
    r"(#rework\b|\bfix(?:es|ed)?\b|\bpatch(?:es|ed)?\b|\brestore(?:s|d)?\b)",
    re.IGNORECASE,
)


def has_same_repo(source_pr: PullRequest, followup_pr: PullRequest) -> bool:
    return source_pr.repo_id == followup_pr.repo_id


def is_followup_after_source(source_pr: PullRequest, followup_pr: PullRequest) -> bool:
    return followup_pr.closed_at > source_pr.closed_at


def is_ai_to_non_ai_within_14_days(
    source_pr: PullRequest, followup_pr: PullRequest
) -> bool:
    if source_pr.ai_generated and not followup_pr.ai_generated:
        return (followup_pr.closed_at - source_pr.closed_at) <= timedelta(days=14)
    return False


def validate_files_belong_to_same_pr(files_list: list[PullRequestFile]) -> bool:
    if not files_list:
        return True

    target_pr_id = files_list[0].pull_request_id
    for file in files_list:
        if target_pr_id != file.pull_request_id:
            return False
    return True


def get_overlapping_files(
    source_files: list[PullRequestFile], followup_files: list[PullRequestFile]
) -> list[PullRequestFile]:
    if not (
        validate_files_belong_to_same_pr(source_files)
        and validate_files_belong_to_same_pr(followup_files)
    ):
        raise Exception("Files do not belong to the same file list")

    source_files_by_path: dict[str, PullRequestFile] = {}
    overlapping_files: list[PullRequestFile] = []

    for source_file in source_files:
        source_files_by_path[source_file.file_path] = source_file

    for followup_file in followup_files:
        if followup_file.file_path in source_files_by_path:
            overlapping_files.append(followup_file)

    return overlapping_files


def has_followup_rework_language(followup_pr: PullRequest) -> bool:
    text = followup_pr.title + " \n" + (followup_pr.body or "")
    return REWORK_LANGUAGE_PATTERN.search(text) is not None


def has_rework_override(followup_pr: PullRequest) -> bool:
    text = followup_pr.title + " \n" + (followup_pr.body or "")
    return re.search(r"#rework\b", text, re.IGNORECASE) is not None
