import uuid
from datetime import date, datetime

from sqlalchemy import String, Date, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ProgressionEvent(Base):
    __tablename__ = "progression_events"

    progression_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.patient_id"))
    progression_date: Mapped[date | None] = mapped_column(Date)
    line_before_progression: Mapped[int | None] = mapped_column(Integer)
    pfs_days: Mapped[int | None] = mapped_column(Integer)
    progression_site: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="progression_events")
