-- =============================================================================
-- SCLC Patient Journey Dashboard — Dimension Tables
-- =============================================================================
-- File:        02_dimension_tables.sql
-- Description: Creates dimension tables in the sclc_core schema.  These
--              provide the descriptive context for every fact record.
-- Target:      Amazon Redshift
-- Prerequisites: 01_create_schemas.sql
-- =============================================================================

SET search_path TO sclc_core, public;

-- ---------------------------------------------------------------------------
-- dim_patient
-- ---------------------------------------------------------------------------
-- Central patient dimension.  One row per unique patient.  Distribution on
-- patient_id co-locates patient data with all fact tables that share the
-- same DISTKEY, enabling merge-join plans on the leader node.
-- Compound SORTKEY (state, created_at) supports geographic filters and
-- recent-patient scans.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sclc_core.dim_patient
(
    patient_id      VARCHAR(36)     NOT NULL    ENCODE zstd,
    external_id     VARCHAR(100)    NOT NULL    ENCODE zstd,
    date_of_birth   DATE                        ENCODE delta32k,
    gender          VARCHAR(20)                 ENCODE bytedict,   -- Male, Female, Other
    race_ethnicity  VARCHAR(50)                 ENCODE bytedict,
    state           VARCHAR(2)                  ENCODE bytedict,   -- US state abbreviation
    county          VARCHAR(100)                ENCODE zstd,
    zip_code        VARCHAR(10)                 ENCODE zstd,
    insurance_type  VARCHAR(50)                 ENCODE bytedict,   -- Medicare, Medicaid, Commercial, Uninsured
    urban_rural     VARCHAR(20)                 ENCODE bytedict,
    created_at      TIMESTAMP       DEFAULT GETDATE()  ENCODE az64,
    updated_at      TIMESTAMP       DEFAULT GETDATE()  ENCODE az64,

    PRIMARY KEY (patient_id),
    UNIQUE (external_id)
)
DISTKEY (patient_id)
COMPOUND SORTKEY (state, created_at);

COMMENT ON TABLE sclc_core.dim_patient IS
    'Patient dimension — one row per unique SCLC patient with demographics '
    'and geographic attributes.';

-- ---------------------------------------------------------------------------
-- dim_facility
-- ---------------------------------------------------------------------------
-- Small reference table distributed to ALL nodes (DISTSTYLE ALL) so that
-- joins with large fact tables never require redistribution.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sclc_core.dim_facility
(
    facility_id     VARCHAR(36)     NOT NULL    ENCODE zstd,
    facility_name   VARCHAR(200)    NOT NULL    ENCODE zstd,
    facility_type   VARCHAR(50)                 ENCODE bytedict,   -- Academic, Community, Veterans, Rural
    state           VARCHAR(2)                  ENCODE bytedict,
    city            VARCHAR(100)                ENCODE zstd,

    PRIMARY KEY (facility_id)
)
DISTSTYLE ALL;

COMMENT ON TABLE sclc_core.dim_facility IS
    'Facility dimension — reference table of diagnosing / treating facilities. '
    'DISTSTYLE ALL for broadcast-join efficiency.';

-- ---------------------------------------------------------------------------
-- dim_date
-- ---------------------------------------------------------------------------
-- Standard date dimension in YYYYMMDD integer-key format.  Distributed to
-- ALL nodes and sorted on full_date for fast range scans.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sclc_core.dim_date
(
    date_key        INTEGER         NOT NULL    ENCODE az64,       -- YYYYMMDD
    full_date       DATE            NOT NULL    ENCODE delta32k,
    year            SMALLINT        NOT NULL    ENCODE az64,
    quarter         SMALLINT        NOT NULL    ENCODE az64,
    month           SMALLINT        NOT NULL    ENCODE az64,
    day             SMALLINT        NOT NULL    ENCODE az64,
    day_of_week     SMALLINT        NOT NULL    ENCODE az64,       -- 1=Sun … 7=Sat
    week_of_year    SMALLINT        NOT NULL    ENCODE az64,
    month_name      VARCHAR(10)     NOT NULL    ENCODE bytedict,   -- January … December
    day_name        VARCHAR(10)     NOT NULL    ENCODE bytedict,   -- Sunday … Saturday
    is_weekend      BOOLEAN         NOT NULL    ENCODE raw,
    is_month_end    BOOLEAN         NOT NULL    ENCODE raw,
    fiscal_year     SMALLINT        NOT NULL    ENCODE az64,
    fiscal_quarter  SMALLINT        NOT NULL    ENCODE az64,

    PRIMARY KEY (date_key)
)
DISTSTYLE ALL
SORTKEY (full_date);

COMMENT ON TABLE sclc_core.dim_date IS
    'Date dimension — one row per calendar day with fiscal calendar attributes. '
    'DISTSTYLE ALL for broadcast-join efficiency.';
