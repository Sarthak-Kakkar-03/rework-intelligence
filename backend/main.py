import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.services.rework_detection.rework_detector import ReworkDetector


def get_cors_allowed_origins() -> list[str]:
    origins = os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001",
    )

    return [origin.strip() for origin in origins.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.rework_detector = ReworkDetector()
    yield


app = FastAPI(title="Rework Autopsy API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
