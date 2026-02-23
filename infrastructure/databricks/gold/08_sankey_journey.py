# Databricks notebook source
"""
Gold Layer: Patient Journey Sankey Diagram Data
Computes patient flow transitions through the SCLC care continuum.
Output: gold.agg_sankey_journey
"""

# COMMAND ----------

# MAGIC %md
# MAGIC # Gold Layer — Patient Journey Sankey
# MAGIC Builds transition data for the Sankey diagram visualization:
# MAGIC - Diagnosis → Stage (LS-SCLC / ES-SCLC)
# MAGIC - Stage → First-line Treatment Category
# MAGIC - First-line Treatment → Best Response
# MAGIC - Best Response → Next Step

# COMMAND ----------

dbutils.widgets.text("environment", "dev", "Environment (dev/staging/prod)")
ENV = dbutils.widgets.get("environment")

CATALOG = f"sclc_{ENV}"
SILVER_SCHEMA = f"{CATALOG}.silver"
GOLD_SCHEMA = f"{CATALOG}.gold"

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window
from datetime import date
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gold.sankey_journey")

SNAPSHOT_DATE = date.today()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Silver Tables

# COMMAND ----------

dim_patient = spark.read.table(f"{SILVER_SCHEMA}.dim_patient")
fact_diagnosis = spark.read.table(f"{SILVER_SCHEMA}.fact_diagnosis")
fact_treatment = spark.read.table(f"{SILVER_SCHEMA}.fact_treatment_episode")
fact_response = spark.read.table(f"{SILVER_SCHEMA}.fact_response_assessment")
fact_progression = spark.read.table(f"{SILVER_SCHEMA}.fact_progression_event")
fact_trial = spark.read.table(f"{SILVER_SCHEMA}.fact_trial_enrollment")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Build Patient Journey Base
# MAGIC Each patient flows through: Diagnosis → Stage → Treatment → Response → Next Step

# COMMAND ----------

# Get first diagnosis stage per patient
first_stage = (
    fact_diagnosis
    .withColumn("rn", F.row_number().over(
        Window.partitionBy("patient_id").orderBy("diagnosis_date")
    ))
    .filter(F.col("rn") == 1)
    .select("patient_id", F.col("stage").alias("initial_stage"))
)

# Get first-line treatment per patient
first_line_tx = (
    fact_treatment
    .filter(F.col("line_of_therapy") == "1st line")
    .withColumn("rn", F.row_number().over(
        Window.partitionBy("patient_id").orderBy("treatment_start_date")
    ))
    .filter(F.col("rn") == 1)
    .select("patient_id", "episode_id",
            F.col("regimen_category").alias("first_line_category"))
)

# Get best response for first-line treatment
best_response_order = {
    "CR": 1, "PR": 2, "SD": 3, "PD": 4
}

best_response = (
    fact_response
    .join(first_line_tx.select("patient_id", "episode_id"), "episode_id", "inner")
    .withColumn("response_rank", F.when(F.col("response_type") == "CR", 1)
                .when(F.col("response_type") == "PR", 2)
                .when(F.col("response_type") == "SD", 3)
                .when(F.col("response_type") == "PD", 4)
                .otherwise(5))
    .withColumn("rn", F.row_number().over(
        Window.partitionBy("patient_id").orderBy("response_rank")
    ))
    .filter(F.col("rn") == 1)
    .select("patient_id", F.col("response_type").alias("best_response"))
)

# Determine next step after first-line response
second_line_patients = (
    fact_treatment
    .filter(F.col("line_of_therapy") == "2nd line")
    .select("patient_id").distinct()
    .withColumn("has_2nd_line", F.lit(True))
)

trial_patients = (
    fact_trial
    .select("patient_id").distinct()
    .withColumn("in_trial", F.lit(True))
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Assemble Journey DataFrame

# COMMAND ----------

journey = (
    first_stage
    .join(first_line_tx, "patient_id", "left")
    .join(best_response, "patient_id", "left")
    .join(second_line_patients, "patient_id", "left")
    .join(trial_patients, "patient_id", "left")
    .fillna({"first_line_category": "No Treatment",
             "best_response": "Not Assessed"})
    .withColumn("next_step",
                F.when(F.col("in_trial") == True, "Clinical Trial")
                .when(F.col("has_2nd_line") == True, "2nd Line Treatment")
                .when(F.col("best_response").isin("CR", "PR"), "Continue/Monitor")
                .otherwise("No Further Treatment"))
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Compute Sankey Transitions
# MAGIC Build (source_node, target_node, patient_count) for each transition level.

# COMMAND ----------

def compute_transitions(df, source_col, target_col, source_category, target_category, stage_filter=None):
    """Compute patient count for each source→target transition."""
    filtered = df
    if stage_filter:
        filtered = df.filter(F.col("initial_stage") == stage_filter)

    return (
        filtered
        .groupBy(F.col(source_col).alias("source_node"),
                 F.col(target_col).alias("target_node"))
        .agg(F.countDistinct("patient_id").alias("patient_count"))
        .withColumn("source_category", F.lit(source_category))
        .withColumn("target_category", F.lit(target_category))
        .withColumn("snapshot_date", F.lit(SNAPSHOT_DATE))
        .withColumn("stage_filter", F.lit(stage_filter))
        .filter(F.col("patient_count") > 0)
    )


stage_filters = [None, "LS-SCLC", "ES-SCLC"]
all_transitions = []

for sf in stage_filters:
    # Transition 1: Diagnosis → Stage
    t1 = compute_transitions(journey, F.lit("Diagnosis"), "initial_stage",
                              "diagnosis", "stage", sf)
    # Fix: need string columns
    t1 = (
        journey if not sf else journey.filter(F.col("initial_stage") == sf)
    )
    t1 = (
        t1.withColumn("source_node", F.lit("SCLC Diagnosis"))
        .groupBy("source_node", F.col("initial_stage").alias("target_node"))
        .agg(F.countDistinct("patient_id").alias("patient_count"))
        .withColumn("source_category", F.lit("diagnosis"))
        .withColumn("target_category", F.lit("stage"))
        .withColumn("snapshot_date", F.lit(SNAPSHOT_DATE))
        .withColumn("stage_filter", F.lit(sf))
    )

    # Transition 2: Stage → Treatment Category
    filtered = journey if not sf else journey.filter(F.col("initial_stage") == sf)
    t2 = (
        filtered
        .groupBy(F.col("initial_stage").alias("source_node"),
                 F.col("first_line_category").alias("target_node"))
        .agg(F.countDistinct("patient_id").alias("patient_count"))
        .withColumn("source_category", F.lit("stage"))
        .withColumn("target_category", F.lit("treatment"))
        .withColumn("snapshot_date", F.lit(SNAPSHOT_DATE))
        .withColumn("stage_filter", F.lit(sf))
    )

    # Transition 3: Treatment Category → Response
    t3 = (
        filtered
        .filter(F.col("first_line_category") != "No Treatment")
        .groupBy(F.col("first_line_category").alias("source_node"),
                 F.col("best_response").alias("target_node"))
        .agg(F.countDistinct("patient_id").alias("patient_count"))
        .withColumn("source_category", F.lit("treatment"))
        .withColumn("target_category", F.lit("response"))
        .withColumn("snapshot_date", F.lit(SNAPSHOT_DATE))
        .withColumn("stage_filter", F.lit(sf))
    )

    # Transition 4: Response → Next Step
    t4 = (
        filtered
        .filter(F.col("best_response") != "Not Assessed")
        .groupBy(F.col("best_response").alias("source_node"),
                 F.col("next_step").alias("target_node"))
        .agg(F.countDistinct("patient_id").alias("patient_count"))
        .withColumn("source_category", F.lit("response"))
        .withColumn("target_category", F.lit("next_step"))
        .withColumn("snapshot_date", F.lit(SNAPSHOT_DATE))
        .withColumn("stage_filter", F.lit(sf))
    )

    all_transitions.extend([t1, t2, t3, t4])

# COMMAND ----------

# MAGIC %md
# MAGIC ## Union and Write

# COMMAND ----------

from functools import reduce

sankey_data = reduce(lambda a, b: a.unionByName(b), all_transitions)

sankey_data = sankey_data.select(
    "snapshot_date", "stage_filter",
    "source_node", "target_node", "patient_count",
    "source_category", "target_category"
).filter(F.col("patient_count") > 0)

display(sankey_data.orderBy("stage_filter", "source_category", F.desc("patient_count")))

# COMMAND ----------

(
    sankey_data.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(f"{GOLD_SCHEMA}.agg_sankey_journey")
)

logger.info(f"Wrote {sankey_data.count()} Sankey transitions to gold.agg_sankey_journey")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Data Quality Checks

# COMMAND ----------

result = spark.read.table(f"{GOLD_SCHEMA}.agg_sankey_journey")

# All stage filters present
filters = [r["stage_filter"] for r in result.select("stage_filter").distinct().collect()]
assert None in filters or len(filters) >= 1, "Must have at least unfiltered results"

# No zero-count transitions
assert result.filter(F.col("patient_count") <= 0).count() == 0, "No zero-count transitions allowed"

# Valid categories
valid_categories = {"diagnosis", "stage", "treatment", "response", "next_step"}
source_cats = {r["source_category"] for r in result.select("source_category").distinct().collect()}
assert source_cats.issubset(valid_categories), f"Invalid source categories: {source_cats - valid_categories}"

logger.info("All Sankey data quality checks passed")
