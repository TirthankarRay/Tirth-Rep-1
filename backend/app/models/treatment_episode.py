import uuid
from datetime import date, datetime

from sqlalchemy import String, Date, DateTime, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TreatmentEpisode(Base):
    __tablename__ = "treatment_episodes"

    episode_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.patient_id"))
    line_of_therapy: Mapped[int | None] = mapped_column(Integer)
    treatment_start_date: Mapped[date | None] = mapped_column(Date)
    treatment_end_date: Mapped[date | None] = mapped_column(Date)
    regimen_name: Mapped[str | None] = mapped_column(String(200))
    regimen_category: Mapped[str | None] = mapped_column(String(100))  # 'Chemo Only', 'Chemo+IO', etc.
    includes_immunotherapy: Mapped[bool | None] = mapped_column(Boolean)
    treating_facility_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    treating_physician_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="treatment_episodes")
    response_assessments = relationship("ResponseAssessment", back_populates="episode", lazy="selectin")
