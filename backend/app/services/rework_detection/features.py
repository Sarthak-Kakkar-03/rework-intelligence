import math
import re
from collections import Counter

from app.api.models import PullRequest, PullRequestFile, ReworkFeatures

_WORD_PATTERN = re.compile(r"[a-z0-9]+")
_REFERENCE_PATTERN = re.compile(r"#(\d+)")
_REVERT_PATTERN = re.compile(r"\brevert(?:s|ed|ing)?\b", re.IGNORECASE)
_TEST_PATH_PATTERN = re.compile(
    r"(?:^|/)tests?(?:/|$)|(?:^|/)test_[^/]+\.\w+$|(?:^|/)[^/]+_test\.\w+$",
    re.IGNORECASE,
)

# Proposal-specified "high-value" file categories: overlap on one of these is
# stronger evidence of rework than overlap on an arbitrary utility file.
_HIGH_RISK_PATH_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("migration", re.compile(r"(?:^|/)migrations?(?:/|$)", re.IGNORECASE)),
    ("api", re.compile(r"(?:^|/)(?:api|routes|endpoints)(?:/|$)", re.IGNORECASE)),
    (
        "config",
        re.compile(
            r"(?:^|/)(?:config|settings)(?:/|$)|\.(?:ya?ml|toml|ini|env|cfg)$",
            re.IGNORECASE,
        ),
    ),
    ("model", re.compile(r"(?:^|/)models?(?:/|$)|(?:^|/)schema\.\w+$", re.IGNORECASE)),
    ("service", re.compile(r"(?:^|/)services?(?:/|$)", re.IGNORECASE)),
]


def _pr_text(pr: PullRequest) -> str:
    return f"{pr.title} \n{pr.body or ''}"


def file_overlap_ratios(
    source_files: list[PullRequestFile],
    followup_files: list[PullRequestFile],
    overlapping_files: list[PullRequestFile],
) -> tuple[int, float, float]:
    shared_count = len(overlapping_files)
    source_ratio = shared_count / len(source_files) if source_files else 0.0
    followup_ratio = shared_count / len(followup_files) if followup_files else 0.0
    return shared_count, source_ratio, followup_ratio


def _tokenize(text: str) -> Counter[str]:
    return Counter(_WORD_PATTERN.findall(text.lower()))


def semantic_similarity(source_pr: PullRequest, followup_pr: PullRequest) -> float:
    """
    Bag-of-words cosine similarity over PR title+body text.

    Stdlib-only placeholder for a real embeddings-based similarity, kept
    dependency-free and explainable until the ML classifier work replaces it.
    """
    source_counts = _tokenize(_pr_text(source_pr))
    followup_counts = _tokenize(_pr_text(followup_pr))

    if not source_counts or not followup_counts:
        return 0.0

    shared_words = set(source_counts) & set(followup_counts)
    dot_product = sum(
        source_counts[word] * followup_counts[word] for word in shared_words
    )

    source_magnitude = math.sqrt(sum(count * count for count in source_counts.values()))
    followup_magnitude = math.sqrt(
        sum(count * count for count in followup_counts.values())
    )

    if source_magnitude == 0 or followup_magnitude == 0:
        return 0.0

    return dot_product / (source_magnitude * followup_magnitude)


def has_revert_signal(pr: PullRequest) -> bool:
    return _REVERT_PATTERN.search(_pr_text(pr)) is not None


def is_test_file(file_path: str) -> bool:
    return _TEST_PATH_PATTERN.search(file_path) is not None


def test_file_overlap(
    source_files: list[PullRequestFile], followup_files: list[PullRequestFile]
) -> bool:
    source_test_paths = {
        file.file_path for file in source_files if is_test_file(file.file_path)
    }
    followup_test_paths = {
        file.file_path for file in followup_files if is_test_file(file.file_path)
    }
    return bool(source_test_paths & followup_test_paths)


def classify_file_risk(file_path: str) -> str | None:
    for risk_category, pattern in _HIGH_RISK_PATH_PATTERNS:
        if pattern.search(file_path):
            return risk_category
    return None


def is_high_risk_file(file_path: str) -> bool:
    return classify_file_risk(file_path) is not None


def high_risk_file_overlap(
    source_files: list[PullRequestFile], followup_files: list[PullRequestFile]
) -> bool:
    source_paths = {
        file.file_path for file in source_files if is_high_risk_file(file.file_path)
    }
    followup_paths = {
        file.file_path for file in followup_files if is_high_risk_file(file.file_path)
    }
    return bool(source_paths & followup_paths)


def extract_referenced_numbers(pr: PullRequest) -> set[int]:
    return {int(match) for match in _REFERENCE_PATTERN.findall(_pr_text(pr))}


def has_explicit_pr_reference(source_pr: PullRequest, followup_pr: PullRequest) -> bool:
    return source_pr.number in extract_referenced_numbers(followup_pr)


def references_same_issue(source_pr: PullRequest, followup_pr: PullRequest) -> bool:
    own_numbers = {source_pr.number, followup_pr.number}
    source_refs = extract_referenced_numbers(source_pr) - own_numbers
    followup_refs = extract_referenced_numbers(followup_pr) - own_numbers
    return bool(source_refs & followup_refs)


def compute_rework_features(
    source_pr: PullRequest,
    followup_pr: PullRequest,
    source_files: list[PullRequestFile],
    followup_files: list[PullRequestFile],
    overlapping_files: list[PullRequestFile],
    author_historical_rework_rate: float,
) -> ReworkFeatures:
    shared_count, source_ratio, followup_ratio = file_overlap_ratios(
        source_files=source_files,
        followup_files=followup_files,
        overlapping_files=overlapping_files,
    )
    hours_between_merges = (
        followup_pr.closed_at - source_pr.closed_at
    ).total_seconds() / 3600.0

    return ReworkFeatures(
        shared_file_count=shared_count,
        source_file_overlap_ratio=round(source_ratio, 3),
        followup_file_overlap_ratio=round(followup_ratio, 3),
        semantic_similarity=round(
            semantic_similarity(source_pr=source_pr, followup_pr=followup_pr), 3
        ),
        has_revert_signal=has_revert_signal(followup_pr),
        has_test_file_overlap=test_file_overlap(
            source_files=source_files, followup_files=followup_files
        ),
        has_high_risk_file_overlap=high_risk_file_overlap(
            source_files=source_files, followup_files=followup_files
        ),
        has_explicit_pr_reference=has_explicit_pr_reference(
            source_pr=source_pr, followup_pr=followup_pr
        ),
        references_same_issue=references_same_issue(
            source_pr=source_pr, followup_pr=followup_pr
        ),
        hours_between_merges=round(hours_between_merges, 2),
        same_author=source_pr.author_login == followup_pr.author_login,
        source_ai_generated=source_pr.ai_generated,
        author_historical_rework_rate=round(author_historical_rework_rate, 4),
    )
