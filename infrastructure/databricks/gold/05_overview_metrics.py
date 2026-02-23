# Databricks notebook source
# MAGIC %md
# MAGIC # Gold Layer: Overview KPI Metrics
# MAGIC
# MAGIC **Pipeline:** SCLC Patient Journey Analytics
# MAGIC **Layer:** Gold (Pre-aggregated KPIs)
# MAGIC **Source:** Silver dimension and fact tables
# MAGIC **Target:** `gold.agg_overview_metrics`
# MAGIC
# MAGIC ## Metrics Calculated
# MAGIC For each combination of (snapshot_date, stage_filter, state_filter):
# MAGIC
# MAGIC | Metric | Description |
# MAGIC |--------|-------------|
# MAGIC | `total_patients` | COUNT DISTINCT patients |
# MAGIC | `new_diagnoses_mtd` | New diagnoses month-to-date |
# MAGIC | `new_diagnoses_qtd` | New diagnoses quarter-to-date |
# MAGIC | `new_diagnoses_ytd` | New diagnoses year-to-date |
# MAGIC | `median_time_to_treatment` | Median days diagnosis to first treatment |
# MAGIC | `biomarker_testing_rate` | % patients with at least one biomarker test |
# MAGIC | `immunotherapy_uptake_rate` | % ES-SCLC patients receiving IO |
# MAGIC | `clinical_trial_rate` | % patients enrolled in clinical trials |

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

import logging
from datetime import date, datetime

from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DateType,
    DoubleType,
    IntegerType,
    LongType,
    StringType,
)

# COMMAND ----------

# Widget parameters
dbutils.widgets.dropdown("environment", "dev", ["dev", "staging", "prod"], "Environment")
dbutils.widgets.text("catalog", "sclc_analytics", "Unity Catalog Name")
dbutils.widgets.text("snapshot_date", "", "Snapshot Date (YYYY-MM-DD, blank=today)")

ENV = dbutils.widgets.get("environment")
CATALOG = dbutils.widgets.get("catalog")
SNAPSHOT_DATE_STR = dbutils.widgets.get("snapshot_date")

# COMMAND ----------

SILVER_SCHEMA = f"{CATALOG}.silver"
GOLD_SCHEMA = f"{CATALOG}.gold"

SNAPSHOT_DATE = (
    datetime.strptime(SNAPSHOT_DATE_STR, "%Y-%m-%d").date()
    if SNAPSHOT_DATE_STR
    else date.today()
)

# COMMAND ----------

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("gold.overview_metrics")
logger.setLevel(logging.INFO)

logger.info(f"Starting Overview KPI Metrics calculation")
logger.info(f"Snapshot Date: {SNAPSHOT_DATE}")

# COMMAND ----------

spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS gold")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Silver Tables

# COMMAND ----------

df_patients = (
    spark.table(f"{SILVER_SCHEMA}.dim_patient")
    .filter(F.col("is_current") == True)
)
df_diagnosis = spark.table(f"{SILVER_SCHEMA}.fact_diagnosis")
df_treatment = spark.table(f"{SILVER_SCHEMA}.fact_treatment_episode")
df_biomarker = spark.table(f"{SILVER_SCHEMA}.fact_biomarker_test")
df_trial = spark.table(f"{SILVER_SCHEMA}.fact_trial_enrollment")

logger.info("Silver tables loaded")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Build Denormalized Patient Base

# COMMAND ----------

def build_patient_base() -> DataFrame:
    """
    Build a denormalized patient base table by joining the patient
    dimension with first diagnosis date, stage, and state.

    Returns
    -------
    DataFrame
        Patient-level base table with diagnosis context.
    """
    # First diagnosis per patient
    df_first_dx = (
        df_diagnosis
        .groupBy("patient_id")
        .agg(
            F.min("diagnosis_date").alias("first_diagnosis_date"),
            F.first(
                F.when(F.col("sclc_stage") != "Unknown", F.col("sclc_stage")),
                ignorenulls=True,
            ).alias("sclc_stage"),
        )
    )

    # First treatment per patient
    df_first_tx = (
        df_treatment
        .filter(F.col("line_of_therapy") == 1)
        .groupBy("patient_id")
        .agg(
            F.min("episode_start_date").alias("first_treatment_date"),
            F.first("regimen_category").alias("first_line_regimen_category"),
        )
    )

    # Any biomarker test
    df_has_biomarker = (
        df_biomarker
        .groupBy("patient_id")
        .agg(F.lit(True).alias("has_biomarker_test"))
    )

    # Any IO treatment
    df_has_io = (
        df_treatment
        .filter(F.col("has_io") == True)
        .select("patient_id")
        .distinct()
        .withColumn("received_io", F.lit(True))
    )

    # Any trial enrollment
    df_has_trial = (
        df_trial
        .select("patient_id")
        .distinct()
        .withColumn("enrolled_in_trial", F.lit(True))
    )

    df_base = (
        df_patients
        .join(df_first_dx, on="patient_id", how="inner")
        .join(df_first_tx, on="patient_id", how="left")
        .join(df_has_biomarker, on="patient_id", how="left")
        .join(df_has_io, on="patient_id", how="left")
        .join(df_has_trial, on="patient_id", how="left")
        .withColumn(
            "has_biomarker_test", F.coalesce(F.col("has_biomarker_test"), F.lit(False))
        )
        .withColumn(
            "received_io", F.coalesce(F.col("received_io"), F.lit(False))
        )
        .withColumn(
            "enrolled_in_trial", F.coalesce(F.col("enrolled_in_trial"), F.lit(False))
        )
        .withColumn(
            "time_to_treatment_days",
            F.datediff(F.col("first_treatment_date"), F.col("first_diagnosis_date")),
        )
        # Only include patients diagnosed on or before the snapshot date
        .filter(F.col("first_diagnosis_date") <= F.lit(SNAPSHOT_DATE))
    )

    logger.info(f"Patient base built: {df_base.count():,} SCLC patients")
    return df_base

# COMMAND ----------

df_base = build_patient_base()
df_base.cache()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Calculate Metrics per Filter Combination

# COMMAND ----------

def calculate_overview_metrics(df_base: DataFrame) -> DataFrame:
    """
    Calculate all overview KPI metrics for every combination of
    stage_filter and state_filter.

    Produces one row per (snapshot_date, stage_filter, state_filter)
    with all metric columns.

    Parameters
    ----------
    df_base : DataFrame
        Denormalized patient base table.

    Returns
    -------
    DataFrame
        Aggregated KPI metrics.
    """
    logger.info("Calculating overview KPI metrics")

    snapshot = SNAPSHOT_DATE
    snapshot_year = snapshot.year
    snapshot_month = snapshot.month
    snapshot_quarter = (snapshot_month - 1) // 3 + 1

    # Period boundaries
    month_start = date(snapshot_year, snapshot_month, 1)
    quarter_month = (snapshot_quarter - 1) * 3 + 1
    quarter_start = date(snapshot_year, quarter_month, 1)
    year_start = date(snapshot_year, 1, 1)

    # Generate filter combinations
    stage_filters = [None, "LS-SCLC", "ES-SCLC"]  # None means "all"
    states = [row["state"] for row in df_base.select("state").distinct().collect() if row["state"]]
    state_filters = [None] + states  # None means "all"

    results = []

    for stage_filter in stage_filters:
        for state_filter in state_filters:
            # Apply filters
            df_filtered = df_base

            if stage_filter:
                df_filtered = df_filtered.filter(F.col("sclc_stage") == stage_filter)
            if state_filter:
                df_filtered = df_filtered.filter(F.col("state") == state_filter)

            # Skip if no data
            total_patients = df_filtered.count()
            if total_patients == 0:
                continue

            # New diagnoses by period
            new_diagnoses_mtd = df_filtered.filter(
                (F.col("first_diagnosis_date") >= F.lit(month_start)) &
                (F.col("first_diagnosis_date") <= F.lit(snapshot))
            ).count()

            new_diagnoses_qtd = df_filtered.filter(
                (F.col("first_diagnosis_date") >= F.lit(quarter_start)) &
                (F.col("first_diagnosis_date") <= F.lit(snapshot))
            ).count()

            new_diagnoses_ytd = df_filtered.filter(
                (F.col("first_diagnosis_date") >= F.lit(year_start)) &
                (F.col("first_diagnosis_date") <= F.lit(snapshot))
            ).count()

            # Median time to treatment
            ttt_stats = df_filtered.filter(
                F.col("time_to_treatment_days").isNotNull()
            ).agg(
                F.percentile_approx("time_to_treatment_days", 0.5).alias("median_ttt"),
            ).first()
            median_time_to_treatment = ttt_stats["median_ttt"] if ttt_stats else None

            # Biomarker testing rate
            biomarker_tested = df_filtered.filter(
                F.col("has_biomarker_test") == True
            ).count()
            biomarker_testing_rate = (
                round(100.0 * biomarker_tested / total_patients, 2)
                if total_patients > 0 else 0.0
            )

            # Immunotherapy uptake rate (among ES-SCLC patients)
            es_patients = df_filtered.filter(F.col("sclc_stage") == "ES-SCLC")
            es_count = es_patients.count()
            es_io_count = es_patients.filter(F.col("received_io") == True).count()
            immunotherapy_uptake_rate = (
                round(100.0 * es_io_count / es_count, 2)
                if es_count > 0 else 0.0
            )

            # Clinical trial enrollment rate
            trial_enrolled = df_filtered.filter(
                F.col("enrolled_in_trial") == True
            ).count()
            clinical_trial_rate = (
                round(100.0 * trial_enrolled / total_patients, 2)
                if total_patients > 0 else 0.0
            )

            results.append((
                str(snapshot),
                stage_filter if stage_filter else "all",
                state_filter if state_filter else "all",
                total_patients,
                new_diagnoses_mtd,
                new_diagnoses_qtd,
                new_diagnoses_ytd,
                float(median_time_to_treatment) if median_time_to_treatment else None,
                biomarker_testing_rate,
                immunotherapy_uptake_rate,
                clinical_trial_rate,
                biomarker_tested,
                es_count,
                es_io_count,
                trial_enrolled,
            ))

    schema = [
        "snapshot_date",
        "stage_filter",
        "state_filter",
        "total_patients",
        "new_diagnoses_mtd",
        "new_diagnoses_qtd",
        "new_diagnoses_ytd",
        "median_time_to_treatment",
        "biomarker_testing_rate",
        "immunotherapy_uptake_rate",
        "clinical_trial_rate",
        "biomarker_tested_count",
        "es_sclc_patient_count",
        "es_sclc_io_count",
        "trial_enrolled_count",
    ]

    df_metrics = spark.createDataFrame(results, schema)

    # Cast types
    df_metrics = (
        df_metrics
        .withColumn("snapshot_date", F.to_date(F.col("snapshot_date")))
        .withColumn("total_patients", F.col("total_patients").cast(LongType()))
        .withColumn("new_diagnoses_mtd", F.col("new_diagnoses_mtd").cast(LongType()))
        .withColumn("new_diagnoses_qtd", F.col("new_diagnoses_qtd").cast(LongType()))
        .withColumn("new_diagnoses_ytd", F.col("new_diagnoses_ytd").cast(LongType()))
        .withColumn("median_time_to_treatment", F.col("median_time_to_treatment").cast(DoubleType()))
        .withColumn("biomarker_testing_rate", F.col("biomarker_testing_rate").cast(DoubleType()))
        .withColumn("immunotherapy_uptake_rate", F.col("immunotherapy_uptake_rate").cast(DoubleType()))
        .withColumn("clinical_trial_rate", F.col("clinical_trial_rate").cast(DoubleType()))
        .withColumn("_updated_timestamp", F.current_timestamp())
    )

    logger.info(f"Overview metrics: {df_metrics.count():,} rows generated")
    return df_metrics

# COMMAND ----------

df_metrics = calculate_overview_metrics(df_base)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Write to Gold Table

# COMMAND ----------

TARGET_TABLE = f"{GOLD_SCHEMA}.agg_overview_metrics"

# Create table if not exists, otherwise overwrite current snapshot partition
if not spark.catalog.tableExists(TARGET_TABLE):
    logger.info(f"Creating {TARGET_TABLE}")
    (
        df_metrics.write
        .format("delta")
        .partitionBy("snapshot_date")
        .saveAsTable(TARGET_TABLE)
    )
else:
    logger.info(f"Overwriting snapshot_date={SNAPSHOT_DATE} partition in {TARGET_TABLE}")
    (
        df_metrics.write
        .format("delta")
        .mode("overwrite")
        .option("replaceWhere", f"snapshot_date = '{SNAPSHOT_DATE}'")
        .saveAsTable(TARGET_TABLE)
    )

spark.sql(f"OPTIMIZE {TARGET_TABLE}")
logger.info(f"Successfully wrote overview metrics to {TARGET_TABLE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validation

# COMMAND ----------

display(spark.sql(f"""
    SELECT
        snapshot_date,
        stage_filter,
        COUNT(*) as state_count,
        SUM(total_patients) as sum_patients,
        AVG(median_time_to_treatment) as avg_median_ttt,
        AVG(biomarker_testing_rate) as avg_biomarker_rate,
        AVG(immunotherapy_uptake_rate) as avg_io_rate,
        AVG(clinical_trial_rate) as avg_trial_rate
    FROM {TARGET_TABLE}
    WHERE snapshot_date = '{SNAPSHOT_DATE}'
    GROUP BY snapshot_date, stage_filter
    ORDER BY snapshot_date, stage_filter
"""))

# COMMAND ----------

df_base.unpersist()
logger.info("Overview metrics processing complete")
