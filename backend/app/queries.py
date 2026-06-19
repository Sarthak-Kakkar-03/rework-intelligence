from contextlib import closing

from app.api.models import (
    AutopsySummary,
    ContextArtifact,
    PullRequest,
    PullRequestFile,
    ReworkEvent,
    ReworkEventDetail,
    ReworkEventDetailContextArtifact,
    ReworkEventDetailEvent,
    ReworkEventDetailPullRequest,
)
from app.db import get_connection
from app.services.rework_detection.models import ReworkCandidate


def get_autopsy_summary() -> AutopsySummary:
    """
    Fetch aggregate metrics and entity counts from the database.

    Returns:
        An AutopsySummary containing counts of teams, repos, pull requests, rework events, context artifacts, AI-generated pull requests, total rework hours, and average days after merge.
    """
    sql = """
        SELECT
          (SELECT COUNT(*) FROM teams) AS team_count,
          (SELECT COUNT(*) FROM repos) AS repo_count,
          (SELECT COUNT(*) FROM pull_requests) AS pull_request_count,
          (SELECT COUNT(*) FROM rework_events) AS rework_event_count,
          (SELECT COUNT(*) FROM context_artifacts) AS context_artifact_count,
          (SELECT COUNT(*) FROM pull_requests WHERE ai_generated = 1) AS ai_generated_pr_count,
          COALESCE((SELECT SUM(human_hours_spent) FROM rework_events), 0) AS total_rework_hours,
          COALESCE((SELECT ROUND(AVG(days_after_merge), 1) FROM rework_events), 0) AS avg_days_after_merge
    """

    with closing(get_connection()) as conn:
        row = conn.execute(sql).fetchone()
        return AutopsySummary(
            team_count=row["team_count"],
            repo_count=row["repo_count"],
            pull_request_count=row["pull_request_count"],
            rework_event_count=row["rework_event_count"],
            context_artifact_count=row["context_artifact_count"],
            ai_generated_pr_count=row["ai_generated_pr_count"],
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
          ai_generated
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
                ai_generated=bool(row["ai_generated"]),
            )
            for row in rows
        ]


def get_pull_requests_ordered_by_closed_at() -> list[PullRequest]:
    """
    Retrieves pull request records ordered by closure time for rework detection.

    Returns:
        A list of PullRequest objects, ordered by closed_at ascending, then by ID.
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
          ai_generated
        FROM pull_requests
        ORDER BY datetime(closed_at) ASC, id ASC
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
                ai_generated=bool(row["ai_generated"]),
            )
            for row in rows
        ]


def get_pull_request_files() -> list[PullRequestFile]:
    """
    Retrieves all changed-file records for pull requests.

    Returns:
        A list of PullRequestFile objects ordered by pull request and file path.
    """
    sql = """
        SELECT
          id,
          pull_request_id,
          file_path,
          additions,
          deletions
        FROM pull_request_files
        ORDER BY pull_request_id, file_path
    """

    with closing(get_connection()) as conn:
        rows = conn.execute(sql).fetchall()
        return [
            PullRequestFile(
                id=row["id"],
                pull_request_id=row["pull_request_id"],
                file_path=row["file_path"],
                additions=row["additions"],
                deletions=row["deletions"],
            )
            for row in rows
        ]


def get_pull_request_files_by_pr_id(pull_request_id: int) -> list[PullRequestFile]:
    """
    Retrieves changed-file records for one pull request.

    Returns:
        A list of PullRequestFile objects ordered by file path.
    """
    sql = """
        SELECT
          id,
          pull_request_id,
          file_path,
          additions,
          deletions
        FROM pull_request_files
        WHERE pull_request_id = ?
        ORDER BY file_path
    """

    with closing(get_connection()) as conn:
        rows = conn.execute(sql, (pull_request_id,)).fetchall()
        return [
            PullRequestFile(
                id=row["id"],
                pull_request_id=row["pull_request_id"],
                file_path=row["file_path"],
                additions=row["additions"],
                deletions=row["deletions"],
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


def clear_rework_events() -> None:
    """
    Deletes all computed rework events and their dependent context artifacts.
    """
    with closing(get_connection()) as conn:
        conn.execute("DELETE FROM context_artifacts")
        conn.execute("DELETE FROM rework_events")
        conn.commit()


def insert_rework_candidates(rework_candidates: list[ReworkCandidate]) -> None:
    """
    Inserts detected rework candidates into the rework_events table.
    """
    sql = """
        INSERT INTO rework_events (
          id,
          source_pr_id,
          followup_pr_id,
          detected_from,
          rework_type,
          severity,
          days_after_merge,
          human_hours_spent,
          root_cause_label,
          summary
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    values = [
        (
            f"RW-{index + 1:03d}",
            candidate.source_pr_id,
            candidate.followup_pr_id,
            "detector",
            "computed_rework",
            candidate.severity,
            candidate.days_after_merge,
            candidate.human_hours_spent,
            candidate.root_cause_label,
            candidate.summary,
        )
        for index, candidate in enumerate(rework_candidates)
    ]

    with closing(get_connection()) as conn:
        conn.executemany(sql, values)
        conn.commit()


def replace_rework_events(rework_candidates: list[ReworkCandidate]) -> None:
    """
    Replaces rework events with detected candidates in one transaction.
    """
    sql = """
        INSERT INTO rework_events (
          id,
          source_pr_id,
          followup_pr_id,
          detected_from,
          rework_type,
          severity,
          days_after_merge,
          human_hours_spent,
          root_cause_label,
          summary
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    values = [
        (
            f"RW-{index + 1:03d}",
            candidate.source_pr_id,
            candidate.followup_pr_id,
            "detector",
            "computed_rework",
            candidate.severity,
            candidate.days_after_merge,
            candidate.human_hours_spent,
            candidate.root_cause_label,
            candidate.summary,
        )
        for index, candidate in enumerate(rework_candidates)
    ]

    with closing(get_connection()) as conn:
        try:
            conn.execute("BEGIN")
            conn.execute("DELETE FROM context_artifacts")
            conn.execute("DELETE FROM rework_events")
            conn.executemany(sql, values)
            conn.commit()
        except Exception:
            conn.rollback()
            raise


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
        ORDER BY datetime(last_updated_at) DESC, id DESC
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


def get_rework_event_repo_team_ids(rework_event_id: str) -> tuple[str, str] | None:
    sql = """
        SELECT
          repo.id AS repo_id,
          repo.team_id AS team_id
        FROM rework_events re
        JOIN pull_requests source_pr
          ON re.source_pr_id = source_pr.id
        JOIN repos repo
          ON source_pr.repo_id = repo.id
        WHERE re.id = ?
    """

    with closing(get_connection()) as conn:
        row = conn.execute(sql, (rework_event_id,)).fetchone()

    if row is None:
        return None

    return row["repo_id"], row["team_id"]


def insert_context_artifact(context_artifact: ContextArtifact) -> ContextArtifact:
    sql = """
        INSERT INTO context_artifacts (
          id,
          rework_event_id,
          name,
          artifact_type,
          repo_id,
          team_id,
          last_updated_at,
          summary
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """

    with closing(get_connection()) as conn:
        conn.execute(
            sql,
            (
                context_artifact.id,
                context_artifact.rework_event_id,
                context_artifact.name,
                context_artifact.artifact_type,
                context_artifact.repo_id,
                context_artifact.team_id,
                context_artifact.last_updated_at.isoformat()
                if context_artifact.last_updated_at
                else None,
                context_artifact.summary,
            ),
        )
        conn.commit()

    return context_artifact


def insert_pull_request(pull_request: PullRequest) -> PullRequest:
    sql = """
        INSERT INTO pull_requests (
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
          ai_generated
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    with closing(get_connection()) as conn:
        conn.execute(
            sql,
            (
                pull_request.id,
                pull_request.number,
                pull_request.repo_id,
                pull_request.title,
                pull_request.body,
                pull_request.state,
                int(pull_request.draft),
                pull_request.created_at.isoformat(),
                pull_request.updated_at.isoformat(),
                pull_request.closed_at.isoformat(),
                pull_request.merged_at.isoformat() if pull_request.merged_at else None,
                int(pull_request.merged),
                pull_request.author_login,
                pull_request.merged_by_login,
                pull_request.base_branch,
                pull_request.head_branch,
                pull_request.additions,
                pull_request.deletions,
                pull_request.changed_files,
                pull_request.commits,
                pull_request.comments,
                pull_request.review_comments,
                int(pull_request.ai_generated),
            ),
        )
        conn.commit()

    return pull_request


def get_rework_event_detail(rework_event_id: str) -> ReworkEventDetail | None:
    """
    Retrieves comprehensive details for a rework event, including its source pull request.

    Returns:
        ReworkEventDetail | None: A `ReworkEventDetail` object containing the rework event, source pull request, followup pull request, and context artifact information; `None` if the rework event is not found.
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
          source_pr.ai_generated AS source_pr_ai_generated,

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
        JOIN pull_requests followup_pr
          ON re.followup_pr_id = followup_pr.id
        JOIN repos followup_repo
          ON followup_pr.repo_id = followup_repo.id
        LEFT JOIN context_artifacts artifact
          ON re.id = artifact.rework_event_id
        WHERE re.id = ?
        ORDER BY artifact.id
    """

    with closing(get_connection()) as conn:
        rows = conn.execute(sql, (rework_event_id,)).fetchall()

    if not rows:
        return None

    row = rows[0]

    context_artifacts = [
        ReworkEventDetailContextArtifact(
            id=artifact_row["context_artifact_id"],
            name=artifact_row["context_artifact_name"],
            artifact_type=artifact_row["artifact_type"],
            summary=artifact_row["context_artifact_summary"],
        )
        for artifact_row in rows
        if artifact_row["context_artifact_id"] is not None
    ]

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
            ai_generated=bool(row["source_pr_ai_generated"]),
        ),
        followup_pr=ReworkEventDetailPullRequest(
            id=row["followup_pr_id"],
            number=row["followup_pr_number"],
            title=row["followup_pr_title"],
            repo_name=row["followup_repo_name"],
        ),
        context_artifacts=context_artifacts,
    )


def change_rework_root_cause_by_id(
    rework_id: str,
    root_cause: str,
) -> ReworkEventDetail | None:
    sql = """
        UPDATE rework_events
        SET root_cause_label = ?
        WHERE id = ?
    """

    with closing(get_connection()) as conn:
        cursor = conn.execute(sql, (root_cause, rework_id))
        conn.commit()

    if cursor.rowcount == 0:
        return None

    return get_rework_event_detail(rework_event_id=rework_id)
