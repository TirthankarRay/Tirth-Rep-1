import uuid
from datetime import date, datetime

from sqlalchemy import String, Date, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    diagnosis_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.patient_id"))
    diagnosis_date: Mapped[date] = mapped_column(Date, nullable=False)
    stage: Mapped[str | None] = mapped_column(String(20))  # 'LS-SCLC' or 'ES-SCLC'
    histology: Mapped[str | None] = mapped_column(String(100))
    ecog_status: Mapped[int | None] = mapped_column(Integer)
    smoking_status: Mapped[str | None] = mapped_column(String(50))
    diagnosing_facility_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    diagnosed_by_physician_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="diagnoses")
