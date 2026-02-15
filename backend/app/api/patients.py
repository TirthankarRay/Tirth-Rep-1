from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.patient import PatientListResponse, PatientDetailRead
from app.services.patient_service import get_patients, get_patient_by_id

router = APIRouter()


@router.get("", response_model=PatientListResponse)
async def list_patients(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    stage: str | None = Query(None),
    state: str | None = Query(None),
    insurance_type: str | None = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
):
    return await get_patients(
        db,
        page=page,
        page_size=page_size,
        stage=stage,
        state=state,
        insurance_type=insurance_type,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/{patient_id}", response_model=PatientDetailRead)
async def get_patient(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    patient = await get_patient_by_id(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return PatientDetailRead.model_validate(patient)
