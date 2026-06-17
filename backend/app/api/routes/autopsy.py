from fastapi import APIRouter

from app import queries

router = APIRouter(prefix="/api/autopsy", tags=["Autopsy"])


@router.get("/summary")
def get_autopsy_summary() -> dict:
    return queries.get_autopsy_summary()
