from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.metrics import (
    OverviewMetrics,
    TimeToTreatmentResponse,
    TreatmentPatternsResponse,
)
from app.services.metrics_service import (
    get_overview_metrics,
    get_time_to_treatment,
    get_treatment_patterns,
)

router = APIRouter()


@router.get("/overview", response_model=OverviewMetrics)
async def overview(
    stage: str | None = Query(None, description="Filter by stage: LS-SCLC or ES-SCLC"),
    state: str | None = Query(None, description="Filter by US state code"),
    db: AsyncSession = Depends(get_db),
):
    return await get_overview_metrics(db, stage=stage, state=state)


@router.get("/time-to-treatment", response_model=TimeToTreatmentResponse)
async def time_to_treatment(
    stage: str | None = Query(None),
    state: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await get_time_to_treatment(db, stage=stage, state=state)


@router.get("/treatment-patterns", response_model=TreatmentPatternsResponse)
async def treatment_patterns(
    stage: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await get_treatment_patterns(db, stage=stage)
