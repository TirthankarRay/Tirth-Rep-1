from pydantic import BaseModel


class OverviewMetrics(BaseModel):
    total_patients: int
    new_diagnoses_mtd: int
    new_diagnoses_qtd: int
    new_diagnoses_ytd: int
    median_time_to_treatment_days: float | None
    biomarker_testing_rate: float
    immunotherapy_uptake_rate: float
    clinical_trial_enrollment_rate: float


class TimeToTreatmentBucket(BaseModel):
    bucket: str
    count: int
    percentage: float


class TimeToTreatmentResponse(BaseModel):
    distribution: list[TimeToTreatmentBucket]
    median_days: float | None
    mean_days: float | None
    target_days: int = 21
    within_target_rate: float


class TreatmentPatternItem(BaseModel):
    regimen_category: str
    count: int
    percentage: float


class TreatmentPatternsResponse(BaseModel):
    first_line: list[TreatmentPatternItem]
    second_line: list[TreatmentPatternItem]
    total_episodes: int


class StateMetric(BaseModel):
    state: str
    patient_count: int
    median_time_to_treatment: float | None = None
    biomarker_testing_rate: float | None = None
    immunotherapy_uptake_rate: float | None = None


class GeographicResponse(BaseModel):
    states: list[StateMetric]


class SankeyNode(BaseModel):
    id: str
    label: str
    count: int


class SankeyLink(BaseModel):
    source: str
    target: str
    value: int


class SankeyResponse(BaseModel):
    nodes: list[SankeyNode]
    links: list[SankeyLink]
