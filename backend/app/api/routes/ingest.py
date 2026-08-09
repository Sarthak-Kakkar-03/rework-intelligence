import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from app.api.models import (
    ContextArtifact,
    ContextArtifactCreate,
    ReworkRecomputeResult,
    ReworkEventDetail,
    ReworkRootCause,
    ReworkDisposition,
)

from app.queries import (
    get_rework_event_repo_team_ids,
    insert_context_artifact,
    replace_rework_events,
    change_rework_root_cause_by_id,
    change_rework_disposition_by_id,
)


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


@router.post("/ingest/rework-events/recompute", response_model=ReworkRecomputeResult)
def recompute_rework_events(request: Request) -> ReworkRecomputeResult:
    detector = request.app.state.rework_detector
    rework_candidates = detector.generate_rework_candidates()
    replace_rework_events(rework_candidates)

    return ReworkRecomputeResult(
        model_used=detector.model_name,
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


@router.post("/ingest/{rework_id}/disposition", response_model=ReworkEventDetail)
def add_disposition(
    rework_id: str,
    disposition: ReworkDisposition,
) -> ReworkEventDetail:
    updated_rework = change_rework_disposition_by_id(
        rework_id=rework_id,
        disposition=disposition.disposition,
    )

    if updated_rework is None:
        raise HTTPException(status_code=404, detail="Rework event not found")

    return updated_rework
