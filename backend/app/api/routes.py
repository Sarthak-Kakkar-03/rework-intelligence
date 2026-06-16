from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/autopsy/summary")
def get_autopsy_summary() -> dict[str, str]:
    return {"message": "TODO: return autopsy summary from SQLite"}