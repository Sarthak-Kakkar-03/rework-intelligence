from fastapi import APIRouter, HTTPException

from app.queries import (
    get_author_historical_rework_rate,
    get_context_artifacts as query_context_artifacts,
    get_global_rework_rate,
    get_pull_request_by_id,
    get_pull_request_files_by_pr_id,
    get_pull_requests as query_pull_requests,
    get_repos as query_repos,
    get_rework_event_pr_ids,
    get_rework_events as query_rework_events,
    get_rework_event_detail as query_rework_event_detail,
)

from app.api.models import (
    ContextArtifact,
    PullRequest,
    Repo,
    ReworkEvent,
    ReworkEventDetail,
    ReworkFeatures,
)
from app.services.rework_detection.features import compute_rework_features
from app.services.rework_detection.signals import get_overlapping_files

router = APIRouter(prefix="/api", tags=["Engineering Data"])


@router.get("/pull-requests", response_model=list[PullRequest])
def get_pull_requests() -> list[PullRequest]:
    """
    Retrieve all pull requests.

    Returns:
        list[PullRequest]: A list of all pull requests.
    """
    return query_pull_requests()


@router.get("/repos", response_model=list[Repo])
def get_repos() -> list[Repo]:
    """
    Retrieve all repositories.
    """
    return query_repos()


@router.get("/rework-events", response_model=list[ReworkEvent])
def get_rework_events() -> list[ReworkEvent]:
    """
    Retrieve all rework events.

    Returns:
        list[ReworkEvent]: A list of ReworkEvent objects.
    """
    return query_rework_events()


@router.get("/context-artifacts", response_model=list[ContextArtifact])
def get_context_artifacts() -> list[ContextArtifact]:
    """
    Retrieve context artifacts.
    """
    return query_context_artifacts()


@router.get("/rework-events/{rework_id}", response_model=ReworkEventDetail)
def get_rework_event_detail(rework_id: str) -> ReworkEventDetail:
    """
    Retrieve details about a rework event.

    Parameters:
        rework_id (str): The identifier of the rework event to retrieve

    Returns:
        detail (ReworkEventDetail): The requested rework event's details

    Raises:
        HTTPException: With status code 404 if the rework event is not found
    """
    detail = query_rework_event_detail(rework_event_id=rework_id)

    if detail is None:
        raise HTTPException(status_code=404, detail="Rework event not found")

    return detail


@router.get("/rework-events/{rework_id}/features", response_model=ReworkFeatures)
def get_rework_event_features(rework_id: str) -> ReworkFeatures:
    """
    Recompute the explainable feature vector for a rework event on demand.

    Features are derived from the current source/follow-up pull requests and
    changed files rather than persisted, so this always reflects live data.

    Raises:
        HTTPException: With status code 404 if the rework event is not found.
    """
    pr_ids = get_rework_event_pr_ids(rework_event_id=rework_id)

    if pr_ids is None:
        raise HTTPException(status_code=404, detail="Rework event not found")

    source_pr_id, followup_pr_id = pr_ids
    source_pr = get_pull_request_by_id(source_pr_id)
    followup_pr = get_pull_request_by_id(followup_pr_id)

    if source_pr is None or followup_pr is None:
        raise HTTPException(status_code=404, detail="Rework event not found")

    source_files = get_pull_request_files_by_pr_id(source_pr_id)
    followup_files = get_pull_request_files_by_pr_id(followup_pr_id)
    overlapping_files = get_overlapping_files(
        source_files=source_files,
        followup_files=followup_files,
    )
    author_historical_rework_rate = get_author_historical_rework_rate(
        author_login=source_pr.author_login,
        before=source_pr.closed_at,
        prior=get_global_rework_rate(),
    )

    return compute_rework_features(
        source_pr=source_pr,
        followup_pr=followup_pr,
        source_files=source_files,
        followup_files=followup_files,
        overlapping_files=overlapping_files,
        author_historical_rework_rate=author_historical_rework_rate,
    )
