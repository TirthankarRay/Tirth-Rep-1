# Databricks notebook source
"""
Gold Layer: Export to Amazon Redshift
Syncs all Silver dimension/fact tables and Gold aggregation tables to Redshift Serverless.
Uses JDBC connector with S3 staging for COPY command performance.
"""

# COMMAND ----------

# MAGIC %md
# MAGIC # Export Pipeline — Databricks → Amazon Redshift
# MAGIC Transfers processed data from Delta Lake to Redshift serving layer:
# MAGIC - Silver dims/facts → `sclc_core` schema
# MAGIC - Gold aggregations → `sclc_analytics` schema

# COMMAND ----------

dbutils.widgets.text("environment", "dev", "Environment (dev/staging/prod)")
dbutils.widgets.text("export_mode", "full", "Export mode (full/incremental)")
ENV = dbutils.widgets.get("environment")
EXPORT_MODE = dbutils.widgets.get("export_mode")

CATALOG = f"sclc_{ENV}"
SILVER_SCHEMA = f"{CATALOG}.silver"
GOLD_SCHEMA = f"{CATALOG}.gold"

# COMMAND ----------

import logging
import time
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("export.redshift")

start_time = time.time()
logger.info(f"Starting Redshift export — env={ENV}, mode={EXPORT_MODE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Redshift Connection Configuration

# COMMAND ----------

# Retrieve credentials from AWS Secrets Manager
secret_scope = f"sclc-{ENV}"
secret_key = "redshift-credentials"

try:
    import json
    secret_json = dbutils.secrets.get(scope=secret_scope, key=secret_key)
    creds = json.loads(secret_json)
    REDSHIFT_HOST = creds["host"]
    REDSHIFT_PORT = creds.get("port", "5439")
    REDSHIFT_DB = creds["database"]
    REDSHIFT_USER = creds["username"]
    REDSHIFT_PASS = creds["password"]
except Exception as e:
    logger.error(f"Failed to retrieve Redshift credentials: {e}")
    raise

REDSHIFT_URL = f"jdbc:redshift://{REDSHIFT_HOST}:{REDSHIFT_PORT}/{REDSHIFT_DB}"
S3_STAGING = f"s3://sclc-data-lake-{ENV}/staging/redshift/"
REDSHIFT_IAM_ROLE = f"arn:aws:iam::role/sclc-{ENV}-redshift-s3-access"

logger.info(f"Redshift endpoint: {REDSHIFT_HOST}:{REDSHIFT_PORT}/{REDSHIFT_DB}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Export Helper Functions

# COMMAND ----------

def export_table(source_table, target_schema, target_table, mode="overwrite"):
    """Export a Delta table to Redshift via S3 COPY."""
    full_source = source_table
    full_target = f"{target_schema}.{target_table}"
    staging_path = f"{S3_STAGING}{target_table}/{datetime.now().strftime('%Y%m%d_%H%M%S')}/"

    logger.info(f"Exporting {full_source} → {full_target}")
    table_start = time.time()

    try:
        df = spark.read.table(full_source)
        row_count = df.count()

        if row_count == 0:
            logger.warning(f"Skipping {full_source}: 0 rows")
            return {"table": full_target, "status": "skipped", "rows": 0}

        # Write to Redshift using COPY via S3 staging
        (
            df.write
            .format("io.github.spark_redshift_community.spark.redshift")
            .option("url", REDSHIFT_URL)
            .option("user", REDSHIFT_USER)
            .option("password", REDSHIFT_PASS)
            .option("dbtable", full_target)
            .option("tempdir", staging_path)
            .option("aws_iam_role", REDSHIFT_IAM_ROLE)
            .option("tempformat", "CSV GZIP")
            .option("preactions", f"TRUNCATE TABLE {full_target};" if mode == "overwrite" else "")
            .option("extracopyoptions", "BLANKSASNULL EMPTYASNULL ACCEPTINVCHARS TRUNCATECOLUMNS")
            .mode("append")  # Use append after truncate for clean overwrite
            .save()
        )

        duration = round(time.time() - table_start, 1)
        logger.info(f"  Exported {row_count:,} rows in {duration}s")
        return {"table": full_target, "status": "success", "rows": row_count, "duration_s": duration}

    except Exception as e:
        logger.error(f"  FAILED: {full_target} — {str(e)}")
        return {"table": full_target, "status": "failed", "error": str(e)}


def execute_redshift_sql(sql_statement):
    """Execute a SQL statement on Redshift via JDBC."""
    logger.info(f"Executing Redshift SQL: {sql_statement[:100]}...")
    try:
        spark.read \
            .format("io.github.spark_redshift_community.spark.redshift") \
            .option("url", REDSHIFT_URL) \
            .option("user", REDSHIFT_USER) \
            .option("password", REDSHIFT_PASS) \
            .option("query", sql_statement) \
            .option("tempdir", f"{S3_STAGING}_temp/") \
            .option("aws_iam_role", REDSHIFT_IAM_ROLE) \
            .load()
        logger.info("  SQL executed successfully")
    except Exception as e:
        # Some DDL statements don't return results, which may cause read errors
        if "EmptyDataFrame" in str(e) or "no results" in str(e).lower():
            logger.info("  SQL executed (no result set)")
        else:
            logger.error(f"  SQL failed: {e}")
            raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Export Silver Tables → sclc_core

# COMMAND ----------

silver_exports = [
    (f"{SILVER_SCHEMA}.dim_patient", "sclc_core", "dim_patient"),
    (f"{SILVER_SCHEMA}.dim_facility", "sclc_core", "dim_facility"),
    (f"{SILVER_SCHEMA}.fact_diagnosis", "sclc_core", "fact_diagnosis"),
    (f"{SILVER_SCHEMA}.fact_treatment_episode", "sclc_core", "fact_treatment_episode"),
    (f"{SILVER_SCHEMA}.fact_response_assessment", "sclc_core", "fact_response_assessment"),
    (f"{SILVER_SCHEMA}.fact_biomarker_test", "sclc_core", "fact_biomarker_test"),
    (f"{SILVER_SCHEMA}.fact_progression_event", "sclc_core", "fact_progression_event"),
    (f"{SILVER_SCHEMA}.fact_trial_enrollment", "sclc_core", "fact_trial_enrollment"),
]

silver_results = []
for source, target_schema, target_table in silver_exports:
    result = export_table(source, target_schema, target_table)
    silver_results.append(result)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Export Gold Tables → sclc_analytics

# COMMAND ----------

gold_exports = [
    (f"{GOLD_SCHEMA}.agg_overview_metrics", "sclc_analytics", "agg_overview_metrics"),
    (f"{GOLD_SCHEMA}.agg_time_to_treatment", "sclc_analytics", "agg_time_to_treatment"),
    (f"{GOLD_SCHEMA}.agg_treatment_patterns", "sclc_analytics", "agg_treatment_patterns"),
    (f"{GOLD_SCHEMA}.agg_geographic_metrics", "sclc_analytics", "agg_geographic_metrics"),
    (f"{GOLD_SCHEMA}.agg_sankey_journey", "sclc_analytics", "agg_sankey_journey"),
]

gold_results = []
for source, target_schema, target_table in gold_exports:
    result = export_table(source, target_schema, target_table)
    gold_results.append(result)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Refresh Materialized Views

# COMMAND ----------

materialized_views = [
    "sclc_core.mv_patient_latest_status",
    "sclc_core.mv_treatment_timeline",
    "sclc_analytics.mv_kpi_current",
]

for mv in materialized_views:
    try:
        execute_redshift_sql(f"REFRESH MATERIALIZED VIEW {mv}")
        logger.info(f"Refreshed materialized view: {mv}")
    except Exception as e:
        logger.warning(f"Could not refresh {mv}: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Export Summary

# COMMAND ----------

all_results = silver_results + gold_results
total_rows = sum(r.get("rows", 0) for r in all_results)
successes = sum(1 for r in all_results if r["status"] == "success")
failures = sum(1 for r in all_results if r["status"] == "failed")
skipped = sum(1 for r in all_results if r["status"] == "skipped")
total_duration = round(time.time() - start_time, 1)

summary = {
    "timestamp": datetime.now().isoformat(),
    "environment": ENV,
    "export_mode": EXPORT_MODE,
    "tables_exported": successes,
    "tables_failed": failures,
    "tables_skipped": skipped,
    "total_rows": total_rows,
    "total_duration_seconds": total_duration,
}

logger.info(f"Export complete: {successes} succeeded, {failures} failed, {skipped} skipped")
logger.info(f"Total rows exported: {total_rows:,}")
logger.info(f"Total duration: {total_duration}s")

# Display results
import pandas as pd
results_df = pd.DataFrame(all_results)
display(spark.createDataFrame(results_df))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Emit CloudWatch Metrics

# COMMAND ----------

try:
    import boto3

    cloudwatch = boto3.client("cloudwatch", region_name="us-east-1")

    metrics = [
        {"MetricName": "ExportTablesSuccess", "Value": successes, "Unit": "Count"},
        {"MetricName": "ExportTablesFailed", "Value": failures, "Unit": "Count"},
        {"MetricName": "ExportTotalRows", "Value": total_rows, "Unit": "Count"},
        {"MetricName": "ExportDurationSeconds", "Value": total_duration, "Unit": "Seconds"},
    ]

    cloudwatch.put_metric_data(
        Namespace=f"SCLC/{ENV}/DataPipeline",
        MetricData=[
            {
                "MetricName": m["MetricName"],
                "Value": m["Value"],
                "Unit": m["Unit"],
                "Dimensions": [
                    {"Name": "Environment", "Value": ENV},
                    {"Name": "Pipeline", "Value": "redshift-export"},
                ],
            }
            for m in metrics
        ],
    )
    logger.info("CloudWatch metrics emitted successfully")
except Exception as e:
    logger.warning(f"Failed to emit CloudWatch metrics: {e}")

# COMMAND ----------

# Fail the notebook if any exports failed
if failures > 0:
    failed_tables = [r["table"] for r in all_results if r["status"] == "failed"]
    raise RuntimeError(f"Export failed for {failures} table(s): {', '.join(failed_tables)}")

logger.info("All exports completed successfully")
