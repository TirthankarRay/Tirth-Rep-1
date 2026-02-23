-- =============================================================================
-- SCLC Patient Journey Dashboard — Pre-Aggregated Analytics Tables
-- =============================================================================
-- File:        04_aggregation_tables.sql
-- Description: Creates snapshot-based aggregation tables in sclc_analytics.
--              These tables are refreshed by the ETL pipeline and serve as
--              the primary data source for the dashboard API, eliminating
--              expensive ad-hoc aggregations at query time.
-- Target:      Amazon Redshift
-- Prerequisites: 01_create_schemas.sql
--
-- Design notes
-- ~~~~~~~~~~~~
-- * Every table carries a snapshot_date column that represents the date on
--   which the aggregation was computed.  The dashboard always reads the
--   most recent snapshot_date.
-- * NULL in stage_filter or state_filter means "all stages" / "all states",
--   allowing a single table to serve both filtered and unfiltered queries.
-- * DISTSTYLE EVEN is used because these tables are small and consumed by
--   simple sequential scans.
-- =============================================================================

SET search_path TO sclc_analytics, public;

-- ---------------------------------------------------------------------------
-- agg_overview_metrics
-- ---------------------------------------------------------------------------
-- Top-level KPI card metrics displayed on the dashboard landing page.
-- One row per (snapshot_date, stage_filter, state_filter) combination.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sclc_analytics.agg_overview_metrics
(
    snapshot_date               DATE            NOT NULL    ENCODE delta32k,
    stage_filter                VARCHAR(20)                 ENCODE bytedict,   -- NULL = all stages
    state_filter                VARCHAR(2)                  ENCODE bytedict,   -- NULL = all states
    total_patients              INTEGER                     ENCODE az64,
    new_diagnoses_mtd           INTEGER                     ENCODE az64,
    new_diagnoses_qtd           INTEGER                     ENCODE az64,
    new_diagnoses_ytd           INTEGER                     ENCODE az64,
    median_time_to_treatment    DECIMAL(10,1)               ENCODE az64,
    biomarker_testing_rate      DECIMAL(5,1)                ENCODE az64,
    immunotherapy_uptake_rate   DECIMAL(5,1)                ENCODE az64,
    clinical_trial_rate         DECIMAL(5,1)                ENCODE az64
)
DISTSTYLE EVEN
SORTKEY (snapshot_date);

-- Redshift does not support composite PRIMARY KEY with expressions, so
-- we enforce uniqueness via a unique constraint workaround at the ETL layer
-- using: (snapshot_date, COALESCE(stage_filter, 'ALL'), COALESCE(state_filter, 'ALL'))

COMMENT ON TABLE sclc_analytics.agg_overview_metrics IS
    'Pre-aggregated KPI metrics for the SCLC dashboard overview cards. '
    'One row per snapshot_date / stage_filter / state_filter combination. '
    'NULL filters represent the "all" aggregate.';

-- ---------------------------------------------------------------------------
-- agg_time_to_treatment
-- ---------------------------------------------------------------------------
-- Time-to-treatment distribution buckets for the histogram / waterfall
-- chart on the dashboard.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sclc_analytics.agg_time_to_treatment
(
    snapshot_date       DATE            NOT NULL    ENCODE delta32k,
    stage_filter        VARCHAR(20)                 ENCODE bytedict,
    state_filter        VARCHAR(2)                  ENCODE bytedict,
    bucket_label        VARCHAR(20)     NOT NULL    ENCODE bytedict,   -- '0-7 days', '8-14 days', '15-21 days', '22-30 days', '31+ days'
    bucket_order        INTEGER         NOT NULL    ENCODE az64,
    patient_count       INTEGER                     ENCODE az64,
    percentage          DECIMAL(5,1)                ENCODE az64,
    median_days         DECIMAL(10,1)               ENCODE az64,
    mean_days           DECIMAL(10,1)               ENCODE az64,
    within_target_pct   DECIMAL(5,1)                ENCODE az64        -- target = 21 days from diagnosis to treatment
)
DISTSTYLE EVEN
SORTKEY (snapshot_date);

COMMENT ON TABLE sclc_analytics.agg_time_to_treatment IS
    'Time-to-treatment distribution in bucketed intervals. '
    'within_target_pct measures the share of patients treated within '
    'the 21-day clinical target.';

-- ---------------------------------------------------------------------------
-- agg_treatment_patterns
-- ---------------------------------------------------------------------------
-- Treatment pattern breakdown by line of therapy and regimen, used for
-- the sunburst / stacked bar charts.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sclc_analytics.agg_treatment_patterns
(
    snapshot_date       DATE            NOT NULL    ENCODE delta32k,
    stage_filter        VARCHAR(20)                 ENCODE bytedict,
    line_of_therapy     VARCHAR(20)                 ENCODE bytedict,   -- '1st line', '2nd line', '3rd line+'
    regimen_name        VARCHAR(200)    NOT NULL    ENCODE zstd,
    regimen_category    VARCHAR(50)                 ENCODE bytedict,   -- 'Chemo+IO', 'Chemo Only', 'IO Monotherapy', 'Targeted', 'Other'
    patient_count       INTEGER                     ENCODE az64,
    percentage          DECIMAL(5,1)                ENCODE az64
)
DISTSTYLE EVEN
SORTKEY (snapshot_date);

COMMENT ON TABLE sclc_analytics.agg_treatment_patterns IS
    'Treatment pattern aggregation by line of therapy and regimen, '
    'providing patient counts and percentages for pattern visualizations.';

-- ---------------------------------------------------------------------------
-- agg_geographic_metrics
-- ---------------------------------------------------------------------------
-- State-level metrics for the choropleth map and geographic drill-down.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sclc_analytics.agg_geographic_metrics
(
    snapshot_date           DATE            NOT NULL    ENCODE delta32k,
    state                   VARCHAR(2)      NOT NULL    ENCODE bytedict,
    state_name              VARCHAR(50)                 ENCODE zstd,
    patient_count           INTEGER                     ENCODE az64,
    avg_time_to_treatment   DECIMAL(10,1)               ENCODE az64,
    immunotherapy_rate      DECIMAL(5,1)                ENCODE az64,
    trial_enrollment_rate   DECIMAL(5,1)                ENCODE az64
)
DISTSTYLE EVEN
SORTKEY (snapshot_date);

COMMENT ON TABLE sclc_analytics.agg_geographic_metrics IS
    'State-level aggregated metrics for the geographic choropleth map, '
    'including treatment timing, immunotherapy adoption, and trial enrollment.';

-- ---------------------------------------------------------------------------
-- agg_sankey_journey
-- ---------------------------------------------------------------------------
-- Node-to-node patient-flow data for the Sankey diagram that visualises
-- the full patient journey (Diagnosis -> Treatment -> Response -> Outcome).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sclc_analytics.agg_sankey_journey
(
    snapshot_date       DATE            NOT NULL    ENCODE delta32k,
    stage_filter        VARCHAR(20)                 ENCODE bytedict,
    source_node         VARCHAR(100)    NOT NULL    ENCODE zstd,
    target_node         VARCHAR(100)    NOT NULL    ENCODE zstd,
    patient_count       INTEGER                     ENCODE az64,
    source_category     VARCHAR(50)                 ENCODE bytedict,
    target_category     VARCHAR(50)                 ENCODE bytedict
)
DISTSTYLE EVEN
SORTKEY (snapshot_date);

COMMENT ON TABLE sclc_analytics.agg_sankey_journey IS
    'Sankey diagram flow data — source-to-target node transitions with '
    'patient counts, used to visualise the end-to-end SCLC patient journey.';
