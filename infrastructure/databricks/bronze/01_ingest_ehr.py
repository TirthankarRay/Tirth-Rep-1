# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze Layer: EHR Data Ingestion
# MAGIC
# MAGIC **Pipeline:** SCLC Patient Journey Analytics
# MAGIC **Layer:** Bronze (Raw Ingestion)
# MAGIC **Source:** S3 Landing Zone - EHR data (FHIR JSON, CSV)
# MAGIC **Target:** Delta Bronze tables in Unity Catalog
# MAGIC
# MAGIC ## Tables Produced
# MAGIC | Table | Source Format | Description |
# MAGIC |-------|--------------|-------------|
# MAGIC | `bronze.ehr_patients` | FHIR JSON | Patient demographics from EHR |
# MAGIC | `bronze.ehr_encounters` | FHIR JSON | Clinical encounters |
# MAGIC | `bronze.ehr_conditions` | FHIR JSON / CSV | Diagnoses and conditions |
# MAGIC | `bronze.ehr_procedures` | FHIR JSON / CSV | Procedures performed |
# MAGIC | `bronze.ehr_observations` | FHIR JSON / CSV | Lab results, vitals, assessments |
# MAGIC
# MAGIC ## Ingestion Strategy
# MAGIC - **Auto Loader** (cloudFiles) for incremental file ingestion
# MAGIC - Schema evolution enabled to handle upstream changes
# MAGIC - Metadata columns added for lineage tracking

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

import logging
import uuid
from datetime import datetime
from functools import wraps

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    ArrayType,
    BooleanType,
    DoubleType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

# COMMAND ----------

# Widget parameters for environment configuration
dbutils.widgets.dropdown("environment", "dev", ["dev", "staging", "prod"], "Environment")
dbutils.widgets.text("catalog", "sclc_analytics", "Unity Catalog Name")
dbutils.widgets.text("batch_id_override", "", "Batch ID Override (optional)")

ENV = dbutils.widgets.get("environment")
CATALOG = dbutils.widgets.get("catalog")
BATCH_ID_OVERRIDE = dbutils.widgets.get("batch_id_override")

# COMMAND ----------

# Derived configuration
S3_BASE = f"s3://sclc-data-lake-{ENV}"
RAW_PATH = f"{S3_BASE}/raw/ehr"
CHECKPOINT_BASE = f"{S3_BASE}/checkpoints/bronze/ehr"
SCHEMA_BASE = f"bronze"

BATCH_ID = BATCH_ID_OVERRIDE if BATCH_ID_OVERRIDE else str(uuid.uuid4())

# Use Unity Catalog three-level namespace
FULL_SCHEMA = f"{CATALOG}.{SCHEMA_BASE}"

# COMMAND ----------

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("bronze.ehr_ingestion")
logger.setLevel(logging.INFO)

logger.info(f"Starting EHR Bronze ingestion")
logger.info(f"Environment: {ENV}")
logger.info(f"Catalog: {CATALOG}")
logger.info(f"Batch ID: {BATCH_ID}")
logger.info(f"Raw Path: {RAW_PATH}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Utility Functions

# COMMAND ----------

def add_metadata_columns(df: DataFrame, source_description: str) -> DataFrame:
    """
    Append standard metadata columns to a DataFrame for lineage tracking.

    Parameters
    ----------
    df : DataFrame
        Source DataFrame to enrich.
    source_description : str
        Human-readable description of the data source.

    Returns
    -------
    DataFrame
        Enriched DataFrame with metadata columns.
    """
    return (
        df
        .withColumn("_ingestion_timestamp", F.current_timestamp())
        .withColumn("_source_file", F.input_file_name())
        .withColumn("_batch_id", F.lit(BATCH_ID))
        .withColumn("_source_description", F.lit(source_description))
        .withColumn("_ingestion_date", F.current_date())
    )


def get_checkpoint_path(table_name: str) -> str:
    """Return the S3 checkpoint location for a given table."""
    return f"{CHECKPOINT_BASE}/{table_name}"


def log_ingestion_metrics(table_name: str, df: DataFrame) -> None:
    """Log row count and schema information for an ingested table."""
    try:
        count = spark.sql(f"SELECT COUNT(*) as cnt FROM {FULL_SCHEMA}.{table_name}").first()["cnt"]
        logger.info(f"Table {FULL_SCHEMA}.{table_name} now has {count} total rows")
    except Exception as e:
        logger.warning(f"Could not retrieve count for {FULL_SCHEMA}.{table_name}: {e}")


def create_table_if_not_exists(table_name: str, schema: StructType) -> None:
    """
    Ensure the target Delta table exists in Unity Catalog.
    If it does not exist, create an empty Delta table with the given schema.
    """
    full_table = f"{FULL_SCHEMA}.{table_name}"
    if not spark.catalog.tableExists(full_table):
        logger.info(f"Creating table {full_table}")
        empty_df = spark.createDataFrame([], schema)
        (
            empty_df.write
            .format("delta")
            .option("mergeSchema", "true")
            .saveAsTable(full_table)
        )
        logger.info(f"Table {full_table} created successfully")
    else:
        logger.info(f"Table {full_table} already exists")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Ensure Catalog and Schema Exist

# COMMAND ----------

spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")
spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA_BASE}")
logger.info(f"Using catalog {CATALOG}, schema {SCHEMA_BASE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Ingest EHR Patients
# MAGIC
# MAGIC Source: FHIR Patient resources (JSON) and demographic CSVs.

# COMMAND ----------

def ingest_ehr_patients() -> None:
    """
    Ingest patient records from EHR source files using Auto Loader.

    Reads FHIR JSON patient bundles and demographic CSV files from the
    S3 landing zone.  Applies schema evolution and appends metadata
    columns before writing to the bronze Delta table.
    """
    table_name = "ehr_patients"
    source_path = f"{RAW_PATH}/patients/"
    checkpoint_path = get_checkpoint_path(table_name)

    logger.info(f"Ingesting {table_name} from {source_path}")

    try:
        df = (
            spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "json")
            .option("cloudFiles.inferColumnTypes", "true")
            .option("cloudFiles.schemaLocation", f"{checkpoint_path}/schema")
            .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
            .option("cloudFiles.maxFilesPerTrigger", 1000)
            .option("pathGlobFilter", "*.{json,ndjson}")
            .load(source_path)
        )

        df_enriched = add_metadata_columns(df, "ehr_fhir_patient")

        query = (
            df_enriched.writeStream
            .format("delta")
            .outputMode("append")
            .option("checkpointLocation", checkpoint_path)
            .option("mergeSchema", "true")
            .trigger(availableNow=True)
            .toTable(f"{FULL_SCHEMA}.{table_name}")
        )

        query.awaitTermination()
        log_ingestion_metrics(table_name, df_enriched)
        logger.info(f"Successfully ingested {table_name}")

    except Exception as e:
        logger.error(f"Failed to ingest {table_name}: {e}", exc_info=True)
        raise

ingest_ehr_patients()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Ingest EHR Encounters

# COMMAND ----------

def ingest_ehr_encounters() -> None:
    """
    Ingest encounter records from EHR source files using Auto Loader.

    Reads FHIR Encounter resources capturing clinic visits, hospital
    admissions, infusion appointments, and telehealth sessions.
    """
    table_name = "ehr_encounters"
    source_path = f"{RAW_PATH}/encounters/"
    checkpoint_path = get_checkpoint_path(table_name)

    logger.info(f"Ingesting {table_name} from {source_path}")

    try:
        df = (
            spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "json")
            .option("cloudFiles.inferColumnTypes", "true")
            .option("cloudFiles.schemaLocation", f"{checkpoint_path}/schema")
            .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
            .option("cloudFiles.maxFilesPerTrigger", 1000)
            .load(source_path)
        )

        df_enriched = add_metadata_columns(df, "ehr_fhir_encounter")

        query = (
            df_enriched.writeStream
            .format("delta")
            .outputMode("append")
            .option("checkpointLocation", checkpoint_path)
            .option("mergeSchema", "true")
            .trigger(availableNow=True)
            .toTable(f"{FULL_SCHEMA}.{table_name}")
        )

        query.awaitTermination()
        log_ingestion_metrics(table_name, df_enriched)
        logger.info(f"Successfully ingested {table_name}")

    except Exception as e:
        logger.error(f"Failed to ingest {table_name}: {e}", exc_info=True)
        raise

ingest_ehr_encounters()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Ingest EHR Conditions (Diagnoses)

# COMMAND ----------

def ingest_ehr_conditions() -> None:
    """
    Ingest condition/diagnosis records from EHR source files.

    Handles both FHIR Condition JSON and flat CSV diagnosis extracts.
    These records are critical for identifying SCLC diagnoses downstream.
    """
    table_name = "ehr_conditions"
    checkpoint_path = get_checkpoint_path(table_name)

    logger.info(f"Ingesting {table_name}")

    try:
        # Ingest JSON FHIR Condition resources
        json_source = f"{RAW_PATH}/conditions/json/"
        df_json = (
            spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "json")
            .option("cloudFiles.inferColumnTypes", "true")
            .option("cloudFiles.schemaLocation", f"{checkpoint_path}/json_schema")
            .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
            .load(json_source)
        )
        df_json_enriched = add_metadata_columns(df_json, "ehr_fhir_condition_json")

        query_json = (
            df_json_enriched.writeStream
            .format("delta")
            .outputMode("append")
            .option("checkpointLocation", f"{checkpoint_path}/json")
            .option("mergeSchema", "true")
            .trigger(availableNow=True)
            .toTable(f"{FULL_SCHEMA}.{table_name}")
        )
        query_json.awaitTermination()

        # Ingest CSV condition extracts
        csv_source = f"{RAW_PATH}/conditions/csv/"
        df_csv = (
            spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "csv")
            .option("header", "true")
            .option("cloudFiles.inferColumnTypes", "true")
            .option("cloudFiles.schemaLocation", f"{checkpoint_path}/csv_schema")
            .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
            .load(csv_source)
        )
        df_csv_enriched = add_metadata_columns(df_csv, "ehr_condition_csv")

        query_csv = (
            df_csv_enriched.writeStream
            .format("delta")
            .outputMode("append")
            .option("checkpointLocation", f"{checkpoint_path}/csv")
            .option("mergeSchema", "true")
            .trigger(availableNow=True)
            .toTable(f"{FULL_SCHEMA}.{table_name}")
        )
        query_csv.awaitTermination()

        log_ingestion_metrics(table_name, df_json_enriched)
        logger.info(f"Successfully ingested {table_name}")

    except Exception as e:
        logger.error(f"Failed to ingest {table_name}: {e}", exc_info=True)
        raise

ingest_ehr_conditions()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Ingest EHR Procedures

# COMMAND ----------

def ingest_ehr_procedures() -> None:
    """
    Ingest procedure records from EHR source files.

    Captures surgical procedures, infusions, radiation treatments,
    and other clinical interventions documented in the EHR.
    """
    table_name = "ehr_procedures"
    checkpoint_path = get_checkpoint_path(table_name)

    logger.info(f"Ingesting {table_name}")

    try:
        # JSON source
        json_source = f"{RAW_PATH}/procedures/json/"
        df_json = (
            spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "json")
            .option("cloudFiles.inferColumnTypes", "true")
            .option("cloudFiles.schemaLocation", f"{checkpoint_path}/json_schema")
            .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
            .load(json_source)
        )
        df_json_enriched = add_metadata_columns(df_json, "ehr_fhir_procedure_json")

        query_json = (
            df_json_enriched.writeStream
            .format("delta")
            .outputMode("append")
            .option("checkpointLocation", f"{checkpoint_path}/json")
            .option("mergeSchema", "true")
            .trigger(availableNow=True)
            .toTable(f"{FULL_SCHEMA}.{table_name}")
        )
        query_json.awaitTermination()

        # CSV source
        csv_source = f"{RAW_PATH}/procedures/csv/"
        df_csv = (
            spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "csv")
            .option("header", "true")
            .option("cloudFiles.inferColumnTypes", "true")
            .option("cloudFiles.schemaLocation", f"{checkpoint_path}/csv_schema")
            .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
            .load(csv_source)
        )
        df_csv_enriched = add_metadata_columns(df_csv, "ehr_procedure_csv")

        query_csv = (
            df_csv_enriched.writeStream
            .format("delta")
            .outputMode("append")
            .option("checkpointLocation", f"{checkpoint_path}/csv")
            .option("mergeSchema", "true")
            .trigger(availableNow=True)
            .toTable(f"{FULL_SCHEMA}.{table_name}")
        )
        query_csv.awaitTermination()

        log_ingestion_metrics(table_name, df_json_enriched)
        logger.info(f"Successfully ingested {table_name}")

    except Exception as e:
        logger.error(f"Failed to ingest {table_name}: {e}", exc_info=True)
        raise

ingest_ehr_procedures()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Ingest EHR Observations (Labs, Vitals, Assessments)

# COMMAND ----------

def ingest_ehr_observations() -> None:
    """
    Ingest observation records from EHR source files.

    Observations include lab results (PD-L1, TMB, CBC), vital signs,
    imaging assessments (RECIST), and clinical notes extractions.
    This is typically the highest-volume EHR resource.
    """
    table_name = "ehr_observations"
    checkpoint_path = get_checkpoint_path(table_name)

    logger.info(f"Ingesting {table_name}")

    try:
        # JSON source
        json_source = f"{RAW_PATH}/observations/json/"
        df_json = (
            spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "json")
            .option("cloudFiles.inferColumnTypes", "true")
            .option("cloudFiles.schemaLocation", f"{checkpoint_path}/json_schema")
            .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
            .option("cloudFiles.maxFilesPerTrigger", 2000)
            .load(json_source)
        )
        df_json_enriched = add_metadata_columns(df_json, "ehr_fhir_observation_json")

        query_json = (
            df_json_enriched.writeStream
            .format("delta")
            .outputMode("append")
            .option("checkpointLocation", f"{checkpoint_path}/json")
            .option("mergeSchema", "true")
            .trigger(availableNow=True)
            .toTable(f"{FULL_SCHEMA}.{table_name}")
        )
        query_json.awaitTermination()

        # CSV source
        csv_source = f"{RAW_PATH}/observations/csv/"
        df_csv = (
            spark.readStream
            .format("cloudFiles")
            .option("cloudFiles.format", "csv")
            .option("header", "true")
            .option("cloudFiles.inferColumnTypes", "true")
            .option("cloudFiles.schemaLocation", f"{checkpoint_path}/csv_schema")
            .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
            .option("cloudFiles.maxFilesPerTrigger", 2000)
            .load(csv_source)
        )
        df_csv_enriched = add_metadata_columns(df_csv, "ehr_observation_csv")

        query_csv = (
            df_csv_enriched.writeStream
            .format("delta")
            .outputMode("append")
            .option("checkpointLocation", f"{checkpoint_path}/csv")
            .option("mergeSchema", "true")
            .trigger(availableNow=True)
            .toTable(f"{FULL_SCHEMA}.{table_name}")
        )
        query_csv.awaitTermination()

        log_ingestion_metrics(table_name, df_json_enriched)
        logger.info(f"Successfully ingested {table_name}")

    except Exception as e:
        logger.error(f"Failed to ingest {table_name}: {e}", exc_info=True)
        raise

ingest_ehr_observations()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Ingestion Summary

# COMMAND ----------

# Log summary of all bronze tables
bronze_tables = [
    "ehr_patients",
    "ehr_encounters",
    "ehr_conditions",
    "ehr_procedures",
    "ehr_observations",
]

logger.info("=" * 60)
logger.info("EHR Bronze Ingestion Summary")
logger.info("=" * 60)

summary_rows = []
for table_name in bronze_tables:
    full_table = f"{FULL_SCHEMA}.{table_name}"
    try:
        count = spark.sql(f"SELECT COUNT(*) as cnt FROM {full_table}").first()["cnt"]
        history = spark.sql(f"DESCRIBE HISTORY {full_table} LIMIT 1").first()
        last_modified = history["timestamp"]
        summary_rows.append((table_name, count, str(last_modified), "SUCCESS"))
        logger.info(f"  {table_name}: {count:,} rows (last modified: {last_modified})")
    except Exception as e:
        summary_rows.append((table_name, -1, "N/A", f"ERROR: {e}"))
        logger.error(f"  {table_name}: ERROR - {e}")

# Create summary DataFrame for notebook display
summary_df = spark.createDataFrame(
    summary_rows,
    ["table_name", "row_count", "last_modified", "status"],
)
display(summary_df)

logger.info(f"Batch ID: {BATCH_ID}")
logger.info(f"Ingestion completed at: {datetime.utcnow().isoformat()}")
logger.info("=" * 60)
