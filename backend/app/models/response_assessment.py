import uuid
from datetime import date, datetime

from sqlalchemy import String, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ResponseAssessment(Base):
    __tablename__ = "response_assessments"

    assessment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    episode_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("treatment_episodes.episode_id"))
    assessment_date: Mapped[date | None] = mapped_column(Date)
    response_type: Mapped[str | None] = mapped_column(String(50))  # 'CR', 'PR', 'SD', 'PD'
    assessment_method: Mapped[str | None] = mapped_column(String(50))  # 'CT', 'PET-CT', 'Clinical'
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    episode = relationship("TreatmentEpisode", back_populates="response_assessments")
