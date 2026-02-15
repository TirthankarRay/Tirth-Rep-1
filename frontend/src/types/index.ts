export interface OverviewMetrics {
  total_patients: number;
  new_diagnoses_mtd: number;
  new_diagnoses_qtd: number;
  new_diagnoses_ytd: number;
  median_time_to_treatment_days: number | null;
  biomarker_testing_rate: number;
  immunotherapy_uptake_rate: number;
  clinical_trial_enrollment_rate: number;
}

export interface TimeToTreatmentBucket {
  bucket: string;
  count: number;
  percentage: number;
}

export interface TimeToTreatmentResponse {
  distribution: TimeToTreatmentBucket[];
  median_days: number | null;
  mean_days: number | null;
  target_days: number;
  within_target_rate: number;
}

export interface TreatmentPatternItem {
  regimen_category: string;
  count: number;
  percentage: number;
}

export interface TreatmentPatternsResponse {
  first_line: TreatmentPatternItem[];
  second_line: TreatmentPatternItem[];
  total_episodes: number;
}

export interface StateMetric {
  state: string;
  patient_count: number;
  median_time_to_treatment: number | null;
  biomarker_testing_rate: number | null;
  immunotherapy_uptake_rate: number | null;
}

export interface GeographicResponse {
  states: StateMetric[];
}

export interface Diagnosis {
  diagnosis_id: string;
  patient_id: string;
  diagnosis_date: string;
  stage: string | null;
  histology: string | null;
  ecog_status: number | null;
  smoking_status: string | null;
}

export interface TreatmentEpisode {
  episode_id: string;
  patient_id: string;
  line_of_therapy: number | null;
  treatment_start_date: string | null;
  treatment_end_date: string | null;
  regimen_name: string | null;
  regimen_category: string | null;
  includes_immunotherapy: boolean | null;
}

export interface BiomarkerTest {
  test_id: string;
  patient_id: string;
  test_date: string | null;
  result_date: string | null;
  biomarker_type: string | null;
  test_result: string | null;
  pdl1_percentage: number | null;
  tmb_score: number | null;
}

export interface PatientDetail {
  patient_id: string;
  external_id: string | null;
  date_of_birth: string | null;
  gender: string | null;
  race_ethnicity: string | null;
  state: string | null;
  county: string | null;
  insurance_type: string | null;
  urban_rural: string | null;
  created_at: string;
  updated_at: string;
  diagnoses: Diagnosis[];
  treatment_episodes: TreatmentEpisode[];
  biomarker_tests: BiomarkerTest[];
}

export interface PatientListResponse {
  items: PatientDetail[];
  total: number;
  page: number;
  page_size: number;
}

export interface SankeyNode {
  id: string;
  label: string;
  count: number;
}

export interface SankeyLink {
  source: string;
  target: string;
  value: number;
}

export interface SankeyResponse {
  nodes: SankeyNode[];
  links: SankeyLink[];
}

export interface Filters {
  stage: string | null;
  state: string | null;
  lineOfTherapy: number | null;
  insuranceType: string | null;
}
