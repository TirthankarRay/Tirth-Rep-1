from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.metrics import GeographicResponse
from app.services.metrics_service import get_geographic_data

router = APIRouter()


@router.get("/states", response_model=GeographicResponse)
async def states(
    metric_type: str = Query("patient_count"),
    db: AsyncSession = Depends(get_db),
):
    return await get_geographic_data(db, metric_type=metric_type)
