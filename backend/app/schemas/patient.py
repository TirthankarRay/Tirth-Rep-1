from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class PatientBase(BaseModel):
    external_id: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    race_ethnicity: str | None = None
    state: str | None = None
    county: str | None = None
    zip_code: str | None = None
    insurance_type: str | None = None
    urban_rural: str | None = None


class PatientRead(PatientBase):
    patient_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DiagnosisRead(BaseModel):
    diagnosis_id: UUID
    patient_id: UUID
    diagnosis_date: date
    stage: str | None = None
    histology: str | None = None
    ecog_status: int | None = None
    smoking_status: str | None = None

    model_config = {"from_attributes": True}


class TreatmentEpisodeRead(BaseModel):
    episode_id: UUID
    patient_id: UUID
    line_of_therapy: int | None = None
    treatment_start_date: date | None = None
    treatment_end_date: date | None = None
    regimen_name: str | None = None
    regimen_category: str | None = None
    includes_immunotherapy: bool | None = None

    model_config = {"from_attributes": True}


class BiomarkerTestRead(BaseModel):
    test_id: UUID
    patient_id: UUID
    test_date: date | None = None
    result_date: date | None = None
    biomarker_type: str | None = None
    test_result: str | None = None
    pdl1_percentage: float | None = None
    tmb_score: float | None = None

    model_config = {"from_attributes": True}


class PatientDetailRead(PatientBase):
    patient_id: UUID
    created_at: datetime
    updated_at: datetime
    diagnoses: list[DiagnosisRead] = []
    treatment_episodes: list[TreatmentEpisodeRead] = []
    biomarker_tests: list[BiomarkerTestRead] = []

    model_config = {"from_attributes": True}


class PatientListResponse(BaseModel):
    items: list[PatientDetailRead]
    total: int
    page: int
    page_size: int
