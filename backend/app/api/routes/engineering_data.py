from fastapi import APIRouter, HTTPException

from app.queries import (
    get_context_artifacts as query_context_artifacts,
    get_pull_requests as query_pull_requests,
    get_rework_events as query_rework_events,
    get_rework_event_detail as query_rework_event_detail,
)

from app.api.models import (
    ContextArtifact,
    PullRequest,
    ReworkEvent,
    ReworkEventDetail,
)

router = APIRouter(prefix="/api", tags=["Engineering Data"])


@router.get("/pull-requests", response_model=list[PullRequest])
def get_pull_requests() -> list[PullRequest]:
    """
    Retrieve all pull requests.

    Returns:
        list[PullRequest]: A list of all pull requests.
    """
    return query_pull_requests()


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
