from contextlib import closing

from app.api.models import (
    AutopsySummary,
    ContextArtifact,
    PullRequest,
    ReworkEvent,
    ReworkEventDetail,
    ReworkEventDetailContextArtifact,
    ReworkEventDetailEvent,
    ReworkEventDetailPullRequest,
)
from app.db import get_connection


def get_autopsy_summary() -> AutopsySummary:
    """
    Fetch aggregate metrics and entity counts from the database.

    Returns:
        An AutopsySummary containing counts of teams, repos, issues, pull requests, rework events, context artifacts, AI-assisted pull requests, total rework hours, and average days after merge.
    """
    sql = """
        SELECT
          (SELECT COUNT(*) FROM teams) AS team_count,
          (SELECT COUNT(*) FROM repos) AS repo_count,
          (SELECT COUNT(*) FROM issues) AS issue_count,
          (SELECT COUNT(*) FROM pull_requests) AS pull_request_count,
          (SELECT COUNT(*) FROM rework_events) AS rework_event_count,
          (SELECT COUNT(*) FROM context_artifacts) AS context_artifact_count,
          (SELECT COUNT(*) FROM pull_requests WHERE ai_assisted = 1) AS ai_assisted_pr_count,
          COALESCE((SELECT SUM(human_hours_spent) FROM rework_events), 0) AS total_rework_hours,
          COALESCE((SELECT ROUND(AVG(days_after_merge), 1) FROM rework_events), 0) AS avg_days_after_merge
    """

    with closing(get_connection()) as conn:
        row = conn.execute(sql).fetchone()
        return AutopsySummary(
            team_count=row["team_count"],
            repo_count=row["repo_count"],
            issue_count=row["issue_count"],
            pull_request_count=row["pull_request_count"],
            rework_event_count=row["rework_event_count"],
            context_artifact_count=row["context_artifact_count"],
            ai_assisted_pr_count=row["ai_assisted_pr_count"],
            total_rework_hours=row["total_rework_hours"],
            avg_days_after_merge=row["avg_days_after_merge"],
        )


def get_pull_requests() -> list[PullRequest]:
    """
    Retrieves all pull request records from the database.

    Returns:
        A list of PullRequest objects, ordered by creation date (most recent first), then by ID.
    """
    sql = """
        SELECT
          id,
          number,
          repo_id,
          title,
          body,
          state,
          draft,
          created_at,
          updated_at,
          closed_at,
          merged_at,
          merged,
          author_login,
          merged_by_login,
          base_branch,
          head_branch,
          additions,
          deletions,
          changed_files,
          commits,
          comments,
          review_comments,
          linked_issue_key,
          ai_assisted,
          ai_tool,
          work_type
        FROM pull_requests
        ORDER BY created_at DESC, id DESC
    """

    with closing(get_connection()) as conn:
        rows = conn.execute(sql).fetchall()
        return [
            PullRequest(
                id=row["id"],
                number=row["number"],
                repo_id=row["repo_id"],
                title=row["title"],
                body=row["body"],
                state=row["state"],
                draft=bool(row["draft"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                closed_at=row["closed_at"],
                merged_at=row["merged_at"],
                merged=bool(row["merged"]),
                author_login=row["author_login"],
                merged_by_login=row["merged_by_login"],
                base_branch=row["base_branch"],
                head_branch=row["head_branch"],
                additions=row["additions"],
                deletions=row["deletions"],
                changed_files=row["changed_files"],
                commits=row["commits"],
                comments=row["comments"],
                review_comments=row["review_comments"],
                linked_issue_key=row["linked_issue_key"],
                ai_assisted=bool(row["ai_assisted"]),
                ai_tool=row["ai_tool"],
                work_type=row["work_type"],
            )
            for row in rows
        ]


def get_rework_events() -> list[ReworkEvent]:
    """
    Retrieve all rework event records from the database, ordered by recency and ID.

    Returns:
        list[ReworkEvent]: A list of ReworkEvent objects ordered by days_after_merge in descending order, then by ID.
    """
    sql = """
        SELECT
          id,
          source_pr_id,
          followup_pr_id,
          issue_key,
          detected_from,
          rework_type,
          severity,
          days_after_merge,
          human_hours_spent,
          root_cause_label,
          summary
        FROM rework_events
        ORDER BY days_after_merge DESC, id
    """

    with closing(get_connection()) as conn:
        rows = conn.execute(sql).fetchall()
        return [
            ReworkEvent(
                id=row["id"],
                source_pr_id=row["source_pr_id"],
                followup_pr_id=row["followup_pr_id"],
                issue_key=row["issue_key"],
                detected_from=row["detected_from"],
                rework_type=row["rework_type"],
                severity=row["severity"],
                days_after_merge=row["days_after_merge"],
                human_hours_spent=row["human_hours_spent"],
                root_cause_label=row["root_cause_label"],
                summary=row["summary"],
            )
            for row in rows
        ]


def get_context_artifacts() -> list[ContextArtifact]:
    """
    Fetch all context artifacts.

    Returns:
        list[ContextArtifact]: Context artifacts ordered by rework event and ID.
    """
    sql = """
        SELECT
          id,
          rework_event_id,
          name,
          artifact_type,
          repo_id,
          team_id,
          last_updated_at,
          summary
        FROM context_artifacts
        ORDER BY rework_event_id, id
    """

    with closing(get_connection()) as conn:
        rows = conn.execute(sql).fetchall()
        return [
            ContextArtifact(
                id=row["id"],
                rework_event_id=row["rework_event_id"],
                name=row["name"],
                artifact_type=row["artifact_type"],
                repo_id=row["repo_id"],
                team_id=row["team_id"],
                last_updated_at=row["last_updated_at"],
                summary=row["summary"],
            )
            for row in rows
        ]


def get_rework_event_detail(rework_event_id: str) -> ReworkEventDetail | None:
    """
    Retrieves comprehensive details for a rework event, including its source pull request.

    Returns:
        ReworkEventDetail | None: A `ReworkEventDetail` object containing the rework event and source pull request details, with optional followup PR and context artifact information; `None` if the rework event is not found.
    """
    sql = """
        SELECT
          re.id AS rework_event_id,
          re.severity,
          re.root_cause_label,
          re.days_after_merge,
          re.human_hours_spent,
          re.summary,

          source_pr.id AS source_pr_id,
          source_pr.number AS source_pr_number,
          source_pr.title AS source_pr_title,
          source_repo.name AS source_repo_name,
          source_pr.ai_assisted AS source_pr_ai_assisted,
          source_pr.ai_tool AS source_pr_ai_tool,

          followup_pr.id AS followup_pr_id,
          followup_pr.number AS followup_pr_number,
          followup_pr.title AS followup_pr_title,
          followup_repo.name AS followup_repo_name,

          artifact.id AS context_artifact_id,
          artifact.name AS context_artifact_name,
          artifact.artifact_type,
          artifact.summary AS context_artifact_summary
        FROM rework_events re
        JOIN pull_requests source_pr
          ON re.source_pr_id = source_pr.id
        JOIN repos source_repo
          ON source_pr.repo_id = source_repo.id
        LEFT JOIN pull_requests followup_pr
          ON re.followup_pr_id = followup_pr.id
        LEFT JOIN repos followup_repo
          ON followup_pr.repo_id = followup_repo.id
        LEFT JOIN context_artifacts artifact
          ON re.id = artifact.rework_event_id
        WHERE re.id = ?
        ORDER BY artifact.id
        LIMIT 1
    """

    with closing(get_connection()) as conn:
        row = conn.execute(sql, (rework_event_id,)).fetchone()

    if row is None:
        return None

    followup_pr = None
    if row["followup_pr_id"] is not None:
        followup_pr = ReworkEventDetailPullRequest(
            id=row["followup_pr_id"],
            number=row["followup_pr_number"],
            title=row["followup_pr_title"],
            repo_name=row["followup_repo_name"],
        )

    context_artifact = None
    if row["context_artifact_id"] is not None:
        context_artifact = ReworkEventDetailContextArtifact(
            id=row["context_artifact_id"],
            name=row["context_artifact_name"],
            artifact_type=row["artifact_type"],
            summary=row["context_artifact_summary"],
        )

    return ReworkEventDetail(
        rework_event=ReworkEventDetailEvent(
            id=row["rework_event_id"],
            severity=row["severity"],
            root_cause_label=row["root_cause_label"],
            days_after_merge=row["days_after_merge"],
            human_hours_spent=row["human_hours_spent"],
            summary=row["summary"],
        ),
        source_pr=ReworkEventDetailPullRequest(
            id=row["source_pr_id"],
            number=row["source_pr_number"],
            title=row["source_pr_title"],
            repo_name=row["source_repo_name"],
            ai_assisted=bool(row["source_pr_ai_assisted"]),
            ai_tool=row["source_pr_ai_tool"],
        ),
        followup_pr=followup_pr,
        context_artifact=context_artifact,
    )
