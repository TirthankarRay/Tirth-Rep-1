import uuid
from datetime import date, datetime

from sqlalchemy import String, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TrialEnrollment(Base):
    __tablename__ = "trial_enrollments"

    enrollment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.patient_id"))
    trial_id: Mapped[str | None] = mapped_column(String(100))
    trial_phase: Mapped[str | None] = mapped_column(String(10))
    enrollment_date: Mapped[date | None] = mapped_column(Date)
    trial_status: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="trial_enrollments")
