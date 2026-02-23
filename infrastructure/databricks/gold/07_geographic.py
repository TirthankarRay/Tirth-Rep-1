# Databricks notebook source
"""
Gold Layer: Geographic Metrics Aggregation
Aggregates patient metrics by US state for the geographic heatmap dashboard component.
Output: gold.agg_geographic_metrics
"""

# COMMAND ----------

# MAGIC %md
# MAGIC # Gold Layer — Geographic Metrics
# MAGIC Aggregates patient-level data by US state:
# MAGIC - Patient count per state
# MAGIC - Average time to treatment
# MAGIC - Immunotherapy adoption rate
# MAGIC - Clinical trial enrollment rate

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
logger = logging.getLogger("gold.geographic")

SNAPSHOT_DATE = date.today()
logger.info(f"Running geographic aggregation for snapshot: {SNAPSHOT_DATE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Silver Tables

# COMMAND ----------

dim_patient = spark.read.table(f"{SILVER_SCHEMA}.dim_patient")
fact_diagnosis = spark.read.table(f"{SILVER_SCHEMA}.fact_diagnosis")
fact_treatment = spark.read.table(f"{SILVER_SCHEMA}.fact_treatment_episode")
fact_biomarker = spark.read.table(f"{SILVER_SCHEMA}.fact_biomarker_test")
fact_trial = spark.read.table(f"{SILVER_SCHEMA}.fact_trial_enrollment")

# COMMAND ----------

# MAGIC %md
# MAGIC ## State Name Lookup

# COMMAND ----------

STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}

state_names_df = spark.createDataFrame(
    [(k, v) for k, v in STATE_NAMES.items()],
    ["state_code", "state_name"]
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Calculate Geographic Metrics

# COMMAND ----------

# Patient count per state
patients_by_state = (
    dim_patient
    .filter(F.col("state").isNotNull())
    .groupBy("state")
    .agg(F.countDistinct("patient_id").alias("patient_count"))
)

# Average time to treatment per state
first_diagnosis = (
    fact_diagnosis
    .groupBy("patient_id")
    .agg(F.min("diagnosis_date").alias("first_diagnosis_date"))
)

first_treatment = (
    fact_treatment
    .groupBy("patient_id")
    .agg(F.min("treatment_start_date").alias("first_treatment_date"))
)

ttt_by_patient = (
    first_diagnosis
    .join(first_treatment, "patient_id", "inner")
    .withColumn("days_to_treatment",
                F.datediff("first_treatment_date", "first_diagnosis_date"))
    .filter(F.col("days_to_treatment") >= 0)
)

ttt_by_state = (
    ttt_by_patient
    .join(dim_patient.select("patient_id", "state"), "patient_id")
    .groupBy("state")
    .agg(F.round(F.avg("days_to_treatment"), 1).alias("avg_time_to_treatment"))
)

# Immunotherapy rate per state (ES-SCLC patients with IO)
es_patients = (
    fact_diagnosis
    .filter(F.col("stage") == "ES-SCLC")
    .select("patient_id").distinct()
)

io_patients = (
    fact_treatment
    .filter(F.col("includes_immunotherapy") == True)
    .select("patient_id").distinct()
)

io_by_state = (
    es_patients
    .join(dim_patient.select("patient_id", "state"), "patient_id")
    .groupBy("state")
    .agg(F.countDistinct("patient_id").alias("es_total"))
    .join(
        es_patients
        .join(io_patients, "patient_id", "inner")
        .join(dim_patient.select("patient_id", "state"), "patient_id")
        .groupBy("state")
        .agg(F.countDistinct("patient_id").alias("io_count")),
        "state", "left"
    )
    .fillna(0, subset=["io_count"])
    .withColumn("immunotherapy_rate",
                F.round(F.col("io_count") / F.col("es_total") * 100, 1))
    .select("state", "immunotherapy_rate")
)

# Trial enrollment rate per state
trial_patients = fact_trial.select("patient_id").distinct()

trial_by_state = (
    dim_patient
    .filter(F.col("state").isNotNull())
    .groupBy("state")
    .agg(F.countDistinct("patient_id").alias("state_total"))
    .join(
        trial_patients
        .join(dim_patient.select("patient_id", "state"), "patient_id")
        .groupBy("state")
        .agg(F.countDistinct("patient_id").alias("trial_count")),
        "state", "left"
    )
    .fillna(0, subset=["trial_count"])
    .withColumn("trial_enrollment_rate",
                F.round(F.col("trial_count") / F.col("state_total") * 100, 1))
    .select("state", "trial_enrollment_rate")
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Join All Metrics

# COMMAND ----------

agg_geographic = (
    patients_by_state
    .join(state_names_df, patients_by_state["state"] == state_names_df["state_code"], "left")
    .join(ttt_by_state, "state", "left")
    .join(io_by_state, "state", "left")
    .join(trial_by_state, "state", "left")
    .withColumn("snapshot_date", F.lit(SNAPSHOT_DATE))
    .select(
        "snapshot_date",
        "state",
        "state_name",
        "patient_count",
        "avg_time_to_treatment",
        "immunotherapy_rate",
        "trial_enrollment_rate"
    )
    .fillna(0.0)
    .orderBy(F.desc("patient_count"))
)

display(agg_geographic)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Write to Gold Table

# COMMAND ----------

(
    agg_geographic.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .option("replaceWhere", f"snapshot_date = '{SNAPSHOT_DATE}'")
    .saveAsTable(f"{GOLD_SCHEMA}.agg_geographic_metrics")
)

logger.info(f"Wrote {agg_geographic.count()} state records to gold.agg_geographic_metrics")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Data Quality Checks

# COMMAND ----------

result = spark.read.table(f"{GOLD_SCHEMA}.agg_geographic_metrics").filter(
    F.col("snapshot_date") == F.lit(SNAPSHOT_DATE)
)

assert result.count() > 0, "No geographic records produced"
assert result.filter(F.col("patient_count") <= 0).count() == 0, "States with zero patients should not exist"
assert result.filter(F.col("state").isNull()).count() == 0, "State code must not be null"

logger.info("All data quality checks passed")
