from fastapi import APIRouter

from app.api.routes import engineering_data, health, autopsy


router = APIRouter()
router.include_router(health.router)
router.include_router(engineering_data.router)
router.include_router(autopsy.router)
