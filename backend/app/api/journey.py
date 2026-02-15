from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.metrics import SankeyResponse
from app.services.metrics_service import get_sankey_data

router = APIRouter()


@router.get("/sankey", response_model=SankeyResponse)
async def sankey(
    stage: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await get_sankey_data(db, stage=stage)
