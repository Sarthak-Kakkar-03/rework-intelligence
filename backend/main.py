from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(title="Rework Autopsy API")

app.include_router(router)