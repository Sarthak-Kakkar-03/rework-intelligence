from contextlib import closing

from app.api.models import (
    AutopsySummary,
    ContextRecommendation,
    PullRequest,
    ReworkEvent,
)
from app.db import get_connection


def get_autopsy_summary() -> AutopsySummary:
    """
    Fetch aggregate metrics and entity counts from the database.

    Returns:
        An AutopsySummary containing counts of teams, repos, issues, pull requests, rework events, context artifacts, context recommendations, AI-assisted pull requests, total rework hours, and average days after merge.
    """
    sql = """
        SELECT
          (SELECT COUNT(*) FROM teams) AS team_count,
          (SELECT COUNT(*) FROM repos) AS repo_count,
          (SELECT COUNT(*) FROM issues) AS issue_count,
          (SELECT COUNT(*) FROM pull_requests) AS pull_request_count,
          (SELECT COUNT(*) FROM rework_events) AS rework_event_count,
          (SELECT COUNT(*) FROM context_artifacts) AS context_artifact_count,
          (SELECT COUNT(*) FROM context_recommendations) AS context_recommendation_count,
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
            context_recommendation_count=row["context_recommendation_count"],
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


def get_context_recommendations() -> list[ContextRecommendation]:
    """
    Retrieve all context recommendations, ordered by priority.

    Returns:
        list[ContextRecommendation]: Context recommendations ordered by priority (high, medium, low) and then by ID.
    """
    sql = """
        SELECT
          id,
          rework_event_id,
          recommended_artifact_id,
          missing_context_type,
          priority,
          recommendation,
          reason
        FROM context_recommendations
        ORDER BY
          CASE priority
            WHEN 'high' THEN 1
            WHEN 'medium' THEN 2
            WHEN 'low' THEN 3
            ELSE 4
          END,
          id
    """

    with closing(get_connection()) as conn:
        rows = conn.execute(sql).fetchall()
        return [
            ContextRecommendation(
                id=row["id"],
                rework_event_id=row["rework_event_id"],
                recommended_artifact_id=row["recommended_artifact_id"],
                missing_context_type=row["missing_context_type"],
                priority=row["priority"],
                recommendation=row["recommendation"],
                reason=row["reason"],
            )
            for row in rows
        ]
