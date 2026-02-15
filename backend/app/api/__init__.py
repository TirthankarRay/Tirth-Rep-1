from fastapi import APIRouter

from app.api.metrics import router as metrics_router
from app.api.patients import router as patients_router
from app.api.geographic import router as geographic_router
from app.api.journey import router as journey_router

router = APIRouter()
router.include_router(metrics_router, prefix="/metrics", tags=["Metrics"])
router.include_router(patients_router, prefix="/patients", tags=["Patients"])
router.include_router(geographic_router, prefix="/geographic", tags=["Geographic"])
router.include_router(journey_router, prefix="/patients/journey", tags=["Patient Journey"])
