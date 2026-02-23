# Databricks notebook source
# MAGIC %md
# MAGIC # Gold Layer: Treatment Analytics
# MAGIC
# MAGIC **Pipeline:** SCLC Patient Journey Analytics
# MAGIC **Layer:** Gold (Pre-aggregated KPIs)
# MAGIC **Source:** Silver dimension and fact tables
# MAGIC **Targets:**
# MAGIC - `gold.agg_time_to_treatment` -- Time-to-treatment distribution
# MAGIC - `gold.agg_treatment_patterns` -- Treatment regimen patterns by line of therapy
# MAGIC
# MAGIC ## Analytics Produced
# MAGIC
# MAGIC ### Time-to-Treatment Distribution
# MAGIC - Days from diagnosis to first treatment per patient
# MAGIC - Bucketed into 0-7, 8-14, 15-21, 22-30, 31+ day intervals
# MAGIC - Median, mean, and within-target percentage (target = 21 days)
# MAGIC
# MAGIC ### Treatment Patterns
# MAGIC - Patient counts per regimen category per line of therapy
# MAGIC - Percentage breakdowns within each line

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

# Target: 21 days from diagnosis to first treatment
TTT_TARGET_DAYS = 21

# Time-to-treatment bucket definitions
TTT_BUCKETS = [
    (0, 7, "0-7 days"),
    (8, 14, "8-14 days"),
    (15, 21, "15-21 days"),
    (22, 30, "22-30 days"),
    (31, 9999, "31+ days"),
]

# COMMAND ----------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("gold.treatment_analytics")
logger.setLevel(logging.INFO)

logger.info(f"Starting Treatment Analytics calculation")
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

logger.info("Silver tables loaded")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part 1: Time-to-Treatment Distribution

# COMMAND ----------

def build_time_to_treatment_distribution() -> DataFrame:
    """
    Calculate the time-to-treatment distribution for SCLC patients.

    For each patient, measures days between first SCLC diagnosis and
    first treatment.  Buckets results into clinically meaningful
    intervals and calculates summary statistics.

    Produces aggregated rows per (snapshot_date, stage_filter,
    ttt_bucket) plus a summary row with overall statistics.

    Returns
    -------
    DataFrame
        Time-to-treatment distribution records.
    """
    logger.info("Building time-to-treatment distribution")

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
        .agg(F.min("episode_start_date").alias("first_treatment_date"))
    )

    # Join and calculate TTT
    df_ttt = (
        df_first_dx
        .join(df_first_tx, on="patient_id", how="inner")
        .withColumn(
            "time_to_treatment_days",
            F.datediff(F.col("first_treatment_date"), F.col("first_diagnosis_date")),
        )
        .filter(
            (F.col("time_to_treatment_days") >= 0) &
            (F.col("first_diagnosis_date") <= F.lit(SNAPSHOT_DATE))
        )
        .join(
            df_patients.select("patient_id", "state"),
            on="patient_id",
            how="left",
        )
    )

    # Assign buckets
    bucket_expr = F.lit(None).cast(StringType())
    bucket_order_expr = F.lit(None).cast(IntegerType())

    for idx, (low, high, label) in enumerate(TTT_BUCKETS):
        bucket_expr = F.when(
            (F.col("time_to_treatment_days") >= low) &
            (F.col("time_to_treatment_days") <= high),
            F.lit(label),
        ).otherwise(bucket_expr)

        bucket_order_expr = F.when(
            (F.col("time_to_treatment_days") >= low) &
            (F.col("time_to_treatment_days") <= high),
            F.lit(idx),
        ).otherwise(bucket_order_expr)

    df_bucketed = (
        df_ttt
        .withColumn("ttt_bucket", bucket_expr)
        .withColumn("bucket_order", bucket_order_expr)
        .withColumn(
            "within_target",
            F.col("time_to_treatment_days") <= TTT_TARGET_DAYS,
        )
    )

    # Calculate per stage filter
    stage_filters = [None, "LS-SCLC", "ES-SCLC"]
    all_results = []

    for stage_filter in stage_filters:
        df_filtered = df_bucketed
        stage_label = "all"

        if stage_filter:
            df_filtered = df_filtered.filter(F.col("sclc_stage") == stage_filter)
            stage_label = stage_filter

        total_patients = df_filtered.count()
        if total_patients == 0:
            continue

        # Summary statistics
        stats = df_filtered.agg(
            F.percentile_approx("time_to_treatment_days", 0.5).alias("median_days"),
            F.avg("time_to_treatment_days").alias("mean_days"),
            F.stddev("time_to_treatment_days").alias("stddev_days"),
            F.min("time_to_treatment_days").alias("min_days"),
            F.max("time_to_treatment_days").alias("max_days"),
            F.percentile_approx("time_to_treatment_days", 0.25).alias("p25_days"),
            F.percentile_approx("time_to_treatment_days", 0.75).alias("p75_days"),
        ).first()

        within_target_count = df_filtered.filter(F.col("within_target")).count()
        within_target_pct = round(100.0 * within_target_count / total_patients, 2)

        # Bucket-level aggregation
        df_bucket_agg = (
            df_filtered
            .groupBy("ttt_bucket", "bucket_order")
            .agg(
                F.count("*").alias("patient_count"),
            )
            .withColumn(
                "percentage",
                F.round(100.0 * F.col("patient_count") / F.lit(total_patients), 2),
            )
            .withColumn("snapshot_date", F.lit(str(SNAPSHOT_DATE)))
            .withColumn("stage_filter", F.lit(stage_label))
            .withColumn("total_patients_in_filter", F.lit(total_patients))
            .withColumn("median_days", F.lit(float(stats["median_days"])))
            .withColumn("mean_days", F.lit(float(stats["mean_days"])))
            .withColumn("stddev_days", F.lit(
                float(stats["stddev_days"]) if stats["stddev_days"] else 0.0
            ))
            .withColumn("min_days", F.lit(int(stats["min_days"])))
            .withColumn("max_days", F.lit(int(stats["max_days"])))
            .withColumn("p25_days", F.lit(float(stats["p25_days"])))
            .withColumn("p75_days", F.lit(float(stats["p75_days"])))
            .withColumn("within_target_pct", F.lit(within_target_pct))
            .withColumn("target_days", F.lit(TTT_TARGET_DAYS))
            .orderBy("bucket_order")
        )

        all_results.append(df_bucket_agg)

    # Union all stage filters
    df_result = all_results[0]
    for df_r in all_results[1:]:
        df_result = df_result.unionByName(df_r)

    df_result = (
        df_result
        .withColumn("snapshot_date", F.to_date(F.col("snapshot_date")))
        .withColumn("_updated_timestamp", F.current_timestamp())
        .drop("bucket_order")
    )

    logger.info(f"Time-to-treatment distribution: {df_result.count():,} rows")
    return df_result

# COMMAND ----------

df_ttt = build_time_to_treatment_distribution()

# Write to gold
TTT_TABLE = f"{GOLD_SCHEMA}.agg_time_to_treatment"

if not spark.catalog.tableExists(TTT_TABLE):
    (
        df_ttt.write
        .format("delta")
        .partitionBy("snapshot_date")
        .saveAsTable(TTT_TABLE)
    )
else:
    (
        df_ttt.write
        .format("delta")
        .mode("overwrite")
        .option("replaceWhere", f"snapshot_date = '{SNAPSHOT_DATE}'")
        .saveAsTable(TTT_TABLE)
    )

spark.sql(f"OPTIMIZE {TTT_TABLE}")
logger.info(f"Wrote time-to-treatment distribution to {TTT_TABLE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part 2: Treatment Patterns

# COMMAND ----------

def build_treatment_patterns() -> DataFrame:
    """
    Calculate treatment pattern distributions by line of therapy.

    For each line of therapy, counts the number of patients receiving
    each regimen category and calculates the percentage breakdown.
    Includes both regimen category (Chemo+IO, Chemo Only, etc.) and
    specific regimen name granularity.

    Returns
    -------
    DataFrame
        Treatment pattern aggregation records.
    """
    logger.info("Building treatment patterns")

    # Join treatments with patient staging
    df_first_dx = (
        df_diagnosis
        .groupBy("patient_id")
        .agg(
            F.first(
                F.when(F.col("sclc_stage") != "Unknown", F.col("sclc_stage")),
                ignorenulls=True,
            ).alias("sclc_stage"),
            F.min("diagnosis_date").alias("first_diagnosis_date"),
        )
    )

    df_tx_with_stage = (
        df_treatment
        .join(df_first_dx, on="patient_id", how="inner")
        .filter(F.col("first_diagnosis_date") <= F.lit(SNAPSHOT_DATE))
    )

    stage_filters = [None, "LS-SCLC", "ES-SCLC"]
    all_results = []

    for stage_filter in stage_filters:
        df_filtered = df_tx_with_stage
        stage_label = "all"

        if stage_filter:
            df_filtered = df_filtered.filter(F.col("sclc_stage") == stage_filter)
            stage_label = stage_filter

        # Aggregate by line of therapy and regimen category
        df_pattern = (
            df_filtered
            .groupBy("line_of_therapy", "line_of_therapy_label", "regimen_category")
            .agg(
                F.countDistinct("patient_id").alias("patient_count"),
                F.collect_set("regimen_name").alias("regimen_names_seen"),
            )
        )

        # Calculate percentage within each line of therapy
        window_line = Window.partitionBy("line_of_therapy")

        df_pattern = (
            df_pattern
            .withColumn(
                "total_patients_in_line",
                F.sum("patient_count").over(window_line),
            )
            .withColumn(
                "percentage",
                F.round(
                    100.0 * F.col("patient_count") / F.col("total_patients_in_line"),
                    2,
                ),
            )
            .withColumn("snapshot_date", F.lit(str(SNAPSHOT_DATE)))
            .withColumn("stage_filter", F.lit(stage_label))
            .withColumn(
                "regimen_names",
                F.concat_ws("; ", F.col("regimen_names_seen")),
            )
            .drop("regimen_names_seen")
        )

        # Also produce a top-regimen-name level detail
        df_regimen_detail = (
            df_filtered
            .groupBy(
                "line_of_therapy",
                "line_of_therapy_label",
                "regimen_category",
                "regimen_name",
            )
            .agg(F.countDistinct("patient_id").alias("regimen_patient_count"))
        )

        # Rank regimens within each line + category
        window_rank = Window.partitionBy(
            "line_of_therapy", "regimen_category"
        ).orderBy(F.col("regimen_patient_count").desc())

        df_top_regimens = (
            df_regimen_detail
            .withColumn("regimen_rank", F.row_number().over(window_rank))
            .filter(F.col("regimen_rank") <= 10)  # Top 10 regimens per category
            .withColumn("snapshot_date", F.lit(str(SNAPSHOT_DATE)))
            .withColumn("stage_filter", F.lit(stage_label))
        )

        all_results.append(df_pattern)

    # Union all results
    df_result = all_results[0]
    for df_r in all_results[1:]:
        df_result = df_result.unionByName(df_r, allowMissingColumns=True)

    df_result = (
        df_result
        .withColumn("snapshot_date", F.to_date(F.col("snapshot_date")))
        .withColumn("_updated_timestamp", F.current_timestamp())
    )

    logger.info(f"Treatment patterns: {df_result.count():,} rows")
    return df_result

# COMMAND ----------

df_patterns = build_treatment_patterns()

# Write to gold
PATTERNS_TABLE = f"{GOLD_SCHEMA}.agg_treatment_patterns"

if not spark.catalog.tableExists(PATTERNS_TABLE):
    (
        df_patterns.write
        .format("delta")
        .partitionBy("snapshot_date")
        .saveAsTable(PATTERNS_TABLE)
    )
else:
    (
        df_patterns.write
        .format("delta")
        .mode("overwrite")
        .option("replaceWhere", f"snapshot_date = '{SNAPSHOT_DATE}'")
        .saveAsTable(PATTERNS_TABLE)
    )

spark.sql(f"OPTIMIZE {PATTERNS_TABLE}")
logger.info(f"Wrote treatment patterns to {PATTERNS_TABLE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validation

# COMMAND ----------

# Time-to-Treatment summary
logger.info("Time-to-Treatment Summary:")
display(spark.sql(f"""
    SELECT
        stage_filter,
        ttt_bucket,
        patient_count,
        percentage,
        median_days,
        mean_days,
        within_target_pct
    FROM {TTT_TABLE}
    WHERE snapshot_date = '{SNAPSHOT_DATE}'
    ORDER BY stage_filter, patient_count DESC
"""))

# COMMAND ----------

# Treatment Patterns summary
logger.info("Treatment Patterns Summary:")
display(spark.sql(f"""
    SELECT
        stage_filter,
        line_of_therapy_label,
        regimen_category,
        patient_count,
        percentage
    FROM {PATTERNS_TABLE}
    WHERE snapshot_date = '{SNAPSHOT_DATE}'
    ORDER BY stage_filter, line_of_therapy, percentage DESC
"""))

# COMMAND ----------

logger.info("Treatment analytics processing complete")
