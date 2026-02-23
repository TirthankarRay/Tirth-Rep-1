-- =============================================================================
-- SCLC Patient Journey Dashboard — Materialized Views
-- =============================================================================
-- File:        05_materialized_views.sql
-- Description: Creates materialized views that pre-compute common query
--              patterns.  These views should be refreshed on a schedule
--              (e.g., after each ETL run) using REFRESH MATERIALIZED VIEW.
-- Target:      Amazon Redshift
-- Prerequisites: 01_create_schemas.sql, 02_dimension_tables.sql,
--                03_fact_tables.sql, 04_aggregation_tables.sql
-- =============================================================================

-- ---------------------------------------------------------------------------
-- mv_patient_latest_status
-- ---------------------------------------------------------------------------
-- Provides the most recent stage, treatment, and facility for every patient
-- in a single flat row.  Useful for patient-list pages, quick look-ups, and
-- filter counts.
--
-- Refresh cadence: after every ETL load into sclc_core fact tables.
-- ---------------------------------------------------------------------------
CREATE MATERIALIZED VIEW sclc_core.mv_patient_latest_status AS
SELECT
    p.patient_id,
    p.external_id,
    p.gender,
    p.race_ethnicity,
    p.state                         AS patient_state,
    p.insurance_type,
    p.urban_rural,

    -- Latest diagnosis info
    dx.diagnosis_date               AS latest_diagnosis_date,
    dx.stage                        AS current_stage,
    dx.ecog_status                  AS latest_ecog_status,
    dx.histology,
    dx.smoking_status,

    -- Latest treatment info
    tx.episode_id                   AS latest_episode_id,
    tx.line_of_therapy              AS current_line_of_therapy,
    tx.treatment_start_date         AS latest_treatment_start_date,
    tx.treatment_end_date           AS latest_treatment_end_date,
    tx.regimen_name                 AS current_regimen_name,
    tx.regimen_category             AS current_regimen_category,
    tx.includes_immunotherapy       AS on_immunotherapy,

    -- Days from diagnosis to first treatment
    DATEDIFF(day, first_tx.first_treatment_date, dx.diagnosis_date) * -1
                                    AS days_to_first_treatment,

    -- Latest facility
    f.facility_id,
    f.facility_name,
    f.facility_type,

    -- Trial enrollment flag
    CASE WHEN te.enrollment_id IS NOT NULL THEN TRUE ELSE FALSE END
                                    AS enrolled_in_trial,

    -- Biomarker testing flag
    CASE WHEN bm.test_id IS NOT NULL THEN TRUE ELSE FALSE END
                                    AS has_biomarker_test

FROM sclc_core.dim_patient p

-- Latest diagnosis (most recent diagnosis_date per patient)
LEFT JOIN (
    SELECT
        patient_id,
        diagnosis_date,
        stage,
        ecog_status,
        histology,
        smoking_status,
        facility_id,
        ROW_NUMBER() OVER (PARTITION BY patient_id ORDER BY diagnosis_date DESC) AS rn
    FROM sclc_core.fact_diagnosis
) dx ON dx.patient_id = p.patient_id AND dx.rn = 1

-- Latest treatment episode (most recent treatment_start_date per patient)
LEFT JOIN (
    SELECT
        episode_id,
        patient_id,
        line_of_therapy,
        treatment_start_date,
        treatment_end_date,
        regimen_name,
        regimen_category,
        includes_immunotherapy,
        facility_id,
        ROW_NUMBER() OVER (PARTITION BY patient_id ORDER BY treatment_start_date DESC) AS rn
    FROM sclc_core.fact_treatment_episode
) tx ON tx.patient_id = p.patient_id AND tx.rn = 1

-- First treatment date (for time-to-treatment calculation)
LEFT JOIN (
    SELECT
        patient_id,
        MIN(treatment_start_date) AS first_treatment_date
    FROM sclc_core.fact_treatment_episode
    GROUP BY patient_id
) first_tx ON first_tx.patient_id = p.patient_id

-- Facility from latest treatment (fallback to diagnosis facility)
LEFT JOIN sclc_core.dim_facility f
    ON f.facility_id = COALESCE(tx.facility_id, dx.facility_id)

-- Any active trial enrollment
LEFT JOIN (
    SELECT
        enrollment_id,
        patient_id,
        ROW_NUMBER() OVER (PARTITION BY patient_id ORDER BY enrollment_date DESC) AS rn
    FROM sclc_core.fact_trial_enrollment
) te ON te.patient_id = p.patient_id AND te.rn = 1

-- Any biomarker test
LEFT JOIN (
    SELECT
        test_id,
        patient_id,
        ROW_NUMBER() OVER (PARTITION BY patient_id ORDER BY test_date DESC) AS rn
    FROM sclc_core.fact_biomarker_test
) bm ON bm.patient_id = p.patient_id AND bm.rn = 1;

COMMENT ON MATERIALIZED VIEW sclc_core.mv_patient_latest_status IS
    'Flat, denormalized view of every patient with their most recent '
    'diagnosis, treatment, facility, trial-enrollment flag, and biomarker '
    'testing flag.  Refresh after each ETL load.';


-- ---------------------------------------------------------------------------
-- mv_treatment_timeline
-- ---------------------------------------------------------------------------
-- Flat view that joins patient demographics with diagnosis, treatment
-- episode, and response assessment data.  Designed for timeline
-- visualisations and drill-down queries.
--
-- Refresh cadence: after every ETL load.
-- ---------------------------------------------------------------------------
CREATE MATERIALIZED VIEW sclc_core.mv_treatment_timeline AS
SELECT
    p.patient_id,
    p.external_id,
    p.gender,
    p.state                         AS patient_state,
    p.insurance_type,

    -- Diagnosis
    dx.diagnosis_id,
    dx.diagnosis_date,
    dx.stage,
    dx.histology,
    dx.ecog_status,

    -- Treatment episode
    te.episode_id,
    te.line_of_therapy,
    te.treatment_start_date,
    te.treatment_end_date,
    te.regimen_name,
    te.regimen_category,
    te.includes_immunotherapy,
    DATEDIFF(day, dx.diagnosis_date, te.treatment_start_date)
                                    AS days_from_diagnosis_to_treatment,
    DATEDIFF(day, te.treatment_start_date, te.treatment_end_date)
                                    AS treatment_duration_days,

    -- Facility
    f.facility_name,
    f.facility_type,

    -- Best response for the episode
    ra.assessment_date              AS response_date,
    ra.response_type,
    ra.assessment_method

FROM sclc_core.dim_patient p

INNER JOIN sclc_core.fact_diagnosis dx
    ON dx.patient_id = p.patient_id

LEFT JOIN sclc_core.fact_treatment_episode te
    ON te.patient_id = p.patient_id

LEFT JOIN sclc_core.dim_facility f
    ON f.facility_id = COALESCE(te.facility_id, dx.facility_id)

-- Best response per episode (CR > PR > SD > PD ordering via CASE)
LEFT JOIN (
    SELECT
        assessment_id,
        episode_id,
        patient_id,
        assessment_date,
        response_type,
        assessment_method,
        ROW_NUMBER() OVER (
            PARTITION BY episode_id
            ORDER BY
                CASE response_type
                    WHEN 'CR' THEN 1
                    WHEN 'PR' THEN 2
                    WHEN 'SD' THEN 3
                    WHEN 'PD' THEN 4
                    ELSE 5
                END,
                assessment_date DESC
        ) AS rn
    FROM sclc_core.fact_response_assessment
) ra ON ra.episode_id = te.episode_id AND ra.rn = 1;

COMMENT ON MATERIALIZED VIEW sclc_core.mv_treatment_timeline IS
    'Flat join of patient + diagnosis + treatment episode + best response. '
    'Supports timeline visualisations and drill-down analysis.  '
    'Refresh after each ETL load.';


-- ---------------------------------------------------------------------------
-- mv_kpi_current
-- ---------------------------------------------------------------------------
-- Returns only the most recent snapshot from agg_overview_metrics.  The
-- dashboard API queries this view directly to populate the KPI cards
-- without having to filter on snapshot_date.
--
-- Refresh cadence: after agg_overview_metrics is refreshed.
-- ---------------------------------------------------------------------------
CREATE MATERIALIZED VIEW sclc_analytics.mv_kpi_current AS
SELECT
    aom.snapshot_date,
    aom.stage_filter,
    aom.state_filter,
    aom.total_patients,
    aom.new_diagnoses_mtd,
    aom.new_diagnoses_qtd,
    aom.new_diagnoses_ytd,
    aom.median_time_to_treatment,
    aom.biomarker_testing_rate,
    aom.immunotherapy_uptake_rate,
    aom.clinical_trial_rate
FROM sclc_analytics.agg_overview_metrics aom
WHERE aom.snapshot_date = (
    SELECT MAX(snapshot_date)
    FROM sclc_analytics.agg_overview_metrics
);

COMMENT ON MATERIALIZED VIEW sclc_analytics.mv_kpi_current IS
    'Latest-snapshot subset of agg_overview_metrics for instant KPI card '
    'queries.  Refresh after each aggregation run.';
