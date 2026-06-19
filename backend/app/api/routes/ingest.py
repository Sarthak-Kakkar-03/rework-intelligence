import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.api.models import ContextArtifact, ContextArtifactCreate

from app.queries import get_rework_event_repo_team_ids, insert_context_artifact

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
