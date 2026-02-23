-- =============================================================================
-- SCLC Patient Journey Dashboard — Fact Tables
-- =============================================================================
-- File:        03_fact_tables.sql
-- Description: Creates fact tables in the sclc_core schema.  Each table
--              captures a distinct clinical event in the SCLC patient
--              journey: diagnosis, treatment episodes, response assessments,
--              biomarker tests, progression events, and trial enrollments.
-- Target:      Amazon Redshift
-- Prerequisites: 01_create_schemas.sql, 02_dimension_tables.sql
--
-- Design notes
-- ~~~~~~~~~~~~
-- * All fact tables use DISTKEY(patient_id) to co-locate patient-centric
--   joins across slices and avoid redistribution at query time.
-- * SORTKEY is set to the primary event date of each table for efficient
--   range-restricted scans.
-- * Foreign-key constraints are declarative (informational) in Redshift;
--   they are not enforced but help the query planner.
-- =============================================================================

SET search_path TO sclc_core, public;

-- ---------------------------------------------------------------------------
-- fact_diagnosis
-- ---------------------------------------------------------------------------
-- One row per unique SCLC diagnosis event.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sclc_core.fact_diagnosis
(
    diagnosis_id        VARCHAR(36)     NOT NULL    ENCODE zstd,
    patient_id          VARCHAR(36)     NOT NULL    ENCODE zstd,
    diagnosis_date      DATE            NOT NULL    ENCODE delta32k,
    diagnosis_date_key  INTEGER                     ENCODE az64,
    stage               VARCHAR(20)                 ENCODE bytedict,   -- LS-SCLC, ES-SCLC
    histology           VARCHAR(100)                ENCODE zstd,
    ecog_status         INTEGER                     ENCODE az64,       -- 0-5
    smoking_status      VARCHAR(50)                 ENCODE bytedict,
    facility_id         VARCHAR(36)                 ENCODE zstd,
    physician_id        VARCHAR(36)                 ENCODE zstd,

    PRIMARY KEY (diagnosis_id),

    FOREIGN KEY (patient_id)         REFERENCES sclc_core.dim_patient (patient_id),
    FOREIGN KEY (diagnosis_date_key) REFERENCES sclc_core.dim_date (date_key),
    FOREIGN KEY (facility_id)        REFERENCES sclc_core.dim_facility (facility_id),

    CHECK (ecog_status >= 0 AND ecog_status <= 5)
)
DISTKEY (patient_id)
COMPOUND SORTKEY (diagnosis_date);

COMMENT ON TABLE sclc_core.fact_diagnosis IS
    'Fact table — one row per SCLC diagnosis event capturing stage, '
    'histology, ECOG performance status, and diagnosing facility.';

-- ---------------------------------------------------------------------------
-- fact_treatment_episode
-- ---------------------------------------------------------------------------
-- One row per treatment episode (a contiguous period on a given regimen
-- within a specific line of therapy).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sclc_core.fact_treatment_episode
(
    episode_id              VARCHAR(36)     NOT NULL    ENCODE zstd,
    patient_id              VARCHAR(36)     NOT NULL    ENCODE zstd,
    line_of_therapy         VARCHAR(20)                 ENCODE bytedict,   -- '1st line', '2nd line', '3rd line+'
    treatment_start_date    DATE            NOT NULL    ENCODE delta32k,
    treatment_end_date      DATE                        ENCODE delta32k,
    start_date_key          INTEGER                     ENCODE az64,
    regimen_name            VARCHAR(200)    NOT NULL    ENCODE zstd,
    regimen_category        VARCHAR(50)                 ENCODE bytedict,   -- 'Chemo+IO', 'Chemo Only', 'IO Monotherapy', 'Targeted', 'Other'
    includes_immunotherapy  BOOLEAN         DEFAULT FALSE  ENCODE raw,
    facility_id             VARCHAR(36)                 ENCODE zstd,
    physician_id            VARCHAR(36)                 ENCODE zstd,

    PRIMARY KEY (episode_id),

    FOREIGN KEY (patient_id)     REFERENCES sclc_core.dim_patient (patient_id),
    FOREIGN KEY (start_date_key) REFERENCES sclc_core.dim_date (date_key),
    FOREIGN KEY (facility_id)    REFERENCES sclc_core.dim_facility (facility_id)
)
DISTKEY (patient_id)
COMPOUND SORTKEY (treatment_start_date);

COMMENT ON TABLE sclc_core.fact_treatment_episode IS
    'Fact table — one row per treatment episode with regimen details, '
    'line of therapy, immunotherapy flag, and treating facility.';

-- ---------------------------------------------------------------------------
-- fact_response_assessment
-- ---------------------------------------------------------------------------
-- One row per RECIST / clinical response assessment tied to a treatment
-- episode.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sclc_core.fact_response_assessment
(
    assessment_id       VARCHAR(36)     NOT NULL    ENCODE zstd,
    episode_id          VARCHAR(36)     NOT NULL    ENCODE zstd,
    patient_id          VARCHAR(36)     NOT NULL    ENCODE zstd,
    assessment_date     DATE            NOT NULL    ENCODE delta32k,
    assessment_date_key INTEGER                     ENCODE az64,
    response_type       VARCHAR(20)                 ENCODE bytedict,   -- CR, PR, SD, PD
    assessment_method   VARCHAR(50)                 ENCODE bytedict,   -- CT, PET-CT, Clinical

    PRIMARY KEY (assessment_id),

    FOREIGN KEY (episode_id)          REFERENCES sclc_core.fact_treatment_episode (episode_id),
    FOREIGN KEY (patient_id)          REFERENCES sclc_core.dim_patient (patient_id),
    FOREIGN KEY (assessment_date_key) REFERENCES sclc_core.dim_date (date_key)
)
DISTKEY (patient_id)
COMPOUND SORTKEY (assessment_date);

COMMENT ON TABLE sclc_core.fact_response_assessment IS
    'Fact table — RECIST response assessments (CR/PR/SD/PD) linked to '
    'treatment episodes.';

-- ---------------------------------------------------------------------------
-- fact_biomarker_test
-- ---------------------------------------------------------------------------
-- One row per biomarker test ordered for a patient (PD-L1, TMB, NGS panel).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sclc_core.fact_biomarker_test
(
    test_id             VARCHAR(36)     NOT NULL    ENCODE zstd,
    patient_id          VARCHAR(36)     NOT NULL    ENCODE zstd,
    test_date           DATE            NOT NULL    ENCODE delta32k,
    test_date_key       INTEGER                     ENCODE az64,
    result_date         DATE                        ENCODE delta32k,
    biomarker_type      VARCHAR(50)                 ENCODE bytedict,   -- PD-L1, TMB, NGS
    test_result         VARCHAR(100)                ENCODE zstd,
    pdl1_percentage     DECIMAL(5,2)                ENCODE az64,
    tmb_score           DECIMAL(10,2)               ENCODE az64,

    PRIMARY KEY (test_id),

    FOREIGN KEY (patient_id)    REFERENCES sclc_core.dim_patient (patient_id),
    FOREIGN KEY (test_date_key) REFERENCES sclc_core.dim_date (date_key)
)
DISTKEY (patient_id)
COMPOUND SORTKEY (test_date);

COMMENT ON TABLE sclc_core.fact_biomarker_test IS
    'Fact table — biomarker tests (PD-L1, TMB, NGS) with quantitative '
    'results for treatment-selection analytics.';

-- ---------------------------------------------------------------------------
-- fact_progression_event
-- ---------------------------------------------------------------------------
-- One row per disease-progression event, capturing progression-free
-- survival days and the anatomical site of progression.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sclc_core.fact_progression_event
(
    event_id                    VARCHAR(36)     NOT NULL    ENCODE zstd,
    patient_id                  VARCHAR(36)     NOT NULL    ENCODE zstd,
    progression_date            DATE            NOT NULL    ENCODE delta32k,
    progression_date_key        INTEGER                     ENCODE az64,
    line_before_progression     VARCHAR(20)                 ENCODE bytedict,
    pfs_days                    INTEGER                     ENCODE az64,
    progression_site            VARCHAR(100)                ENCODE zstd,

    PRIMARY KEY (event_id),

    FOREIGN KEY (patient_id)            REFERENCES sclc_core.dim_patient (patient_id),
    FOREIGN KEY (progression_date_key)  REFERENCES sclc_core.dim_date (date_key)
)
DISTKEY (patient_id)
COMPOUND SORTKEY (progression_date);

COMMENT ON TABLE sclc_core.fact_progression_event IS
    'Fact table — disease-progression events with PFS days and '
    'progression site for survival analytics.';

-- ---------------------------------------------------------------------------
-- fact_trial_enrollment
-- ---------------------------------------------------------------------------
-- One row per clinical-trial enrollment event for a patient.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sclc_core.fact_trial_enrollment
(
    enrollment_id       VARCHAR(36)     NOT NULL    ENCODE zstd,
    patient_id          VARCHAR(36)     NOT NULL    ENCODE zstd,
    trial_id            VARCHAR(100)                ENCODE zstd,
    trial_phase         VARCHAR(20)                 ENCODE bytedict,
    enrollment_date     DATE            NOT NULL    ENCODE delta32k,
    enrollment_date_key INTEGER                     ENCODE az64,
    trial_status        VARCHAR(50)                 ENCODE bytedict,

    PRIMARY KEY (enrollment_id),

    FOREIGN KEY (patient_id)          REFERENCES sclc_core.dim_patient (patient_id),
    FOREIGN KEY (enrollment_date_key) REFERENCES sclc_core.dim_date (date_key)
)
DISTKEY (patient_id)
COMPOUND SORTKEY (enrollment_date);

COMMENT ON TABLE sclc_core.fact_trial_enrollment IS
    'Fact table — clinical-trial enrollment events with trial phase '
    'and status for trial-participation analytics.';
