from datetime import datetime, timezone

import pytest

from app.api.models import PullRequest, PullRequestFile
from app.services.rework_detection.features import (
    classify_file_risk,
    compute_rework_features,
    extract_referenced_numbers,
    file_overlap_ratios,
    has_explicit_pr_reference,
    has_revert_signal,
    high_risk_file_overlap,
    is_high_risk_file,
    is_test_file,
    references_same_issue,
    semantic_similarity,
    test_file_overlap as has_overlapping_test_files,
)

NOW = datetime(2026, 4, 1, tzinfo=timezone.utc)


def make_pr(
    id: int,
    number: int,
    title: str = "",
    body: str | None = None,
) -> PullRequest:
    return PullRequest(
        id=id,
        number=number,
        repo_id="repo-1",
        title=title,
        body=body,
        state="closed",
        created_at=NOW,
        updated_at=NOW,
        closed_at=NOW,
        author_login="someone",
        base_branch="main",
        head_branch="feature",
    )


def make_file(pull_request_id: int, file_path: str) -> PullRequestFile:
    return PullRequestFile(
        id=f"{pull_request_id}:{file_path}",
        pull_request_id=pull_request_id,
        file_path=file_path,
    )


def test_file_overlap_ratios_with_partial_overlap():
    source_files = [make_file(1, "a.py"), make_file(1, "b.py")]
    followup_files = [
        make_file(2, "a.py"),
        make_file(2, "c.py"),
        make_file(2, "d.py"),
    ]
    overlapping = [make_file(2, "a.py")]

    shared_count, source_ratio, followup_ratio = file_overlap_ratios(
        source_files=source_files,
        followup_files=followup_files,
        overlapping_files=overlapping,
    )

    assert shared_count == 1
    assert source_ratio == 0.5
    assert followup_ratio == 1 / 3


def test_file_overlap_ratios_with_no_files_is_zero_not_divide_error():
    shared_count, source_ratio, followup_ratio = file_overlap_ratios(
        source_files=[],
        followup_files=[],
        overlapping_files=[],
    )

    assert shared_count == 0
    assert source_ratio == 0.0
    assert followup_ratio == 0.0


def test_semantic_similarity_identical_text_is_high():
    source_pr = make_pr(1, 41, title="Fix retry handling", body="Handles retries")
    followup_pr = make_pr(2, 42, title="Fix retry handling", body="Handles retries")

    assert semantic_similarity(source_pr, followup_pr) == pytest.approx(1.0)


def test_semantic_similarity_unrelated_text_is_zero():
    source_pr = make_pr(1, 41, title="Add retry handling", body="Handles Jira sync")
    followup_pr = make_pr(2, 42, title="Update onboarding docs", body="New hire steps")

    assert semantic_similarity(source_pr, followup_pr) == 0.0


def test_semantic_similarity_empty_text_is_zero():
    source_pr = make_pr(1, 41, title="", body=None)
    followup_pr = make_pr(2, 42, title="", body=None)

    assert semantic_similarity(source_pr, followup_pr) == 0.0


def test_has_revert_signal_matches_github_style_title():
    pr = make_pr(2, 42, title='Revert "Add retry handling"', body=None)
    assert has_revert_signal(pr) is True


def test_has_revert_signal_matches_body_language():
    pr = make_pr(2, 42, title="Undo bad rollout", body="This reverts commit abc123.")
    assert has_revert_signal(pr) is True


def test_has_revert_signal_false_for_unrelated_text():
    pr = make_pr(2, 42, title="Add retry handling", body="Handles Jira sync")
    assert has_revert_signal(pr) is False


def test_is_test_file_matches_common_test_paths():
    assert is_test_file("backend/tests/test_features.py") is True
    assert is_test_file("backend/app/services/foo_test.py") is True
    assert is_test_file("frontend/tests/page.test.tsx") is True


def test_is_test_file_false_for_regular_source_file():
    assert is_test_file("backend/app/services/foo.py") is False


def test_test_file_overlap_true_when_shared_test_path():
    source_files = [make_file(1, "backend/tests/test_foo.py")]
    followup_files = [
        make_file(2, "backend/tests/test_foo.py"),
        make_file(2, "backend/app/foo.py"),
    ]

    assert has_overlapping_test_files(source_files, followup_files) is True


def test_test_file_overlap_false_when_no_shared_test_path():
    source_files = [make_file(1, "backend/tests/test_foo.py")]
    followup_files = [make_file(2, "backend/tests/test_bar.py")]

    assert has_overlapping_test_files(source_files, followup_files) is False


def test_extract_referenced_numbers_finds_all_hash_refs():
    pr = make_pr(1, 41, title="Fixes #41", body="Related to #99 and #100")
    assert extract_referenced_numbers(pr) == {41, 99, 100}


def test_has_explicit_pr_reference_true_when_followup_cites_source_number():
    source_pr = make_pr(1, 41, title="Add retry handling", body=None)
    followup_pr = make_pr(2, 42, title="Fix retry bug", body="Fixes #41.")

    assert has_explicit_pr_reference(source_pr, followup_pr) is True


def test_has_explicit_pr_reference_false_when_no_reference():
    source_pr = make_pr(1, 41, title="Add retry handling", body=None)
    followup_pr = make_pr(2, 42, title="Fix retry bug", body="No references here.")

    assert has_explicit_pr_reference(source_pr, followup_pr) is False


def test_references_same_issue_true_when_both_cite_a_shared_number():
    source_pr = make_pr(1, 41, title="Add retry handling", body="See #500 for context.")
    followup_pr = make_pr(2, 42, title="Fix retry bug", body="Follows up on #500.")

    assert references_same_issue(source_pr, followup_pr) is True


def test_references_same_issue_false_when_only_one_side_cites_it():
    source_pr = make_pr(1, 41, title="Add retry handling", body="See #500 for context.")
    followup_pr = make_pr(2, 42, title="Fix retry bug", body="No shared reference.")

    assert references_same_issue(source_pr, followup_pr) is False


def test_references_same_issue_ignores_mutual_pr_number_references():
    source_pr = make_pr(1, 41, title="Add retry handling", body="Related to #42.")
    followup_pr = make_pr(2, 42, title="Fix retry bug", body="Fixes #41.")

    assert references_same_issue(source_pr, followup_pr) is False


def test_compute_rework_features_returns_full_vector():
    source_pr = make_pr(1, 41, title="Add retry handling", body="Handles retries")
    followup_pr = make_pr(
        2, 42, title='Revert "Add retry handling"', body="Fixes #41."
    )
    source_files = [make_file(1, "a.py")]
    followup_files = [make_file(2, "a.py")]
    overlapping_files = [make_file(2, "a.py")]

    features = compute_rework_features(
        source_pr=source_pr,
        followup_pr=followup_pr,
        source_files=source_files,
        followup_files=followup_files,
        overlapping_files=overlapping_files,
        author_historical_rework_rate=0.2,
    )

    assert features.shared_file_count == 1
    assert features.source_file_overlap_ratio == 1.0
    assert features.followup_file_overlap_ratio == 1.0
    assert features.has_revert_signal is True
    assert features.has_explicit_pr_reference is True
    assert features.has_test_file_overlap is False
    assert features.same_author is True
    assert features.source_ai_generated is False
    assert features.author_historical_rework_rate == 0.2


def test_classify_file_risk_matches_expected_categories():
    assert classify_file_risk("backend/db/migrations/001_init.sql") == "migration"
    assert classify_file_risk("backend/app/api/routes/ingest.py") == "api"
    assert classify_file_risk("backend/app/config/settings.py") == "config"
    assert classify_file_risk("config/production.yaml") == "config"
    assert classify_file_risk("backend/app/models/user.py") == "model"
    assert classify_file_risk("src/deployment_risk/schema.py") == "model"
    assert classify_file_risk("backend/app/services/billing.py") == "service"


def test_classify_file_risk_returns_none_for_generic_file():
    assert classify_file_risk("src/shared/format_date.py") is None


def test_is_high_risk_file_matches_classify_file_risk():
    assert is_high_risk_file("backend/db/migrations/001_init.sql") is True
    assert is_high_risk_file("src/shared/format_date.py") is False


def test_high_risk_file_overlap_true_when_shared_migration_file():
    source_files = [make_file(1, "backend/db/migrations/001_init.sql")]
    followup_files = [
        make_file(2, "backend/db/migrations/001_init.sql"),
        make_file(2, "backend/app/models/user.py"),
    ]

    assert high_risk_file_overlap(source_files, followup_files) is True


def test_high_risk_file_overlap_false_when_only_generic_files_shared():
    source_files = [make_file(1, "src/shared/format_date.py")]
    followup_files = [make_file(2, "src/shared/format_date.py")]

    assert high_risk_file_overlap(source_files, followup_files) is False
