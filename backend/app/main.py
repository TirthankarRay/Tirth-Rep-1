from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router as api_router
from app.db.session import engine
from app.models import base  # noqa: F401 – ensure models are registered

app = FastAPI(
    title="SCLC Patient Journey Dashboard API",
    version="1.0.0",
    description="API for Small Cell Lung Cancer patient journey analytics",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
