from fastapi import APIRouter

from app.queries import (
    get_context_recommendations as query_context_recommendations,
    get_pull_requests as query_pull_requests,
    get_rework_events as query_rework_events,
)

from app.api.models import ContextRecommendation, PullRequest, ReworkEvent

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


@router.get("/context-recommendations", response_model=list[ContextRecommendation])
def get_context_recommendations() -> list[ContextRecommendation]:
    """
    Retrieve context recommendations.

    Returns:
        A list of context recommendations.
    """
    return query_context_recommendations()
