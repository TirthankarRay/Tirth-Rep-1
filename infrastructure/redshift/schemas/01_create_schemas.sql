-- =============================================================================
-- SCLC Patient Journey Dashboard — Schema Definitions
-- =============================================================================
-- File:        01_create_schemas.sql
-- Description: Creates the three logical schemas that partition the data
--              warehouse into staging, core (dimensions + facts), and
--              pre-aggregated analytics layers.
-- Target:      Amazon Redshift
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. sclc_core — Dimensions and fact tables
--    Contains the canonical patient-journey data model used by all downstream
--    queries and aggregations.
-- ---------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS sclc_core
    AUTHORIZATION sclc_admin;

COMMENT ON SCHEMA sclc_core IS
    'Core data model for the SCLC Patient Journey Dashboard. '
    'Houses dimension and fact tables representing patients, diagnoses, '
    'treatments, biomarkers, progression events, and clinical-trial enrollment.';

-- ---------------------------------------------------------------------------
-- 2. sclc_analytics — Pre-aggregated / reporting tables
--    Stores snapshot-based aggregations consumed directly by the dashboard
--    API layer.  Tables here are refreshed by scheduled ETL jobs.
-- ---------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS sclc_analytics
    AUTHORIZATION sclc_admin;

COMMENT ON SCHEMA sclc_analytics IS
    'Pre-aggregated analytics tables for the SCLC Patient Journey Dashboard. '
    'Contains snapshot-based KPIs, treatment-pattern summaries, geographic '
    'metrics, and Sankey journey flows consumed by the front-end API.';

-- ---------------------------------------------------------------------------
-- 3. sclc_staging — ETL staging area
--    Temporary landing zone for raw / transformed data before it is merged
--    into sclc_core.  Tables here may be truncated between loads.
-- ---------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS sclc_staging
    AUTHORIZATION sclc_admin;

COMMENT ON SCHEMA sclc_staging IS
    'ETL staging schema for the SCLC Patient Journey Dashboard. '
    'Serves as a temporary landing zone for raw ingestion files and '
    'intermediate transformations before upsert into sclc_core tables.';
