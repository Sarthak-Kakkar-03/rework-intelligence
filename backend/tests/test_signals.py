from datetime import datetime, timezone

from app.api.models import PullRequest
from app.services.rework_detection.signals import has_followup_rework_language

NOW = datetime(2026, 4, 1, tzinfo=timezone.utc)


def make_pr(title: str = "", body: str | None = None) -> PullRequest:
    return PullRequest(
        id=1,
        number=1,
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


def test_has_followup_rework_language_matches_original_keywords():
    assert has_followup_rework_language(make_pr(title="Fix retry bug")) is True
    assert has_followup_rework_language(make_pr(title="Patch idempotency gap")) is True
    assert has_followup_rework_language(make_pr(title="Restore prior behavior")) is True


def test_has_followup_rework_language_matches_widened_keywords():
    assert has_followup_rework_language(make_pr(body="Handles a rare bug.")) is True
    assert (
        has_followup_rework_language(make_pr(title="Fix regression in parser")) is True
    )
    assert has_followup_rework_language(make_pr(title="Cleanup pass")) is True
    assert has_followup_rework_language(make_pr(title="Clean-up pass")) is True
    assert (
        has_followup_rework_language(make_pr(body="Correct the helper names.")) is True
    )
    assert has_followup_rework_language(make_pr(title="Hotfix for staging")) is True
    assert (
        has_followup_rework_language(make_pr(body="Adjust the timeout value.")) is True
    )
    assert has_followup_rework_language(make_pr(body="The build was broken.")) is True


def test_has_followup_rework_language_false_for_unrelated_text():
    pr = make_pr(title="Add retry handling", body="Handles Jira sync")
    assert has_followup_rework_language(pr) is False
