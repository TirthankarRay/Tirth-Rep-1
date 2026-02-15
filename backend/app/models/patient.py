import uuid
from datetime import date, datetime

from sqlalchemy import String, Date, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Patient(Base):
    __tablename__ = "patients"

    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str | None] = mapped_column(String(50), unique=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(10))
    race_ethnicity: Mapped[str | None] = mapped_column(String(50))
    state: Mapped[str | None] = mapped_column(String(2))
    county: Mapped[str | None] = mapped_column(String(100))
    zip_code: Mapped[str | None] = mapped_column(String(10))
    insurance_type: Mapped[str | None] = mapped_column(String(50))
    urban_rural: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    diagnoses = relationship("Diagnosis", back_populates="patient", lazy="selectin")
    treatment_episodes = relationship("TreatmentEpisode", back_populates="patient", lazy="selectin")
    biomarker_tests = relationship("BiomarkerTest", back_populates="patient", lazy="selectin")
    progression_events = relationship("ProgressionEvent", back_populates="patient", lazy="selectin")
    trial_enrollments = relationship("TrialEnrollment", back_populates="patient", lazy="selectin")
