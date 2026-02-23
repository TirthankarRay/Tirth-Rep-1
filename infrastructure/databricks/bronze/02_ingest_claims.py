# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze Layer: Claims Data Ingestion
# MAGIC
# MAGIC **Pipeline:** SCLC Patient Journey Analytics
# MAGIC **Layer:** Bronze (Raw Ingestion)
# MAGIC **Source:** S3 Landing Zone - Claims data (CSV, Parquet)
# MAGIC **Target:** Delta Bronze tables in Unity Catalog
# MAGIC
# MAGIC ## Tables Produced
# MAGIC | Table | Source Format | Description |
# MAGIC |-------|--------------|-------------|
# MAGIC | `bronze.claims_professional` | CSV / Parquet | CMS-1500 professional claims |
# MAGIC | `bronze.claims_institutional` | CSV / Parquet | UB-04 institutional/facility claims |
# MAGIC | `bronze.claims_pharmacy` | CSV / Parquet | NCPDP pharmacy/Rx claims |
# MAGIC
# MAGIC ## Ingestion Strategy
# MAGIC - **Auto Loader** (cloudFiles) for incremental file ingestion
# MAGIC - Date-partitioned output for efficient downstream queries
# MAGIC - Schema evolution enabled to accommodate payer format variations

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

import logging
import uuid
from datetime import datetime

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DateType,
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

# COMMAND ----------

# Widget parameters
dbutils.widgets.dropdown("environment", "dev", ["dev", "staging", "prod"], "Environment")
dbutils.widgets.text("catalog", "sclc_analytics", "Unity Catalog Name")
dbutils.widgets.text("batch_id_override", "", "Batch ID Override (optional)")
dbutils.widgets.dropdown("file_format", "csv", ["csv", "parquet", "mixed"], "Source File Format")

ENV = dbutils.widgets.get("environment")
CATALOG = dbutils.widgets.get("catalog")
BATCH_ID_OVERRIDE = dbutils.widgets.get("batch_id_override")
FILE_FORMAT = dbutils.widgets.get("file_format")

# COMMAND ----------

# Derived configuration
S3_BASE = f"s3://sclc-data-lake-{ENV}"
RAW_PATH = f"{S3_BASE}/raw/claims"
CHECKPOINT_BASE = f"{S3_BASE}/checkpoints/bronze/claims"
SCHEMA_BASE = "bronze"

BATCH_ID = BATCH_ID_OVERRIDE if BATCH_ID_OVERRIDE else str(uuid.uuid4())
FULL_SCHEMA = f"{CATALOG}.{SCHEMA_BASE}"

# COMMAND ----------

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("bronze.claims_ingestion")
logger.setLevel(logging.INFO)

logger.info(f"Starting Claims Bronze ingestion")
logger.info(f"Environment: {ENV}")
logger.info(f"Catalog: {CATALOG}")
logger.info(f"Batch ID: {BATCH_ID}")
logger.info(f"Raw Path: {RAW_PATH}")
logger.info(f"File Format: {FILE_FORMAT}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Utility Functions

# COMMAND ----------

def add_metadata_columns(df: DataFrame, source_description: str) -> DataFrame:
    """
    Append standard metadata columns and a partition date column to
    a DataFrame for lineage tracking and efficient partitioning.

    Parameters
    ----------
    df : DataFrame
        Source DataFrame to enrich.
    source_description : str
        Human-readable description of the data source.

    Returns
    -------
    DataFrame
        Enriched DataFrame with metadata and partition columns.
    """
    return (
        df
        .withColumn("_ingestion_timestamp", F.current_timestamp())
        .withColumn("_source_file", F.input_file_name())
        .withColumn("_batch_id", F.lit(BATCH_ID))
        .withColumn("_source_description", F.lit(source_description))
        .withColumn("_ingestion_date", F.current_date())
        .withColumn("_partition_date", F.current_date())
    )


def derive_partition_date(df: DataFrame, date_column: str) -> DataFrame:
    """
    Derive _partition_date from an existing date column when available.

    Falls back to current_date() if the source column is null or
    cannot be parsed.

    Parameters
    ----------
    df : DataFrame
        DataFrame containing the date column.
    date_column : str
        Name of the column to derive the partition date from.

    Returns
    -------
    DataFrame
        DataFrame with _partition_date derived from the source column.
    """
    return df.withColumn(
        "_partition_date",
        F.coalesce(
            F.to_date(F.col(date_column)),
            F.current_date(),
        ),
    )


def get_checkpoint_path(table_name: str, format_type: str = "") -> str:
    """Return the S3 checkpoint location for a given table and format."""
    suffix = f"/{format_type}" if format_type else ""
    return f"{CHECKPOINT_BASE}/{table_name}{suffix}"


def log_ingestion_metrics(table_name: str) -> None:
    """Log row count and partition information for an ingested table."""
    full_table = f"{FULL_SCHEMA}.{table_name}"
    try:
        count = spark.sql(f"SELECT COUNT(*) as cnt FROM {full_table}").first()["cnt"]
        partitions = spark.sql(
            f"SELECT COUNT(DISTINCT _partition_date) as parts FROM {full_table}"
        ).first()["parts"]
        logger.info(f"Table {full_table}: {count:,} total rows across {partitions} partitions")
    except Exception as e:
        logger.warning(f"Could not retrieve metrics for {full_table}: {e}")


def ingest_claims_table(
    table_name: str,
    source_subpath: str,
    source_description: str,
    service_date_column: str = "service_from_date",
) -> None:
    """
    Generic claims ingestion function using Auto Loader.

    Supports CSV, Parquet, and mixed-format ingestion.  Adds metadata
    columns, derives partition date from the service date column, and
    writes to a date-partitioned Delta table.

    Parameters
    ----------
    table_name : str
        Target bronze table name (without schema prefix).
    source_subpath : str
        Subdirectory under the raw claims path.
    source_description : str
        Human-readable label for lineage metadata.
    service_date_column : str
        Column name containing the claim service date used for
        partition derivation.
    """
    checkpoint_path = get_checkpoint_path(table_name)
    source_path = f"{RAW_PATH}/{source_subpath}/"

    logger.info(f"Ingesting {table_name} from {source_path}")

    try:
        formats_to_ingest = []
        if FILE_FORMAT == "csv":
            formats_to_ingest = [("csv", {"header": "true"})]
        elif FILE_FORMAT == "parquet":
            formats_to_ingest = [("parquet", {})]
        else:
            # Mixed mode: ingest both CSV and Parquet
            formats_to_ingest = [
                ("csv", {"header": "true"}),
                ("parquet", {}),
            ]

        for fmt, extra_options in formats_to_ingest:
            fmt_checkpoint = f"{checkpoint_path}/{fmt}"
            fmt_source = (
                f"{source_path}{fmt}/"
                if FILE_FORMAT == "mixed"
                else source_path
            )

            logger.info(f"  Reading {fmt} files from {fmt_source}")

            reader = (
                spark.readStream
                .format("cloudFiles")
                .option("cloudFiles.format", fmt)
                .option("cloudFiles.inferColumnTypes", "true")
                .option("cloudFiles.schemaLocation", f"{fmt_checkpoint}/schema")
                .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
                .option("cloudFiles.maxFilesPerTrigger", 1000)
            )

            # Apply format-specific options (e.g., header for CSV)
            for key, value in extra_options.items():
                reader = reader.option(key, value)

            df = reader.load(fmt_source)

            # Add metadata columns
            df_enriched = add_metadata_columns(df, f"{source_description}_{fmt}")

            # Derive partition date from service date if present
            if service_date_column in df.columns:
                df_enriched = derive_partition_date(df_enriched, service_date_column)

            query = (
                df_enriched.writeStream
                .format("delta")
                .outputMode("append")
                .option("checkpointLocation", fmt_checkpoint)
                .option("mergeSchema", "true")
                .partitionBy("_partition_date")
                .trigger(availableNow=True)
                .toTable(f"{FULL_SCHEMA}.{table_name}")
            )

            query.awaitTermination()
            logger.info(f"  Completed {fmt} ingestion for {table_name}")

        log_ingestion_metrics(table_name)
        logger.info(f"Successfully ingested {table_name}")

    except Exception as e:
        logger.error(f"Failed to ingest {table_name}: {e}", exc_info=True)
        raise

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
# MAGIC ## 1. Ingest Professional Claims (CMS-1500)
# MAGIC
# MAGIC Professional claims from physician offices, outpatient clinics,
# MAGIC and ambulatory care settings.  Contains CPT/HCPCS procedure codes,
# MAGIC ICD-10 diagnoses, and provider information.

# COMMAND ----------

ingest_claims_table(
    table_name="claims_professional",
    source_subpath="professional",
    source_description="claims_professional",
    service_date_column="service_from_date",
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Ingest Institutional Claims (UB-04)
# MAGIC
# MAGIC Institutional claims from hospitals, skilled nursing facilities,
# MAGIC and other inpatient/outpatient facilities.  Contains revenue codes,
# MAGIC DRG codes, and admission/discharge information.

# COMMAND ----------

ingest_claims_table(
    table_name="claims_institutional",
    source_subpath="institutional",
    source_description="claims_institutional",
    service_date_column="admission_date",
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Ingest Pharmacy Claims (NCPDP)
# MAGIC
# MAGIC Pharmacy claims capturing outpatient drug dispensing events.
# MAGIC Contains NDC codes, days supply, quantity, and prescriber info.
# MAGIC Important for capturing oral oncology agents and supportive care.

# COMMAND ----------

ingest_claims_table(
    table_name="claims_pharmacy",
    source_subpath="pharmacy",
    source_description="claims_pharmacy",
    service_date_column="fill_date",
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Ingestion Summary

# COMMAND ----------

claims_tables = [
    "claims_professional",
    "claims_institutional",
    "claims_pharmacy",
]

logger.info("=" * 60)
logger.info("Claims Bronze Ingestion Summary")
logger.info("=" * 60)

summary_rows = []
for table_name in claims_tables:
    full_table = f"{FULL_SCHEMA}.{table_name}"
    try:
        stats = spark.sql(f"""
            SELECT
                COUNT(*) as total_rows,
                COUNT(DISTINCT _partition_date) as partition_count,
                MIN(_partition_date) as min_date,
                MAX(_partition_date) as max_date,
                COUNT(DISTINCT _batch_id) as batch_count
            FROM {full_table}
        """).first()

        summary_rows.append((
            table_name,
            stats["total_rows"],
            stats["partition_count"],
            str(stats["min_date"]),
            str(stats["max_date"]),
            stats["batch_count"],
            "SUCCESS",
        ))
        logger.info(
            f"  {table_name}: {stats['total_rows']:,} rows, "
            f"{stats['partition_count']} partitions "
            f"({stats['min_date']} to {stats['max_date']})"
        )
    except Exception as e:
        summary_rows.append((table_name, -1, 0, "N/A", "N/A", 0, f"ERROR: {e}"))
        logger.error(f"  {table_name}: ERROR - {e}")

summary_df = spark.createDataFrame(
    summary_rows,
    [
        "table_name",
        "total_rows",
        "partition_count",
        "min_date",
        "max_date",
        "batch_count",
        "status",
    ],
)
display(summary_df)

logger.info(f"Batch ID: {BATCH_ID}")
logger.info(f"Ingestion completed at: {datetime.utcnow().isoformat()}")
logger.info("=" * 60)
