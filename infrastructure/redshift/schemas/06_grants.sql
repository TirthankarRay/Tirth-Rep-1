-- =============================================================================
-- SCLC Patient Journey Dashboard — Roles and Grants
-- =============================================================================
-- File:        06_grants.sql
-- Description: Creates application roles and grants schema / table-level
--              permissions following the principle of least privilege.
-- Target:      Amazon Redshift
-- Prerequisites: 01_create_schemas.sql through 05_materialized_views.sql
--
-- Roles
-- ~~~~~
--   sclc_readonly  — Dashboard viewers; SELECT on analytics + MVs only.
--   sclc_analyst   — Data analysts; SELECT on core + analytics schemas.
--   sclc_etl       — ETL service account; full staging access, DML on
--                    core + analytics.
--   sclc_admin     — Full control over all SCLC schemas and objects.
-- =============================================================================

-- ============================================================
-- 1. Create roles (idempotent — Redshift errors if role exists,
--    so we trap with a DO block equivalent or simply run these
--    one-time during provisioning).
-- ============================================================

-- NOTE: Redshift does not support CREATE ROLE IF NOT EXISTS.
--       Wrap in exception-safe blocks or run conditionally in
--       your provisioning script.  The statements below assume
--       first-time setup.

CREATE GROUP sclc_readonly;
CREATE GROUP sclc_analyst;
CREATE GROUP sclc_etl;
CREATE GROUP sclc_admin;

-- ============================================================
-- 2. Schema-level USAGE grants
-- ============================================================

-- sclc_readonly: analytics layer only
ALTER DEFAULT PRIVILEGES IN SCHEMA sclc_analytics
    GRANT SELECT ON TABLES TO GROUP sclc_readonly;
GRANT USAGE ON SCHEMA sclc_analytics TO GROUP sclc_readonly;
GRANT USAGE ON SCHEMA sclc_core TO GROUP sclc_readonly;  -- needed for MVs in sclc_core

-- sclc_analyst: core + analytics
ALTER DEFAULT PRIVILEGES IN SCHEMA sclc_core
    GRANT SELECT ON TABLES TO GROUP sclc_analyst;
ALTER DEFAULT PRIVILEGES IN SCHEMA sclc_analytics
    GRANT SELECT ON TABLES TO GROUP sclc_analyst;
GRANT USAGE ON SCHEMA sclc_core TO GROUP sclc_analyst;
GRANT USAGE ON SCHEMA sclc_analytics TO GROUP sclc_analyst;

-- sclc_etl: staging (full), core + analytics (DML)
GRANT ALL ON SCHEMA sclc_staging TO GROUP sclc_etl;
GRANT USAGE ON SCHEMA sclc_core TO GROUP sclc_etl;
GRANT USAGE ON SCHEMA sclc_analytics TO GROUP sclc_etl;
ALTER DEFAULT PRIVILEGES IN SCHEMA sclc_staging
    GRANT ALL ON TABLES TO GROUP sclc_etl;
ALTER DEFAULT PRIVILEGES IN SCHEMA sclc_core
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO GROUP sclc_etl;
ALTER DEFAULT PRIVILEGES IN SCHEMA sclc_analytics
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO GROUP sclc_etl;

-- sclc_admin: full control on all schemas
GRANT ALL ON SCHEMA sclc_core TO GROUP sclc_admin;
GRANT ALL ON SCHEMA sclc_analytics TO GROUP sclc_admin;
GRANT ALL ON SCHEMA sclc_staging TO GROUP sclc_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA sclc_core
    GRANT ALL ON TABLES TO GROUP sclc_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA sclc_analytics
    GRANT ALL ON TABLES TO GROUP sclc_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA sclc_staging
    GRANT ALL ON TABLES TO GROUP sclc_admin;

-- ============================================================
-- 3. Explicit table-level grants for existing objects
-- ============================================================

-- ---------------------------------------------------------------------------
-- sclc_readonly — SELECT on analytics tables and materialized views
-- ---------------------------------------------------------------------------
GRANT SELECT ON ALL TABLES IN SCHEMA sclc_analytics TO GROUP sclc_readonly;

-- Materialized views in sclc_core that readonly users need
GRANT SELECT ON sclc_core.mv_patient_latest_status TO GROUP sclc_readonly;
GRANT SELECT ON sclc_core.mv_treatment_timeline TO GROUP sclc_readonly;
GRANT SELECT ON sclc_analytics.mv_kpi_current TO GROUP sclc_readonly;

-- ---------------------------------------------------------------------------
-- sclc_analyst — SELECT on all core + analytics tables
-- ---------------------------------------------------------------------------
GRANT SELECT ON ALL TABLES IN SCHEMA sclc_core TO GROUP sclc_analyst;
GRANT SELECT ON ALL TABLES IN SCHEMA sclc_analytics TO GROUP sclc_analyst;

-- ---------------------------------------------------------------------------
-- sclc_etl — Full DML on staging; INSERT/UPDATE/DELETE on core + analytics
-- ---------------------------------------------------------------------------
GRANT ALL ON ALL TABLES IN SCHEMA sclc_staging TO GROUP sclc_etl;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA sclc_core TO GROUP sclc_etl;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA sclc_analytics TO GROUP sclc_etl;

-- ---------------------------------------------------------------------------
-- sclc_admin — ALL on everything
-- ---------------------------------------------------------------------------
GRANT ALL ON ALL TABLES IN SCHEMA sclc_core TO GROUP sclc_admin;
GRANT ALL ON ALL TABLES IN SCHEMA sclc_analytics TO GROUP sclc_admin;
GRANT ALL ON ALL TABLES IN SCHEMA sclc_staging TO GROUP sclc_admin;
