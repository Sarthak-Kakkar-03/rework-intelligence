from fastapi import APIRouter

from app.queries import (
    get_context_recommendations as query_context_recommendations,
    get_pull_requests as query_pull_requests,
    get_rework_events as query_rework_events,
)

router = APIRouter(prefix="/api", tags=["Engineering Data"])


@router.get("/pull-requests")
def get_pull_requests() -> list[dict]:
    return query_pull_requests()


@router.get("/rework-events")
def get_rework_events() -> list[dict]:
    return query_rework_events()


@router.get("/context-recommendations")
def get_context_recommendations() -> list[dict]:
    return query_context_recommendations()
