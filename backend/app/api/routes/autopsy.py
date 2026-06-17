from fastapi import APIRouter

from app import queries
from app.api.models import AutopsySummary

router = APIRouter(prefix="/api/autopsy", tags=["Autopsy"])


@router.get("/summary", response_model=AutopsySummary)
def get_autopsy_summary() -> AutopsySummary:
    """
    Retrieve the autopsy summary.
    
    Returns:
    	AutopsySummary: The autopsy summary data.
    """
    return queries.get_autopsy_summary()
