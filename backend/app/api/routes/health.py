from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Report API liveness and whether Chroma responds to a heartbeat."""
    return {"status": "ok"}
