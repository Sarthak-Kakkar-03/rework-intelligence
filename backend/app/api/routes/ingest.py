import uuid
import sqlite3
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException

from app.api.models import (
    ContextArtifact,
    ContextArtifactCreate,
    PullRequest,
    PullRequestCreate,
)

from app.queries import (
    get_rework_event_repo_team_ids,
    insert_context_artifact,
    insert_pull_request,
)

from random import randint

router = APIRouter(prefix="/api", tags=["Ingest"])


@router.post("/ingest/context-artifact/{rework_id}", response_model=ContextArtifact)
def ingest_context_artifact(
    rework_id: str,
    artifact: ContextArtifactCreate,
) -> ContextArtifact:
    team_repo_id = get_rework_event_repo_team_ids(rework_event_id=rework_id)
    if not team_repo_id:
        raise HTTPException(status_code=404, detail="Rework id not found")
    repo_id, team_id = team_repo_id

    context_artifact = ContextArtifact(
        id=uuid.uuid4().hex,
        rework_event_id=rework_id,
        name=artifact.name,
        artifact_type=artifact.artifact_type,
        repo_id=repo_id,
        team_id=team_id,
        last_updated_at=datetime.now(timezone.utc),
        summary=artifact.summary,
    )

    return insert_context_artifact(context_artifact)


@router.post("/ingest/pull-request", response_model=PullRequest)
def ingest_pull_request(pull_request: PullRequestCreate) -> PullRequest:
    now = datetime.now(timezone.utc)
    pull_request = PullRequest(
        id=randint(1_000_000, 9_999_999),
        number=pull_request.number,
        repo_id=pull_request.repo_id,
        title=pull_request.title,
        body=pull_request.body,
        state="closed",
        draft=0,
        created_at=now - timedelta(hours=15),
        updated_at=now - timedelta(hours=10),
        closed_at=now - timedelta(hours=5),
        merged_at=now,
        merged=1,
        author_login=pull_request.author_login,
        merged_by_login=pull_request.merged_by_login,
        base_branch="main",
        head_branch=pull_request.head_branch,
        additions=randint(1000, 4000),
        deletions=randint(50, 600),
        changed_files=randint(1, 6),
        commits=randint(1, 8),
        comments=randint(2, 20),
        review_comments=randint(3, 9),
        ai_generated=pull_request.ai_generated,
    )

    try:
        return insert_pull_request(pull_request=pull_request)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Pull request could not be created: {exc}",
        ) from exc
