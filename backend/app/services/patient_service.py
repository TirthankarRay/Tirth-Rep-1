from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.patient import Patient
from app.models.diagnosis import Diagnosis
from app.schemas.patient import PatientDetailRead, PatientListResponse


async def get_patients(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 25,
    stage: str | None = None,
    state: str | None = None,
    insurance_type: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> PatientListResponse:
    q = (
        select(Patient)
        .options(
            selectinload(Patient.diagnoses),
            selectinload(Patient.treatment_episodes),
            selectinload(Patient.biomarker_tests),
        )
    )

    count_q = select(func.count()).select_from(Patient)

    if stage:
        q = q.join(Diagnosis, Patient.patient_id == Diagnosis.patient_id).where(Diagnosis.stage == stage)
        count_q = count_q.join(Diagnosis, Patient.patient_id == Diagnosis.patient_id).where(Diagnosis.stage == stage)
    if state:
        q = q.where(Patient.state == state)
        count_q = count_q.where(Patient.state == state)
    if insurance_type:
        q = q.where(Patient.insurance_type == insurance_type)
        count_q = count_q.where(Patient.insurance_type == insurance_type)

    sort_col = getattr(Patient, sort_by, Patient.created_at)
    if sort_order == "asc":
        q = q.order_by(sort_col.asc())
    else:
        q = q.order_by(sort_col.desc())

    r = await db.execute(count_q)
    total = r.scalar() or 0

    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    patients = result.scalars().unique().all()

    return PatientListResponse(
        items=[PatientDetailRead.model_validate(p) for p in patients],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_patient_by_id(db: AsyncSession, patient_id: UUID) -> Patient | None:
    q = (
        select(Patient)
        .options(
            selectinload(Patient.diagnoses),
            selectinload(Patient.treatment_episodes),
            selectinload(Patient.biomarker_tests),
            selectinload(Patient.progression_events),
            selectinload(Patient.trial_enrollments),
        )
        .where(Patient.patient_id == patient_id)
    )
    result = await db.execute(q)
    return result.scalars().first()
