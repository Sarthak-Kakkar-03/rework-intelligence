from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """
    Verify the API is running.
    
    Returns:
    	dict[str, str]: A status dictionary with "status" set to "ok".
    """
    return {"status": "ok"}
