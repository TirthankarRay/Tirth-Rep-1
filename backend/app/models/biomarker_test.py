import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import String, Date, DateTime, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class BiomarkerTest(Base):
    __tablename__ = "biomarker_tests"

    test_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.patient_id"))
    test_date: Mapped[date | None] = mapped_column(Date)
    result_date: Mapped[date | None] = mapped_column(Date)
    biomarker_type: Mapped[str | None] = mapped_column(String(50))  # 'PD-L1', 'TMB', 'NGS'
    test_result: Mapped[str | None] = mapped_column(String(100))
    pdl1_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    tmb_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    testing_facility_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="biomarker_tests")
