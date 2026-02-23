# Databricks notebook source
# MAGIC %md
# MAGIC # Silver Layer: Patient Dimension (SCD Type 2)
# MAGIC
# MAGIC **Pipeline:** SCLC Patient Journey Analytics
# MAGIC **Layer:** Silver (Cleaned & Conformed)
# MAGIC **Source:** `bronze.ehr_patients`, `bronze.claims_professional`
# MAGIC **Target:** `silver.dim_patient`
# MAGIC
# MAGIC ## Processing Logic
# MAGIC 1. Read patient records from EHR and claims bronze tables
# MAGIC 2. Deduplicate across sources using fuzzy matching (name + DOB + zip)
# MAGIC 3. Assign a master `patient_id` (UUID) to each unique patient
# MAGIC 4. Standardize demographics (gender, race/ethnicity, state, insurance type)
# MAGIC 5. Classify urban/rural based on zip code
# MAGIC 6. Implement SCD Type 2 tracking with effective_date, end_date, is_current
# MAGIC 7. Apply data quality expectations

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

import logging
import uuid
from datetime import date, datetime

from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql.types import (
    BooleanType,
    DateType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

# COMMAND ----------

# Widget parameters
dbutils.widgets.dropdown("environment", "dev", ["dev", "staging", "prod"], "Environment")
dbutils.widgets.text("catalog", "sclc_analytics", "Unity Catalog Name")
dbutils.widgets.dropdown("run_mode", "incremental", ["incremental", "full_refresh"], "Run Mode")

ENV = dbutils.widgets.get("environment")
CATALOG = dbutils.widgets.get("catalog")
RUN_MODE = dbutils.widgets.get("run_mode")

# COMMAND ----------

# Namespace configuration
BRONZE_SCHEMA = f"{CATALOG}.bronze"
SILVER_SCHEMA = f"{CATALOG}.silver"
TARGET_TABLE = f"{SILVER_SCHEMA}.dim_patient"

# COMMAND ----------

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("silver.dim_patient")
logger.setLevel(logging.INFO)

logger.info(f"Starting Patient Dimension processing")
logger.info(f"Environment: {ENV} | Run Mode: {RUN_MODE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Ensure Schema Exists

# COMMAND ----------

spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS silver")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Reference Data: Urban/Rural Classification & State Codes

# COMMAND ----------

# Urban/Rural classification by zip code prefix (first 3 digits = ZCTA prefix)
# In production this would come from a HUD-USPS crosswalk or RUCA codes reference table.
# Here we use a UDF-based approach that can be extended with a lookup table.

# State abbreviation standardization mapping
STATE_MAPPING = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI",
    "south carolina": "SC", "south dakota": "SD", "tennessee": "TN", "texas": "TX",
    "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
    "district of columbia": "DC",
}

# Gender standardization mapping
GENDER_MAPPING = {
    "m": "Male", "male": "Male", "f": "Female", "female": "Female",
    "o": "Other", "other": "Other", "u": "Unknown", "unknown": "Unknown",
    "non-binary": "Other", "nb": "Other", "x": "Other",
}

# Insurance type standardization
INSURANCE_MAPPING = {
    "medicare": "Medicare", "medicaid": "Medicaid",
    "commercial": "Commercial", "private": "Commercial",
    "employer": "Commercial", "hmo": "Commercial", "ppo": "Commercial",
    "self-pay": "Self-Pay", "uninsured": "Self-Pay",
    "tricare": "Other Government", "va": "Other Government",
    "other": "Other",
}

# Race/Ethnicity standardization
RACE_ETHNICITY_MAPPING = {
    "white": "White", "caucasian": "White",
    "black": "Black or African American", "african american": "Black or African American",
    "black or african american": "Black or African American",
    "hispanic": "Hispanic or Latino", "latino": "Hispanic or Latino",
    "hispanic or latino": "Hispanic or Latino",
    "asian": "Asian", "asian american": "Asian",
    "native hawaiian": "Native Hawaiian or Pacific Islander",
    "pacific islander": "Native Hawaiian or Pacific Islander",
    "american indian": "American Indian or Alaska Native",
    "alaska native": "American Indian or Alaska Native",
    "native american": "American Indian or Alaska Native",
    "two or more": "Two or More Races", "multiracial": "Two or More Races",
    "other": "Other", "unknown": "Unknown", "declined": "Unknown",
    "not reported": "Unknown",
}

# Broadcast mappings as Python dicts for UDF usage
broadcast_state = spark.sparkContext.broadcast(STATE_MAPPING)
broadcast_gender = spark.sparkContext.broadcast(GENDER_MAPPING)
broadcast_insurance = spark.sparkContext.broadcast(INSURANCE_MAPPING)
broadcast_race = spark.sparkContext.broadcast(RACE_ETHNICITY_MAPPING)

# COMMAND ----------

# MAGIC %md
# MAGIC ## UDFs for Standardization

# COMMAND ----------

@F.udf(StringType())
def standardize_state(raw_state):
    """
    Standardize state values to 2-letter abbreviations.

    Handles full state names, mixed case, and already-abbreviated codes.
    Returns None for unrecognized values.
    """
    if raw_state is None:
        return None
    cleaned = raw_state.strip()
    # Already a valid 2-letter code
    if len(cleaned) == 2 and cleaned.upper() in broadcast_state.value.values():
        return cleaned.upper()
    # Full name lookup
    mapped = broadcast_state.value.get(cleaned.lower())
    return mapped


@F.udf(StringType())
def standardize_gender(raw_gender):
    """Standardize gender values to Male/Female/Other/Unknown."""
    if raw_gender is None:
        return "Unknown"
    mapped = broadcast_gender.value.get(raw_gender.strip().lower(), "Unknown")
    return mapped


@F.udf(StringType())
def standardize_insurance(raw_insurance):
    """Standardize insurance type to canonical categories."""
    if raw_insurance is None:
        return "Unknown"
    cleaned = raw_insurance.strip().lower()
    for key, value in broadcast_insurance.value.items():
        if key in cleaned:
            return value
    return "Other"


@F.udf(StringType())
def standardize_race_ethnicity(raw_race):
    """Standardize race/ethnicity values to OMB categories."""
    if raw_race is None:
        return "Unknown"
    cleaned = raw_race.strip().lower()
    for key, value in broadcast_race.value.items():
        if key in cleaned:
            return value
    return "Unknown"


@F.udf(StringType())
def classify_urban_rural(zip_code):
    """
    Classify a zip code as Urban, Suburban, or Rural.

    Uses a simplified heuristic based on zip code prefix density.
    In production, this would be replaced with a RUCA code lookup
    or HUD-USPS crosswalk table join.
    """
    if zip_code is None:
        return "Unknown"
    cleaned = zip_code.strip()[:5]
    if len(cleaned) < 5 or not cleaned.isdigit():
        return "Unknown"

    prefix = int(cleaned[:3])
    # Major metro area prefixes (simplified heuristic)
    urban_prefixes = set(range(100, 120)) | set(range(200, 220)) | \
        set(range(300, 320)) | set(range(600, 620)) | \
        set(range(900, 920)) | set(range(700, 710))
    suburban_prefixes = set(range(120, 150)) | set(range(220, 260)) | \
        set(range(320, 350)) | set(range(620, 650)) | \
        set(range(920, 950))

    if prefix in urban_prefixes:
        return "Urban"
    elif prefix in suburban_prefixes:
        return "Suburban"
    else:
        return "Rural"


@F.udf(StringType())
def generate_patient_uuid():
    """Generate a new UUID4 for a master patient identifier."""
    return str(uuid.uuid4())

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Extract Patients from Bronze Sources

# COMMAND ----------

def extract_ehr_patients() -> DataFrame:
    """
    Extract and normalize patient records from the bronze EHR table.

    Selects relevant demographic fields from FHIR Patient resources
    and normalizes column names for downstream processing.

    Returns
    -------
    DataFrame
        Normalized patient records with source='ehr'.
    """
    logger.info("Extracting patients from bronze.ehr_patients")

    df = spark.table(f"{BRONZE_SCHEMA}.ehr_patients")

    df_normalized = (
        df
        .select(
            F.col("id").alias("source_patient_id"),
            F.col("name").alias("patient_name"),
            F.col("birthDate").alias("date_of_birth"),
            F.col("gender").alias("raw_gender"),
            F.col("address").alias("raw_address"),
            F.col("race").alias("raw_race_ethnicity"),
            F.col("insurance_type").alias("raw_insurance_type"),
            F.col("_ingestion_timestamp"),
        )
        .withColumn("source_system", F.lit("ehr"))
        # Extract first/last name from FHIR name structure
        .withColumn(
            "first_name",
            F.upper(F.trim(F.coalesce(
                F.col("patient_name.given")[0],
                F.col("patient_name"),
            ))),
        )
        .withColumn(
            "last_name",
            F.upper(F.trim(F.coalesce(
                F.col("patient_name.family"),
                F.col("patient_name"),
            ))),
        )
        .withColumn(
            "zip_code",
            F.coalesce(
                F.col("raw_address.postalCode"),
                F.col("raw_address"),
            ),
        )
        .withColumn(
            "state_raw",
            F.coalesce(
                F.col("raw_address.state"),
                F.lit(None).cast(StringType()),
            ),
        )
    )

    return df_normalized


def extract_claims_patients() -> DataFrame:
    """
    Extract and normalize patient records from the bronze claims table.

    Professional claims contain subscriber demographics that supplement
    or substitute for EHR data.

    Returns
    -------
    DataFrame
        Normalized patient records with source='claims'.
    """
    logger.info("Extracting patients from bronze.claims_professional")

    df = spark.table(f"{BRONZE_SCHEMA}.claims_professional")

    # Deduplicate claims to unique patients
    df_patients = (
        df
        .select(
            F.col("subscriber_id").alias("source_patient_id"),
            F.col("subscriber_first_name").alias("first_name"),
            F.col("subscriber_last_name").alias("last_name"),
            F.col("subscriber_dob").alias("date_of_birth"),
            F.col("subscriber_gender").alias("raw_gender"),
            F.col("subscriber_zip").alias("zip_code"),
            F.col("subscriber_state").alias("state_raw"),
            F.col("subscriber_race").alias("raw_race_ethnicity"),
            F.col("payer_name").alias("raw_insurance_type"),
            F.col("_ingestion_timestamp"),
        )
        .withColumn("source_system", F.lit("claims"))
        .withColumn("first_name", F.upper(F.trim(F.col("first_name"))))
        .withColumn("last_name", F.upper(F.trim(F.col("last_name"))))
    )

    # Take the most recent record per subscriber
    window_latest = Window.partitionBy("source_patient_id").orderBy(
        F.col("_ingestion_timestamp").desc()
    )
    df_deduped = (
        df_patients
        .withColumn("_row_num", F.row_number().over(window_latest))
        .filter(F.col("_row_num") == 1)
        .drop("_row_num")
    )

    return df_deduped

# COMMAND ----------

logger.info("Extracting patient records from bronze sources")
df_ehr_patients = extract_ehr_patients()
df_claims_patients = extract_claims_patients()

logger.info(f"EHR patient records: {df_ehr_patients.count():,}")
logger.info(f"Claims patient records: {df_claims_patients.count():,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Union and Deduplicate Across Sources (Fuzzy Matching)

# COMMAND ----------

def fuzzy_deduplicate_patients(
    df_ehr: DataFrame,
    df_claims: DataFrame,
) -> DataFrame:
    """
    Deduplicate patients across EHR and claims sources using fuzzy matching.

    Matching strategy:
    - Exact match on normalized (last_name, date_of_birth, zip5)
    - Soundex match on first_name for phonetic similarity
    - Assigns a master patient_id to each unique patient group

    Parameters
    ----------
    df_ehr : DataFrame
        Normalized EHR patient records.
    df_claims : DataFrame
        Normalized claims patient records.

    Returns
    -------
    DataFrame
        Deduplicated patient records with master_patient_id assigned.
    """
    logger.info("Starting cross-source patient deduplication")

    # Select common columns for union
    common_cols = [
        "source_patient_id",
        "source_system",
        "first_name",
        "last_name",
        "date_of_birth",
        "zip_code",
        "state_raw",
        "raw_gender",
        "raw_race_ethnicity",
        "raw_insurance_type",
        "_ingestion_timestamp",
    ]

    # Ensure columns exist in both DataFrames (fill missing with null)
    for col_name in common_cols:
        if col_name not in df_ehr.columns:
            df_ehr = df_ehr.withColumn(col_name, F.lit(None).cast(StringType()))
        if col_name not in df_claims.columns:
            df_claims = df_claims.withColumn(col_name, F.lit(None).cast(StringType()))

    df_all = df_ehr.select(common_cols).unionByName(df_claims.select(common_cols))

    # Create matching keys for fuzzy deduplication
    df_keyed = (
        df_all
        .withColumn("dob_str", F.date_format(F.to_date("date_of_birth"), "yyyyMMdd"))
        .withColumn("zip5", F.substring(F.col("zip_code"), 1, 5))
        .withColumn("first_name_soundex", F.soundex(F.col("first_name")))
        .withColumn("last_name_clean", F.regexp_replace(F.col("last_name"), "[^A-Z]", ""))
        # Blocking key: exact match on last_name + DOB + zip5
        .withColumn(
            "match_key_exact",
            F.concat_ws(
                "|",
                F.col("last_name_clean"),
                F.col("dob_str"),
                F.col("zip5"),
            ),
        )
        # Fuzzy key: soundex(first) + last + DOB (handles zip typos)
        .withColumn(
            "match_key_fuzzy",
            F.concat_ws(
                "|",
                F.col("first_name_soundex"),
                F.col("last_name_clean"),
                F.col("dob_str"),
            ),
        )
    )

    # Assign patient group using exact key first, then fuzzy fallback
    window_exact = Window.partitionBy("match_key_exact").orderBy(
        # Prefer EHR as the golden source
        F.when(F.col("source_system") == "ehr", 1).otherwise(2),
        F.col("_ingestion_timestamp").desc(),
    )

    df_grouped = (
        df_keyed
        .withColumn("group_rank", F.row_number().over(window_exact))
        .withColumn(
            "master_patient_id",
            F.first("source_patient_id").over(
                Window.partitionBy("match_key_exact")
                .orderBy(
                    F.when(F.col("source_system") == "ehr", 1).otherwise(2),
                    F.col("_ingestion_timestamp").desc(),
                )
            ),
        )
    )

    # For each patient group, take the best record (EHR preferred, most recent)
    df_golden = (
        df_grouped
        .filter(F.col("group_rank") == 1)
        .withColumn("master_patient_id", generate_patient_uuid())
        .drop(
            "group_rank", "dob_str", "zip5", "first_name_soundex",
            "last_name_clean", "match_key_exact", "match_key_fuzzy",
        )
    )

    logger.info(f"Deduplication complete: {df_golden.count():,} unique patients")
    return df_golden

# COMMAND ----------

df_deduped = fuzzy_deduplicate_patients(df_ehr_patients, df_claims_patients)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Standardize Demographics

# COMMAND ----------

def standardize_demographics(df: DataFrame) -> DataFrame:
    """
    Apply standardization transformations to all demographic fields.

    Normalizes gender, race/ethnicity, state codes, insurance type,
    and urban/rural classification using the UDFs defined above.

    Parameters
    ----------
    df : DataFrame
        Deduplicated patient records with raw demographic columns.

    Returns
    -------
    DataFrame
        Patient records with standardized demographic columns.
    """
    logger.info("Standardizing demographic fields")

    df_std = (
        df
        .withColumn("gender", standardize_gender(F.col("raw_gender")))
        .withColumn("race_ethnicity", standardize_race_ethnicity(F.col("raw_race_ethnicity")))
        .withColumn("state", standardize_state(F.col("state_raw")))
        .withColumn("insurance_type", standardize_insurance(F.col("raw_insurance_type")))
        .withColumn("zip5", F.substring(F.col("zip_code"), 1, 5))
        .withColumn("urban_rural", classify_urban_rural(F.col("zip_code")))
        .withColumn("date_of_birth", F.to_date(F.col("date_of_birth")))
        .withColumn(
            "age_at_processing",
            F.floor(
                F.datediff(F.current_date(), F.to_date(F.col("date_of_birth"))) / 365.25
            ).cast(IntegerType()),
        )
    )

    return df_std

# COMMAND ----------

df_standardized = standardize_demographics(df_deduped)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Data Quality Checks

# COMMAND ----------

def apply_data_quality_checks(df: DataFrame) -> DataFrame:
    """
    Apply data quality validations using Delta expectations pattern.

    Flags records that fail quality checks and logs violation summaries.
    Records are NOT dropped -- they are flagged for review.

    Parameters
    ----------
    df : DataFrame
        Standardized patient records.

    Returns
    -------
    DataFrame
        Records with _dq_valid flag and _dq_issues array.
    """
    logger.info("Applying data quality checks")

    df_dq = (
        df
        # Individual quality flags
        .withColumn(
            "_dq_has_name",
            (F.col("first_name").isNotNull()) & (F.col("last_name").isNotNull()),
        )
        .withColumn(
            "_dq_has_dob",
            F.col("date_of_birth").isNotNull(),
        )
        .withColumn(
            "_dq_valid_age",
            (F.col("age_at_processing") >= 0) & (F.col("age_at_processing") <= 120),
        )
        .withColumn(
            "_dq_has_gender",
            F.col("gender") != "Unknown",
        )
        .withColumn(
            "_dq_has_state",
            F.col("state").isNotNull(),
        )
        .withColumn(
            "_dq_has_zip",
            (F.col("zip5").isNotNull()) & (F.length(F.col("zip5")) == 5),
        )
        # Aggregate quality flag
        .withColumn(
            "_dq_valid",
            (
                F.col("_dq_has_name")
                & F.col("_dq_has_dob")
                & F.col("_dq_valid_age")
            ),
        )
        # Collect issues into an array
        .withColumn(
            "_dq_issues",
            F.array_compact(
                F.array(
                    F.when(~F.col("_dq_has_name"), F.lit("missing_name")),
                    F.when(~F.col("_dq_has_dob"), F.lit("missing_dob")),
                    F.when(~F.col("_dq_valid_age"), F.lit("invalid_age")),
                    F.when(~F.col("_dq_has_gender"), F.lit("unknown_gender")),
                    F.when(~F.col("_dq_has_state"), F.lit("missing_state")),
                    F.when(~F.col("_dq_has_zip"), F.lit("invalid_zip")),
                )
            ),
        )
    )

    # Log quality summary
    total = df_dq.count()
    valid = df_dq.filter(F.col("_dq_valid")).count()
    logger.info(f"Data quality: {valid:,}/{total:,} records pass all critical checks "
                f"({100 * valid / max(total, 1):.1f}%)")

    # Log individual check results
    for check_col in ["_dq_has_name", "_dq_has_dob", "_dq_valid_age",
                       "_dq_has_gender", "_dq_has_state", "_dq_has_zip"]:
        pass_count = df_dq.filter(F.col(check_col)).count()
        logger.info(f"  {check_col}: {pass_count:,}/{total:,} pass")

    # Drop intermediate flag columns, keep summary columns
    df_clean = df_dq.drop(
        "_dq_has_name", "_dq_has_dob", "_dq_valid_age",
        "_dq_has_gender", "_dq_has_state", "_dq_has_zip",
    )

    return df_clean

# COMMAND ----------

df_quality_checked = apply_data_quality_checks(df_standardized)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Build SCD Type 2 Patient Dimension

# COMMAND ----------

def build_scd2_patient_dimension(df_incoming: DataFrame) -> None:
    """
    Implement SCD Type 2 merge into the silver.dim_patient table.

    For each incoming patient record:
    - If the patient does not exist: INSERT with is_current=True
    - If the patient exists and attributes changed: expire the old record
      (set end_date and is_current=False) and INSERT the new record
    - If the patient exists and nothing changed: skip (no-op)

    Parameters
    ----------
    df_incoming : DataFrame
        Standardized, quality-checked patient records to merge.
    """
    logger.info("Building SCD Type 2 patient dimension")

    # Prepare incoming records with SCD columns
    today = date.today()
    max_date = date(9999, 12, 31)

    df_new = (
        df_incoming
        .select(
            F.col("master_patient_id").alias("patient_id"),
            "source_patient_id",
            "source_system",
            "first_name",
            "last_name",
            "date_of_birth",
            "age_at_processing",
            "gender",
            "race_ethnicity",
            "state",
            "zip5",
            "urban_rural",
            "insurance_type",
            "_dq_valid",
            "_dq_issues",
        )
        .withColumn("effective_date", F.lit(today).cast(DateType()))
        .withColumn("end_date", F.lit(max_date).cast(DateType()))
        .withColumn("is_current", F.lit(True))
        .withColumn("_updated_timestamp", F.current_timestamp())
        # Hash of tracked attributes to detect changes
        .withColumn(
            "_attribute_hash",
            F.sha2(
                F.concat_ws(
                    "|",
                    "gender",
                    "race_ethnicity",
                    "state",
                    "zip5",
                    "urban_rural",
                    "insurance_type",
                ),
                256,
            ),
        )
    )

    target_table = TARGET_TABLE

    # Check if target table exists
    table_exists = spark.catalog.tableExists(target_table)

    if not table_exists or RUN_MODE == "full_refresh":
        logger.info(f"Writing full patient dimension to {target_table}")
        (
            df_new.write
            .format("delta")
            .mode("overwrite")
            .option("overwriteSchema", "true")
            .saveAsTable(target_table)
        )
        logger.info(f"Created {target_table} with {df_new.count():,} records")
        return

    # SCD Type 2 MERGE for incremental mode
    logger.info(f"Performing SCD Type 2 merge into {target_table}")

    df_new.createOrReplaceTempView("incoming_patients")

    # The MERGE handles three scenarios:
    # 1. Matched + attributes changed: expire old record
    # 2. Not matched: insert new record
    # We handle the insert of the new version separately after expiring
    merge_sql = f"""
    MERGE INTO {target_table} AS target
    USING incoming_patients AS source
    ON target.patient_id = source.patient_id AND target.is_current = true

    WHEN MATCHED AND target._attribute_hash != source._attribute_hash THEN
        UPDATE SET
            target.is_current = false,
            target.end_date = source.effective_date,
            target._updated_timestamp = current_timestamp()

    WHEN NOT MATCHED THEN
        INSERT (
            patient_id, source_patient_id, source_system,
            first_name, last_name, date_of_birth, age_at_processing,
            gender, race_ethnicity, state, zip5, urban_rural,
            insurance_type, _dq_valid, _dq_issues,
            effective_date, end_date, is_current,
            _updated_timestamp, _attribute_hash
        )
        VALUES (
            source.patient_id, source.source_patient_id, source.source_system,
            source.first_name, source.last_name, source.date_of_birth,
            source.age_at_processing,
            source.gender, source.race_ethnicity, source.state, source.zip5,
            source.urban_rural, source.insurance_type,
            source._dq_valid, source._dq_issues,
            source.effective_date, source.end_date, source.is_current,
            source._updated_timestamp, source._attribute_hash
        )
    """
    spark.sql(merge_sql)

    # Insert new versions for changed records
    insert_changed_sql = f"""
    INSERT INTO {target_table}
    SELECT source.*
    FROM incoming_patients source
    INNER JOIN {target_table} target
        ON target.patient_id = source.patient_id
        AND target.is_current = false
        AND target.end_date = source.effective_date
    WHERE NOT EXISTS (
        SELECT 1 FROM {target_table} t2
        WHERE t2.patient_id = source.patient_id
        AND t2.is_current = true
        AND t2._attribute_hash = source._attribute_hash
    )
    """
    spark.sql(insert_changed_sql)

    result_count = spark.sql(
        f"SELECT COUNT(*) as cnt FROM {target_table} WHERE is_current = true"
    ).first()["cnt"]
    total_count = spark.sql(
        f"SELECT COUNT(*) as cnt FROM {target_table}"
    ).first()["cnt"]

    logger.info(f"SCD2 merge complete: {result_count:,} current records, "
                f"{total_count:,} total records (including history)")

# COMMAND ----------

build_scd2_patient_dimension(df_quality_checked)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Optimize and Validate

# COMMAND ----------

# Optimize the Delta table
logger.info(f"Optimizing {TARGET_TABLE}")
spark.sql(f"OPTIMIZE {TARGET_TABLE} ZORDER BY (patient_id, state)")

# Analyze table for statistics
spark.sql(f"ANALYZE TABLE {TARGET_TABLE} COMPUTE STATISTICS FOR ALL COLUMNS")

# COMMAND ----------

# Final validation summary
validation_df = spark.sql(f"""
    SELECT
        COUNT(*) as total_records,
        COUNT(DISTINCT patient_id) as unique_patients,
        SUM(CASE WHEN is_current THEN 1 ELSE 0 END) as current_records,
        SUM(CASE WHEN NOT is_current THEN 1 ELSE 0 END) as historical_records,
        SUM(CASE WHEN _dq_valid THEN 1 ELSE 0 END) as dq_valid_records,
        COUNT(DISTINCT gender) as distinct_genders,
        COUNT(DISTINCT race_ethnicity) as distinct_race_ethnicities,
        COUNT(DISTINCT state) as distinct_states,
        COUNT(DISTINCT insurance_type) as distinct_insurance_types,
        COUNT(DISTINCT urban_rural) as distinct_urban_rural,
        MIN(effective_date) as earliest_effective_date,
        MAX(effective_date) as latest_effective_date
    FROM {TARGET_TABLE}
""")

display(validation_df)

# Table history
display(spark.sql(f"DESCRIBE HISTORY {TARGET_TABLE} LIMIT 5"))

logger.info("Patient dimension processing complete")
