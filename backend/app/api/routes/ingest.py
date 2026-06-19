import uuid
import sqlite3
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException

from app.api.models import (
    ContextArtifact,
    ContextArtifactCreate,
    PullRequest,
    PullRequestCreate,
    PullRequestFile,
    PullRequestFilesCreate,
    PullRequestWithFilesCreate,
    ReworkRecomputeResult,
    ReworkEventDetail,
    ReworkRootCause,
)

from app.queries import (
    get_next_pull_request_number,
    get_rework_event_repo_team_ids,
    insert_context_artifact,
    insert_pull_request,
    insert_pull_request_files,
    insert_pull_request_with_files,
    replace_rework_events,
    change_rework_root_cause_by_id,
)
from app.services.rework_detection.rework_detector import generate_rework_candidates

from random import randint

router = APIRouter(prefix="/api", tags=["Ingest"])
logger = logging.getLogger(__name__)
MAX_PULL_REQUEST_CREATE_ATTEMPTS = 3


def _build_pull_request(
    pull_request: PullRequestCreate,
    pull_request_number: int,
) -> PullRequest:
    """
    Builds a pull request object from creation data.
    
    Constructs a PullRequest with derived timestamp fields based on a closed_at value, which defaults to the current UTC time if not provided in the input. The created_at, updated_at, and merged_at fields are calculated relative to closed_at (15 hours, 10 hours, and 0 hours prior respectively). Random numeric metrics are generated for code changes and review activity.
    
    Parameters:
    	pull_request (PullRequestCreate): The pull request creation data
    	pull_request_number (int): The pull request number to assign
    
    Returns:
    	PullRequest: A fully constructed pull request object with synthetic metrics and derived timestamps
    """
    closed_at = pull_request.closed_at or datetime.now(timezone.utc)
    return PullRequest(
        id=randint(1_000_000, 9_999_999),
        number=pull_request_number,
        repo_id=pull_request.repo_id,
        title=pull_request.title,
        body=pull_request.body,
        state="closed",
        draft=0,
        created_at=closed_at - timedelta(hours=15),
        updated_at=closed_at - timedelta(hours=10),
        closed_at=closed_at,
        merged_at=closed_at,
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
    last_error: sqlite3.IntegrityError | None = None

    for _ in range(MAX_PULL_REQUEST_CREATE_ATTEMPTS):
        pull_request_number = get_next_pull_request_number(
            repo_id=pull_request.repo_id
        )
        new_pull_request = _build_pull_request(
            pull_request=pull_request,
            pull_request_number=pull_request_number,
        )

        try:
            return insert_pull_request(pull_request=new_pull_request)
        except sqlite3.IntegrityError as exc:
            last_error = exc
            logger.exception("Pull request could not be created")

    raise HTTPException(
        status_code=400,
        detail="Pull request could not be created",
    ) from last_error


@router.post(
    "/ingest/pull-request/{pull_request_id}/files",
    response_model=list[PullRequestFile],
)
def ingest_pull_request_files(
    pull_request_id: int,
    files: PullRequestFilesCreate,
) -> list[PullRequestFile]:
    try:
        return insert_pull_request_files(
            pull_request_id=pull_request_id,
            file_paths=files.file_paths,
        )
    except sqlite3.IntegrityError as exc:
        logger.exception("Pull request files could not be created")
        raise HTTPException(
            status_code=400,
            detail="Pull request files could not be created",
        ) from exc


@router.post("/ingest/pull-request-with-files", response_model=PullRequest)
def ingest_pull_request_with_files(
    request: PullRequestWithFilesCreate,
) -> PullRequest:
    last_error: sqlite3.IntegrityError | None = None

    for _ in range(MAX_PULL_REQUEST_CREATE_ATTEMPTS):
        pull_request_number = get_next_pull_request_number(
            repo_id=request.pull_request.repo_id
        )
        pull_request = _build_pull_request(
            pull_request=request.pull_request,
            pull_request_number=pull_request_number,
        )

        try:
            return insert_pull_request_with_files(
                pull_request=pull_request,
                file_paths=request.file_paths,
            )
        except sqlite3.IntegrityError as exc:
            last_error = exc
            logger.exception("Pull request with files could not be created")

    raise HTTPException(
        status_code=400,
        detail="Pull request with files could not be created",
    ) from last_error


@router.post("/ingest/rework-events/recompute", response_model=ReworkRecomputeResult)
def recompute_rework_events() -> ReworkRecomputeResult:
    rework_candidates = generate_rework_candidates()
    replace_rework_events(rework_candidates)

    return ReworkRecomputeResult(
        rework_event_count=len(rework_candidates),
        message=f"Recomputed and inserted {len(rework_candidates)} rework events.",
    )


@router.post("/ingest/{rework_id}/root-cause", response_model=ReworkEventDetail)
def add_root_cause(
    rework_id: str,
    root_cause: ReworkRootCause,
) -> ReworkEventDetail:
    updated_rework = change_rework_root_cause_by_id(
        rework_id=rework_id,
        root_cause=root_cause.root_cause,
    )

    if updated_rework is None:
        raise HTTPException(status_code=404, detail="Rework event not found")

    return updated_rework
