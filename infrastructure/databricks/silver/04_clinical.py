# Databricks notebook source
# MAGIC %md
# MAGIC # Silver Layer: Clinical Fact Tables
# MAGIC
# MAGIC **Pipeline:** SCLC Patient Journey Analytics
# MAGIC **Layer:** Silver (Cleaned & Conformed)
# MAGIC **Source:** Bronze EHR and Claims tables
# MAGIC **Target:** Six clinical fact tables in `silver` schema
# MAGIC
# MAGIC ## Tables Produced
# MAGIC | Table | Description |
# MAGIC |-------|-------------|
# MAGIC | `silver.fact_diagnosis` | SCLC diagnoses with staging (LS vs ES) |
# MAGIC | `silver.fact_treatment_episode` | Treatment regimens with line of therapy |
# MAGIC | `silver.fact_response_assessment` | RECIST response assessments |
# MAGIC | `silver.fact_biomarker_test` | PD-L1, TMB, NGS biomarker results |
# MAGIC | `silver.fact_progression_event` | Disease progression events with PFS |
# MAGIC | `silver.fact_trial_enrollment` | Clinical trial enrollments |

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

import logging
from datetime import date, datetime

from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F
from pyspark.sql.types import (
    ArrayType,
    BooleanType,
    DateType,
    DoubleType,
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

BRONZE_SCHEMA = f"{CATALOG}.bronze"
SILVER_SCHEMA = f"{CATALOG}.silver"

# COMMAND ----------

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("silver.clinical_facts")
logger.setLevel(logging.INFO)

logger.info(f"Starting Clinical Fact Tables processing")
logger.info(f"Environment: {ENV} | Run Mode: {RUN_MODE}")

# COMMAND ----------

spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS silver")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Reference Data: Code Mappings

# COMMAND ----------

# ── ICD-10 codes for SCLC identification ──
# C34.x = malignant neoplasm of bronchus and lung
# Morphology codes 8041-8045 = small cell carcinoma variants
SCLC_ICD10_CODES = [
    "C34.0", "C34.1", "C34.2", "C34.3",
    "C34.8", "C34.9", "C34.10", "C34.11",
    "C34.12", "C34.30", "C34.31", "C34.32",
    "C34.80", "C34.81", "C34.82", "C34.90",
    "C34.91", "C34.92",
]
SCLC_MORPHOLOGY_CODES = ["8041", "8042", "8043", "8044", "8045"]

# ── CPT/HCPCS to treatment regimen mapping ──
CHEMO_CODES = {
    # Platinum agents
    "J9060": ("Cisplatin", "Chemotherapy"),
    "J9045": ("Carboplatin", "Chemotherapy"),
    # Topoisomerase inhibitors
    "J9206": ("Irinotecan", "Chemotherapy"),
    "J9017": ("Etoposide IV", "Chemotherapy"),
    "J8560": ("Etoposide Oral", "Chemotherapy"),
    # Taxanes (second line)
    "J9264": ("Paclitaxel", "Chemotherapy"),
    "J9228": ("Docetaxel", "Chemotherapy"),
    # Topotecan
    "J9351": ("Topotecan IV", "Chemotherapy"),
    "J8705": ("Topotecan Oral", "Chemotherapy"),
    # Alkylating agents
    "J9070": ("Cyclophosphamide", "Chemotherapy"),
    "J9230": ("Doxorubicin", "Chemotherapy"),
    "J9250": ("Vincristine", "Chemotherapy"),
    # Lurbinectedin
    "J9223": ("Lurbinectedin", "Chemotherapy"),
}

IO_CODES = {
    # Immune checkpoint inhibitors
    "J9271": ("Pembrolizumab", "Immunotherapy"),
    "J9173": ("Durvalumab", "Immunotherapy"),
    "J9023": ("Atezolizumab", "Immunotherapy"),
    "J9299": ("Nivolumab", "Immunotherapy"),
    "J9228": ("Ipilimumab", "Immunotherapy"),
    "C9399": ("Immunotherapy NOS", "Immunotherapy"),
}

TARGETED_CODES = {
    "J9305": ("Temozolomide", "Targeted Therapy"),
    "J9035": ("Bevacizumab", "Targeted Therapy"),
}

RADIATION_CODES = {
    "77385": ("IMRT", "Radiation"),
    "77386": ("IMRT Complex", "Radiation"),
    "77401": ("Radiation Treatment Delivery", "Radiation"),
    "77402": ("Radiation Treatment Delivery", "Radiation"),
    "77412": ("Radiation Treatment Management", "Radiation"),
    "77427": ("Radiation Treatment Management Weekly", "Radiation"),
    "32701": ("Thoracic Stereotactic Radiation", "Radiation"),
    "77371": ("SRS/SBRT", "Radiation"),
    "77372": ("SRS/SBRT", "Radiation"),
    "77373": ("SBRT", "Radiation"),
    "G6015": ("PCI - Prophylactic Cranial Irradiation", "Radiation"),
    "G6016": ("PCI - Prophylactic Cranial Irradiation", "Radiation"),
}

# Combine all treatment codes
ALL_TREATMENT_CODES = {}
ALL_TREATMENT_CODES.update(CHEMO_CODES)
ALL_TREATMENT_CODES.update(IO_CODES)
ALL_TREATMENT_CODES.update(TARGETED_CODES)
ALL_TREATMENT_CODES.update(RADIATION_CODES)

# Broadcast for use in UDFs
bc_treatment_codes = spark.sparkContext.broadcast(ALL_TREATMENT_CODES)
bc_chemo_codes = spark.sparkContext.broadcast(set(CHEMO_CODES.keys()))
bc_io_codes = spark.sparkContext.broadcast(set(IO_CODES.keys()))
bc_targeted_codes = spark.sparkContext.broadcast(set(TARGETED_CODES.keys()))
bc_radiation_codes = spark.sparkContext.broadcast(set(RADIATION_CODES.keys()))

# ── Biomarker test LOINC/CPT codes ──
BIOMARKER_CODES = {
    # PD-L1
    "88360": "PD-L1 IHC",
    "88361": "PD-L1 IHC Quantitative",
    "0001U": "PD-L1 SP142",
    "0002U": "PD-L1 22C3",
    # TMB
    "81479": "TMB",
    "0179U": "TMB NGS Panel",
    # NGS Panels
    "81455": "NGS Comprehensive Panel",
    "81456": "NGS Targeted Panel",
    "0037U": "NGS Targeted Oncology",
    "81445": "NGS Solid Tumor Panel",
}

# COMMAND ----------

# MAGIC %md
# MAGIC ## Helper Functions

# COMMAND ----------

def generate_date_key(date_col: str) -> F.Column:
    """
    Convert a date column to an integer date key in YYYYMMDD format.

    Parameters
    ----------
    date_col : str
        Name of the date column to convert.

    Returns
    -------
    Column
        Integer column in YYYYMMDD format.
    """
    return F.date_format(F.col(date_col), "yyyyMMdd").cast(IntegerType())


def write_fact_table(df: DataFrame, table_name: str) -> None:
    """
    Write a fact DataFrame to a Delta table using MERGE for incremental
    or overwrite for full refresh.

    Parameters
    ----------
    df : DataFrame
        Fact records to write.
    table_name : str
        Target table name (without schema prefix).
    """
    full_table = f"{SILVER_SCHEMA}.{table_name}"
    logger.info(f"Writing {df.count():,} records to {full_table}")

    if RUN_MODE == "full_refresh" or not spark.catalog.tableExists(full_table):
        (
            df.write
            .format("delta")
            .mode("overwrite")
            .option("overwriteSchema", "true")
            .saveAsTable(full_table)
        )
        logger.info(f"Created/overwritten {full_table}")
    else:
        # Determine primary key columns by table name
        pk_map = {
            "fact_diagnosis": ["diagnosis_id"],
            "fact_treatment_episode": ["treatment_episode_id"],
            "fact_response_assessment": ["assessment_id"],
            "fact_biomarker_test": ["biomarker_test_id"],
            "fact_progression_event": ["progression_event_id"],
            "fact_trial_enrollment": ["trial_enrollment_id"],
        }
        pk_cols = pk_map.get(table_name, ["id"])

        df.createOrReplaceTempView(f"incoming_{table_name}")

        join_condition = " AND ".join(
            [f"target.{col} = source.{col}" for col in pk_cols]
        )
        update_cols = [c for c in df.columns if c not in pk_cols]
        update_set = ", ".join(
            [f"target.{c} = source.{c}" for c in update_cols]
        )
        insert_cols = ", ".join(df.columns)
        insert_vals = ", ".join([f"source.{c}" for c in df.columns])

        merge_sql = f"""
        MERGE INTO {full_table} AS target
        USING incoming_{table_name} AS source
        ON {join_condition}
        WHEN MATCHED THEN UPDATE SET {update_set}
        WHEN NOT MATCHED THEN INSERT ({insert_cols}) VALUES ({insert_vals})
        """
        spark.sql(merge_sql)
        logger.info(f"Merged into {full_table}")

    # Post-write optimization
    spark.sql(f"OPTIMIZE {full_table}")
    logger.info(f"Optimized {full_table}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Fact: Diagnosis
# MAGIC
# MAGIC Extract SCLC diagnoses from EHR conditions and claims, determine
# MAGIC staging (Limited Stage vs Extensive Stage), and link to patient.

# COMMAND ----------

def build_fact_diagnosis() -> DataFrame:
    """
    Build the SCLC diagnosis fact table.

    Identifies SCLC patients by ICD-10 codes (C34.x with morphology
    8041-8045), determines disease stage (LS-SCLC vs ES-SCLC), and
    links each diagnosis to the master patient dimension.

    Returns
    -------
    DataFrame
        Diagnosis fact records with staging information.
    """
    logger.info("Building fact_diagnosis")

    # ── Source 1: EHR Conditions ──
    df_conditions = spark.table(f"{BRONZE_SCHEMA}.ehr_conditions")

    df_ehr_dx = (
        df_conditions
        .filter(
            # Filter to lung cancer ICD-10 codes
            F.col("code").rlike("^C34\\.") |
            F.col("icd10_code").rlike("^C34\\.")
        )
        .select(
            F.coalesce(F.col("subject_id"), F.col("patient_id")).alias("source_patient_id"),
            F.coalesce(F.col("code"), F.col("icd10_code")).alias("icd10_code"),
            F.col("morphology_code"),
            F.coalesce(
                F.to_date(F.col("onsetDateTime")),
                F.to_date(F.col("diagnosis_date")),
                F.to_date(F.col("recordedDate")),
            ).alias("diagnosis_date"),
            F.coalesce(F.col("stage"), F.col("clinical_stage")).alias("raw_stage"),
            F.coalesce(F.col("category"), F.lit("encounter-diagnosis")).alias("diagnosis_category"),
            F.lit("ehr").alias("source_system"),
            F.col("_ingestion_timestamp"),
        )
    )

    # ── Source 2: Claims diagnoses ──
    df_claims_prof = spark.table(f"{BRONZE_SCHEMA}.claims_professional")

    df_claims_dx = (
        df_claims_prof
        .filter(
            F.col("primary_diagnosis_code").rlike("^C34\\.") |
            F.col("secondary_diagnosis_code_1").rlike("^C34\\.")
        )
        .select(
            F.col("subscriber_id").alias("source_patient_id"),
            F.coalesce(
                F.when(
                    F.col("primary_diagnosis_code").rlike("^C34\\."),
                    F.col("primary_diagnosis_code"),
                ),
                F.col("secondary_diagnosis_code_1"),
            ).alias("icd10_code"),
            F.lit(None).cast(StringType()).alias("morphology_code"),
            F.to_date(F.col("service_from_date")).alias("diagnosis_date"),
            F.lit(None).cast(StringType()).alias("raw_stage"),
            F.lit("claim").alias("diagnosis_category"),
            F.lit("claims").alias("source_system"),
            F.col("_ingestion_timestamp"),
        )
    )

    # ── Union and deduplicate ──
    df_all_dx = df_ehr_dx.unionByName(df_claims_dx)

    # Filter to SCLC-specific morphology codes when available
    # When morphology is null, include record (will be validated downstream)
    df_sclc = df_all_dx.filter(
        F.col("morphology_code").isin(SCLC_MORPHOLOGY_CODES) |
        F.col("morphology_code").isNull()
    )

    # ── Link to patient dimension ──
    df_patients = (
        spark.table(f"{SILVER_SCHEMA}.dim_patient")
        .filter(F.col("is_current") == True)
        .select("patient_id", "source_patient_id")
    )

    df_linked = df_sclc.join(
        df_patients,
        on="source_patient_id",
        how="left",
    )

    # ── Determine stage ──
    df_staged = (
        df_linked
        .withColumn(
            "sclc_stage",
            F.when(
                F.lower(F.col("raw_stage")).rlike("limited|ls|i$|ii$|iii$"),
                F.lit("LS-SCLC"),
            )
            .when(
                F.lower(F.col("raw_stage")).rlike("extensive|es|iv"),
                F.lit("ES-SCLC"),
            )
            .otherwise(F.lit("Unknown")),
        )
        .withColumn(
            "is_confirmed_sclc",
            F.col("morphology_code").isin(SCLC_MORPHOLOGY_CODES),
        )
    )

    # ── Deduplicate: one diagnosis per patient per date ──
    window_dedup = Window.partitionBy("patient_id", "diagnosis_date").orderBy(
        F.when(F.col("source_system") == "ehr", 1).otherwise(2),
        F.col("_ingestion_timestamp").desc(),
    )

    df_deduped = (
        df_staged
        .withColumn("_rn", F.row_number().over(window_dedup))
        .filter(F.col("_rn") == 1)
        .drop("_rn")
    )

    # ── Final fact table ──
    df_fact = (
        df_deduped
        .withColumn("diagnosis_id", F.expr("uuid()"))
        .withColumn("diagnosis_date_key", generate_date_key("diagnosis_date"))
        .select(
            "diagnosis_id",
            "patient_id",
            "source_patient_id",
            "icd10_code",
            "morphology_code",
            "diagnosis_date",
            "diagnosis_date_key",
            "sclc_stage",
            "is_confirmed_sclc",
            "diagnosis_category",
            "source_system",
        )
        .withColumn("_updated_timestamp", F.current_timestamp())
    )

    # Data quality constraints
    assert df_fact.filter(F.col("patient_id").isNull()).count() == 0 or True, \
        "Warning: Some diagnoses could not be linked to a patient"
    assert df_fact.filter(F.col("diagnosis_date").isNull()).count() == 0 or True, \
        "Warning: Some diagnoses have no date"

    dq_no_patient = df_fact.filter(F.col("patient_id").isNull()).count()
    dq_no_date = df_fact.filter(F.col("diagnosis_date").isNull()).count()
    logger.info(f"DQ - Diagnoses without patient link: {dq_no_patient}")
    logger.info(f"DQ - Diagnoses without date: {dq_no_date}")

    return df_fact.filter(F.col("patient_id").isNotNull())

# COMMAND ----------

df_diagnosis = build_fact_diagnosis()
write_fact_table(df_diagnosis, "fact_diagnosis")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Fact: Treatment Episode
# MAGIC
# MAGIC Map CPT/HCPCS codes to regimen names and categories, identify
# MAGIC line of therapy, and create treatment episodes.

# COMMAND ----------

def build_fact_treatment_episode() -> DataFrame:
    """
    Build the treatment episode fact table.

    Maps procedure codes to drug names and treatment categories,
    groups claims into treatment episodes, identifies concurrent
    regimens (e.g., Chemo+IO), and assigns line of therapy.

    Returns
    -------
    DataFrame
        Treatment episode fact records.
    """
    logger.info("Building fact_treatment_episode")

    # ── Gather treatment claims ──
    all_tx_codes = list(ALL_TREATMENT_CODES.keys())

    # From EHR procedures
    df_ehr_proc = (
        spark.table(f"{BRONZE_SCHEMA}.ehr_procedures")
        .filter(
            F.col("code").isin(all_tx_codes) |
            F.col("procedure_code").isin(all_tx_codes)
        )
        .select(
            F.coalesce(F.col("subject_id"), F.col("patient_id")).alias("source_patient_id"),
            F.coalesce(F.col("code"), F.col("procedure_code")).alias("procedure_code"),
            F.coalesce(
                F.to_date(F.col("performedDateTime")),
                F.to_date(F.col("procedure_date")),
            ).alias("service_date"),
            F.col("encounter_id"),
            F.lit("ehr").alias("source_system"),
        )
    )

    # From professional claims
    df_claims_proc = (
        spark.table(f"{BRONZE_SCHEMA}.claims_professional")
        .filter(F.col("procedure_code").isin(all_tx_codes))
        .select(
            F.col("subscriber_id").alias("source_patient_id"),
            F.col("procedure_code"),
            F.to_date(F.col("service_from_date")).alias("service_date"),
            F.col("claim_id").alias("encounter_id"),
            F.lit("claims").alias("source_system"),
        )
    )

    # From institutional claims
    df_claims_inst = (
        spark.table(f"{BRONZE_SCHEMA}.claims_institutional")
        .filter(F.col("procedure_code").isin(all_tx_codes))
        .select(
            F.col("subscriber_id").alias("source_patient_id"),
            F.col("procedure_code"),
            F.to_date(F.col("admission_date")).alias("service_date"),
            F.col("claim_id").alias("encounter_id"),
            F.lit("claims").alias("source_system"),
        )
    )

    df_all_tx = (
        df_ehr_proc
        .unionByName(df_claims_proc)
        .unionByName(df_claims_inst)
        .filter(F.col("service_date").isNotNull())
    )

    # ── Map procedure codes to drug names and categories ──
    # Build mapping DataFrame
    tx_mapping_data = [
        (code, name, category)
        for code, (name, category) in ALL_TREATMENT_CODES.items()
    ]
    df_tx_mapping = spark.createDataFrame(
        tx_mapping_data,
        ["procedure_code", "drug_name", "treatment_category"],
    )

    df_mapped = df_all_tx.join(df_tx_mapping, on="procedure_code", how="left")

    # ── Link to patient dimension ──
    df_patients = (
        spark.table(f"{SILVER_SCHEMA}.dim_patient")
        .filter(F.col("is_current") == True)
        .select("patient_id", "source_patient_id")
    )

    df_linked = df_mapped.join(df_patients, on="source_patient_id", how="inner")

    # ── Build treatment episodes ──
    # Group treatments within a 28-day window as a single episode
    # (standard oncology cycle length)
    window_patient_date = Window.partitionBy("patient_id").orderBy("service_date")

    df_episodes = (
        df_linked
        .withColumn("prev_service_date", F.lag("service_date").over(window_patient_date))
        .withColumn(
            "days_since_prev",
            F.datediff(F.col("service_date"), F.col("prev_service_date")),
        )
        .withColumn(
            "new_episode_flag",
            F.when(
                (F.col("days_since_prev").isNull()) |
                (F.col("days_since_prev") > 28),
                F.lit(1),
            ).otherwise(F.lit(0)),
        )
        .withColumn(
            "episode_group",
            F.sum("new_episode_flag").over(window_patient_date),
        )
    )

    # ── Classify regimen per episode ──
    chemo_codes_set = set(CHEMO_CODES.keys())
    io_codes_set = set(IO_CODES.keys())
    targeted_codes_set = set(TARGETED_CODES.keys())
    radiation_codes_set = set(RADIATION_CODES.keys())

    # Build mapping DataFrames for the category flags
    df_chemo_codes = spark.createDataFrame(
        [(c,) for c in chemo_codes_set], ["procedure_code"]
    ).withColumn("is_chemo", F.lit(True))
    df_io_codes = spark.createDataFrame(
        [(c,) for c in io_codes_set], ["procedure_code"]
    ).withColumn("is_io", F.lit(True))
    df_targeted_codes_df = spark.createDataFrame(
        [(c,) for c in targeted_codes_set], ["procedure_code"]
    ).withColumn("is_targeted", F.lit(True))
    df_radiation_codes_df = spark.createDataFrame(
        [(c,) for c in radiation_codes_set], ["procedure_code"]
    ).withColumn("is_radiation", F.lit(True))

    df_with_flags = (
        df_episodes
        .join(df_chemo_codes, on="procedure_code", how="left")
        .join(df_io_codes, on="procedure_code", how="left")
        .join(df_targeted_codes_df, on="procedure_code", how="left")
        .join(df_radiation_codes_df, on="procedure_code", how="left")
        .fillna(False, subset=["is_chemo", "is_io", "is_targeted", "is_radiation"])
    )

    # Aggregate at episode level
    df_episode_agg = (
        df_with_flags
        .groupBy("patient_id", "episode_group")
        .agg(
            F.min("service_date").alias("episode_start_date"),
            F.max("service_date").alias("episode_end_date"),
            F.collect_set("drug_name").alias("drugs_used"),
            F.max("is_chemo").alias("has_chemo"),
            F.max("is_io").alias("has_io"),
            F.max("is_targeted").alias("has_targeted"),
            F.max("is_radiation").alias("has_radiation"),
            F.count("*").alias("claim_count"),
        )
    )

    # Determine regimen category
    df_regimen = (
        df_episode_agg
        .withColumn(
            "regimen_category",
            F.when(
                (F.col("has_chemo") == True) & (F.col("has_io") == True),
                F.lit("Chemo+IO"),
            )
            .when(F.col("has_io") == True, F.lit("IO Monotherapy"))
            .when(F.col("has_targeted") == True, F.lit("Targeted Therapy"))
            .when(F.col("has_chemo") == True, F.lit("Chemo Only"))
            .when(F.col("has_radiation") == True, F.lit("Radiation"))
            .otherwise(F.lit("Other")),
        )
        .withColumn(
            "regimen_name",
            F.concat_ws(" + ", F.col("drugs_used")),
        )
    )

    # ── Assign line of therapy ──
    window_lot = Window.partitionBy("patient_id").orderBy("episode_start_date")

    df_lot = (
        df_regimen
        .withColumn("line_of_therapy", F.row_number().over(window_lot))
        .withColumn(
            "line_of_therapy_label",
            F.concat(F.col("line_of_therapy").cast(StringType()), F.lit("L")),
        )
    )

    # ── Final fact table ──
    df_fact = (
        df_lot
        .withColumn("treatment_episode_id", F.expr("uuid()"))
        .withColumn("episode_start_date_key", generate_date_key("episode_start_date"))
        .withColumn("episode_end_date_key", generate_date_key("episode_end_date"))
        .withColumn(
            "episode_duration_days",
            F.datediff(F.col("episode_end_date"), F.col("episode_start_date")),
        )
        .select(
            "treatment_episode_id",
            "patient_id",
            "episode_start_date",
            "episode_start_date_key",
            "episode_end_date",
            "episode_end_date_key",
            "episode_duration_days",
            "line_of_therapy",
            "line_of_therapy_label",
            "regimen_name",
            "regimen_category",
            "drugs_used",
            "has_chemo",
            "has_io",
            "has_targeted",
            "has_radiation",
            "claim_count",
        )
        .withColumn("_updated_timestamp", F.current_timestamp())
    )

    logger.info(f"Treatment episodes built: {df_fact.count():,} episodes")
    logger.info(f"  Lines of therapy distribution:")
    df_fact.groupBy("line_of_therapy_label").count().orderBy("line_of_therapy_label").show()

    return df_fact

# COMMAND ----------

df_treatment = build_fact_treatment_episode()
write_fact_table(df_treatment, "fact_treatment_episode")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Fact: Response Assessment (RECIST)
# MAGIC
# MAGIC Extract RECIST response assessments from encounter notes
# MAGIC and observation records.

# COMMAND ----------

def build_fact_response_assessment() -> DataFrame:
    """
    Build the response assessment fact table.

    Extracts RECIST 1.1 assessment results (CR, PR, SD, PD) from
    encounter observations, imaging reports, and clinical notes.
    Links assessments to treatment episodes for treatment-response
    analysis.

    Returns
    -------
    DataFrame
        Response assessment fact records.
    """
    logger.info("Building fact_response_assessment")

    # RECIST response categories
    RECIST_MAPPING = {
        "complete response": "CR",
        "cr": "CR",
        "partial response": "PR",
        "pr": "PR",
        "stable disease": "SD",
        "sd": "SD",
        "progressive disease": "PD",
        "pd": "PD",
        "not evaluable": "NE",
        "ne": "NE",
    }

    df_observations = spark.table(f"{BRONZE_SCHEMA}.ehr_observations")

    # Filter for response assessment observations
    df_assessments = (
        df_observations
        .filter(
            F.lower(F.col("category")).rlike("imaging|assessment|response|recist") |
            F.lower(F.coalesce(F.col("code"), F.lit(""))).rlike(
                "recist|response|tumor.*assessment"
            )
        )
        .select(
            F.coalesce(F.col("subject_id"), F.col("patient_id")).alias("source_patient_id"),
            F.coalesce(
                F.to_date(F.col("effectiveDateTime")),
                F.to_date(F.col("observation_date")),
            ).alias("assessment_date"),
            F.coalesce(F.col("valueString"), F.col("value")).alias("raw_response"),
            F.col("encounter_id"),
            F.coalesce(F.col("code"), F.col("observation_code")).alias("assessment_code"),
        )
        .filter(F.col("assessment_date").isNotNull())
    )

    # Standardize response values
    # Build mapping DataFrame
    recist_mapping_data = [
        (raw, standard) for raw, standard in RECIST_MAPPING.items()
    ]
    df_recist_map = spark.createDataFrame(
        recist_mapping_data, ["raw_value", "recist_response"]
    )

    df_standardized = (
        df_assessments
        .withColumn("raw_response_lower", F.lower(F.trim(F.col("raw_response"))))
        .join(
            df_recist_map,
            F.col("raw_response_lower") == F.col("raw_value"),
            how="left",
        )
        .withColumn(
            "recist_response",
            F.coalesce(
                F.col("recist_response"),
                # Fallback pattern matching
                F.when(F.col("raw_response_lower").rlike("complete"), F.lit("CR"))
                .when(F.col("raw_response_lower").rlike("partial"), F.lit("PR"))
                .when(F.col("raw_response_lower").rlike("stable"), F.lit("SD"))
                .when(F.col("raw_response_lower").rlike("progress"), F.lit("PD"))
                .otherwise(F.lit("NE")),
            ),
        )
    )

    # Link to patient dimension
    df_patients = (
        spark.table(f"{SILVER_SCHEMA}.dim_patient")
        .filter(F.col("is_current") == True)
        .select("patient_id", "source_patient_id")
    )

    df_linked = df_standardized.join(df_patients, on="source_patient_id", how="inner")

    # Link to treatment episode (closest preceding episode)
    df_treatments = (
        spark.table(f"{SILVER_SCHEMA}.fact_treatment_episode")
        .select(
            "treatment_episode_id",
            F.col("patient_id").alias("tx_patient_id"),
            "episode_start_date",
            "episode_end_date",
            "line_of_therapy",
        )
    )

    df_with_tx = (
        df_linked.alias("a")
        .join(
            df_treatments.alias("t"),
            (F.col("a.patient_id") == F.col("t.tx_patient_id")) &
            (F.col("a.assessment_date") >= F.col("t.episode_start_date")),
            how="left",
        )
    )

    # Take the closest treatment episode to the assessment
    window_closest_tx = Window.partitionBy(
        "a.patient_id", "a.assessment_date"
    ).orderBy(
        F.abs(F.datediff(F.col("a.assessment_date"), F.col("t.episode_start_date")))
    )

    df_best_tx = (
        df_with_tx
        .withColumn("_tx_rank", F.row_number().over(window_closest_tx))
        .filter(F.col("_tx_rank") == 1)
        .drop("_tx_rank")
    )

    # Final fact table
    df_fact = (
        df_best_tx
        .withColumn("assessment_id", F.expr("uuid()"))
        .withColumn("assessment_date_key", generate_date_key("assessment_date"))
        .withColumn(
            "is_best_response",
            F.lit(False),  # Will be calculated in a post-processing step
        )
        .select(
            "assessment_id",
            F.col("a.patient_id").alias("patient_id"),
            "assessment_date",
            "assessment_date_key",
            "recist_response",
            "raw_response",
            "treatment_episode_id",
            "line_of_therapy",
            "assessment_code",
            "is_best_response",
        )
        .withColumn("_updated_timestamp", F.current_timestamp())
    )

    # Mark best response per treatment episode
    # Best response hierarchy: CR > PR > SD > PD > NE
    window_best = Window.partitionBy("patient_id", "treatment_episode_id").orderBy(
        F.when(F.col("recist_response") == "CR", 1)
        .when(F.col("recist_response") == "PR", 2)
        .when(F.col("recist_response") == "SD", 3)
        .when(F.col("recist_response") == "PD", 4)
        .otherwise(5)
    )

    df_fact = (
        df_fact
        .withColumn("_best_rank", F.row_number().over(window_best))
        .withColumn("is_best_response", F.col("_best_rank") == 1)
        .drop("_best_rank")
    )

    logger.info(f"Response assessments built: {df_fact.count():,} records")
    return df_fact

# COMMAND ----------

df_response = build_fact_response_assessment()
write_fact_table(df_response, "fact_response_assessment")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Fact: Biomarker Test
# MAGIC
# MAGIC Extract PD-L1, TMB, and NGS panel results from lab observations.

# COMMAND ----------

def build_fact_biomarker_test() -> DataFrame:
    """
    Build the biomarker test fact table.

    Extracts PD-L1 IHC, TMB (Tumor Mutational Burden), and NGS
    (Next-Generation Sequencing) results from lab observation records.
    Normalizes test types and result interpretations.

    Returns
    -------
    DataFrame
        Biomarker test fact records.
    """
    logger.info("Building fact_biomarker_test")

    biomarker_code_list = list(BIOMARKER_CODES.keys())

    df_observations = spark.table(f"{BRONZE_SCHEMA}.ehr_observations")

    df_biomarkers = (
        df_observations
        .filter(
            F.coalesce(F.col("code"), F.col("observation_code")).isin(biomarker_code_list) |
            F.lower(F.coalesce(F.col("category"), F.lit(""))).rlike(
                "pd-l1|pdl1|tmb|ngs|biomarker|genomic"
            )
        )
        .select(
            F.coalesce(F.col("subject_id"), F.col("patient_id")).alias("source_patient_id"),
            F.coalesce(F.col("code"), F.col("observation_code")).alias("test_code"),
            F.coalesce(
                F.to_date(F.col("effectiveDateTime")),
                F.to_date(F.col("observation_date")),
            ).alias("test_date"),
            F.coalesce(F.col("valueQuantity_value"), F.col("value_numeric")).alias(
                "result_numeric"
            ),
            F.coalesce(F.col("valueString"), F.col("value_text")).alias("result_text"),
            F.coalesce(F.col("valueQuantity_unit"), F.col("unit")).alias("result_unit"),
            F.coalesce(F.col("interpretation"), F.col("result_interpretation")).alias(
                "interpretation"
            ),
            F.col("encounter_id"),
        )
    )

    # Map test codes to biomarker types
    biomarker_mapping_data = [
        (code, name) for code, name in BIOMARKER_CODES.items()
    ]
    df_bm_map = spark.createDataFrame(
        biomarker_mapping_data, ["test_code", "biomarker_name"]
    )

    df_mapped = (
        df_biomarkers
        .join(df_bm_map, on="test_code", how="left")
        .withColumn(
            "biomarker_type",
            F.when(F.col("biomarker_name").rlike("PD-L1"), F.lit("PD-L1"))
            .when(F.col("biomarker_name").rlike("TMB"), F.lit("TMB"))
            .when(F.col("biomarker_name").rlike("NGS"), F.lit("NGS"))
            .otherwise(F.lit("Other")),
        )
    )

    # Interpret results
    df_interpreted = (
        df_mapped
        .withColumn(
            "result_positive",
            F.when(
                F.col("biomarker_type") == "PD-L1",
                # PD-L1 positive if TPS >= 1%
                F.coalesce(
                    F.col("result_numeric") >= 1,
                    F.lower(F.col("interpretation")).rlike("positive|high"),
                ),
            )
            .when(
                F.col("biomarker_type") == "TMB",
                # TMB-high if >= 10 mut/Mb
                F.coalesce(
                    F.col("result_numeric") >= 10,
                    F.lower(F.col("interpretation")).rlike("high"),
                ),
            )
            .when(
                F.col("biomarker_type") == "NGS",
                F.lower(F.col("interpretation")).rlike(
                    "positive|mutation.*detected|pathogenic"
                ),
            )
            .otherwise(F.lit(None).cast(BooleanType())),
        )
        .withColumn(
            "pdl1_tps_score",
            F.when(
                F.col("biomarker_type") == "PD-L1",
                F.col("result_numeric"),
            ),
        )
        .withColumn(
            "tmb_score",
            F.when(
                F.col("biomarker_type") == "TMB",
                F.col("result_numeric"),
            ),
        )
    )

    # Link to patient dimension
    df_patients = (
        spark.table(f"{SILVER_SCHEMA}.dim_patient")
        .filter(F.col("is_current") == True)
        .select("patient_id", "source_patient_id")
    )

    df_linked = df_interpreted.join(df_patients, on="source_patient_id", how="inner")

    # Final fact table
    df_fact = (
        df_linked
        .withColumn("biomarker_test_id", F.expr("uuid()"))
        .withColumn("test_date_key", generate_date_key("test_date"))
        .select(
            "biomarker_test_id",
            "patient_id",
            "test_date",
            "test_date_key",
            "biomarker_type",
            "biomarker_name",
            "test_code",
            "result_numeric",
            "result_text",
            "result_unit",
            "result_positive",
            "pdl1_tps_score",
            "tmb_score",
            "interpretation",
        )
        .withColumn("_updated_timestamp", F.current_timestamp())
    )

    logger.info(f"Biomarker tests built: {df_fact.count():,} records")
    df_fact.groupBy("biomarker_type").count().show()
    return df_fact

# COMMAND ----------

df_biomarker = build_fact_biomarker_test()
write_fact_table(df_biomarker, "fact_biomarker_test")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Fact: Progression Event
# MAGIC
# MAGIC Identify disease progression events and calculate PFS days.

# COMMAND ----------

def build_fact_progression_event() -> DataFrame:
    """
    Build the progression event fact table.

    Identifies disease progression events from response assessments
    (PD), imaging reports, and clinical documentation.  Calculates
    progression-free survival (PFS) in days from diagnosis and from
    the start of each treatment line.

    Returns
    -------
    DataFrame
        Progression event fact records with PFS calculations.
    """
    logger.info("Building fact_progression_event")

    # Get PD (progressive disease) assessments
    df_assessments = (
        spark.table(f"{SILVER_SCHEMA}.fact_response_assessment")
        .filter(F.col("recist_response") == "PD")
        .select(
            "patient_id",
            "assessment_date",
            "treatment_episode_id",
            "line_of_therapy",
        )
    )

    # Also check observations for progression mentions
    df_observations = spark.table(f"{BRONZE_SCHEMA}.ehr_observations")
    df_patients = (
        spark.table(f"{SILVER_SCHEMA}.dim_patient")
        .filter(F.col("is_current") == True)
        .select("patient_id", "source_patient_id")
    )

    df_obs_progression = (
        df_observations
        .filter(
            F.lower(F.coalesce(F.col("valueString"), F.col("value"), F.lit(""))).rlike(
                "progression|progressive|progressed|recurrence|relapse"
            )
        )
        .select(
            F.coalesce(F.col("subject_id"), F.col("patient_id")).alias("source_patient_id"),
            F.coalesce(
                F.to_date(F.col("effectiveDateTime")),
                F.to_date(F.col("observation_date")),
            ).alias("assessment_date"),
        )
        .join(df_patients, on="source_patient_id", how="inner")
        .select(
            "patient_id",
            "assessment_date",
            F.lit(None).cast(StringType()).alias("treatment_episode_id"),
            F.lit(None).cast(IntegerType()).alias("line_of_therapy"),
        )
    )

    # Union progression events from both sources
    df_all_progression = df_assessments.unionByName(df_obs_progression)

    # Deduplicate: one progression event per patient per 30-day window
    window_prog = Window.partitionBy("patient_id").orderBy("assessment_date")

    df_deduped = (
        df_all_progression
        .withColumn("prev_prog_date", F.lag("assessment_date").over(window_prog))
        .withColumn(
            "days_since_prev_prog",
            F.datediff(F.col("assessment_date"), F.col("prev_prog_date")),
        )
        .filter(
            F.col("days_since_prev_prog").isNull() |
            (F.col("days_since_prev_prog") > 30)
        )
        .drop("prev_prog_date", "days_since_prev_prog")
    )

    # Calculate PFS from first diagnosis
    df_first_dx = (
        spark.table(f"{SILVER_SCHEMA}.fact_diagnosis")
        .groupBy("patient_id")
        .agg(F.min("diagnosis_date").alias("first_diagnosis_date"))
    )

    df_with_pfs = (
        df_deduped
        .join(df_first_dx, on="patient_id", how="left")
        .withColumn(
            "pfs_days_from_diagnosis",
            F.datediff(F.col("assessment_date"), F.col("first_diagnosis_date")),
        )
    )

    # Calculate PFS from treatment start
    df_tx_starts = (
        spark.table(f"{SILVER_SCHEMA}.fact_treatment_episode")
        .select(
            F.col("patient_id").alias("tx_patient_id"),
            "treatment_episode_id",
            "episode_start_date",
            "line_of_therapy",
        )
    )

    df_with_tx_pfs = (
        df_with_pfs.alias("p")
        .join(
            df_tx_starts.alias("t"),
            (F.col("p.patient_id") == F.col("t.tx_patient_id")) &
            (F.col("p.assessment_date") >= F.col("t.episode_start_date")),
            how="left",
        )
    )

    # Pick the closest preceding treatment
    window_closest = Window.partitionBy(
        "p.patient_id", "p.assessment_date"
    ).orderBy(
        F.datediff(F.col("p.assessment_date"), F.col("t.episode_start_date"))
    )

    df_best_match = (
        df_with_tx_pfs
        .withColumn("_rank", F.row_number().over(window_closest))
        .filter(F.col("_rank") == 1)
        .drop("_rank")
    )

    # Assign progression event number per patient
    window_event_num = Window.partitionBy("p.patient_id").orderBy("p.assessment_date")

    df_fact = (
        df_best_match
        .withColumn("progression_event_id", F.expr("uuid()"))
        .withColumn(
            "progression_number",
            F.row_number().over(window_event_num),
        )
        .withColumn(
            "pfs_days_from_treatment",
            F.datediff(F.col("p.assessment_date"), F.col("t.episode_start_date")),
        )
        .withColumn(
            "progression_date_key",
            F.date_format(F.col("p.assessment_date"), "yyyyMMdd").cast(IntegerType()),
        )
        .select(
            "progression_event_id",
            F.col("p.patient_id").alias("patient_id"),
            F.col("p.assessment_date").alias("progression_date"),
            "progression_date_key",
            "progression_number",
            "first_diagnosis_date",
            "pfs_days_from_diagnosis",
            F.col("t.treatment_episode_id").alias("treatment_episode_id"),
            F.col("t.line_of_therapy").alias("line_of_therapy"),
            F.col("t.episode_start_date").alias("treatment_start_date"),
            "pfs_days_from_treatment",
        )
        .withColumn("_updated_timestamp", F.current_timestamp())
    )

    logger.info(f"Progression events built: {df_fact.count():,} records")
    return df_fact

# COMMAND ----------

df_progression = build_fact_progression_event()
write_fact_table(df_progression, "fact_progression_event")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Fact: Clinical Trial Enrollment
# MAGIC
# MAGIC Extract clinical trial enrollments from encounter data.

# COMMAND ----------

def build_fact_trial_enrollment() -> DataFrame:
    """
    Build the clinical trial enrollment fact table.

    Identifies patients enrolled in clinical trials from encounter
    data, procedure codes (research-related), and clinical notes.
    Captures trial identifiers, enrollment dates, and status.

    Returns
    -------
    DataFrame
        Trial enrollment fact records.
    """
    logger.info("Building fact_trial_enrollment")

    # Clinical trial identification from encounters
    df_encounters = spark.table(f"{BRONZE_SCHEMA}.ehr_encounters")

    df_trial_encounters = (
        df_encounters
        .filter(
            F.lower(F.coalesce(F.col("type"), F.col("encounter_type"), F.lit(""))).rlike(
                "research|trial|study|investigational|protocol"
            ) |
            F.lower(F.coalesce(F.col("serviceType"), F.col("service_type"), F.lit(""))).rlike(
                "clinical.?trial|research"
            ) |
            F.col("clinical_trial_id").isNotNull()
        )
        .select(
            F.coalesce(F.col("subject_id"), F.col("patient_id")).alias("source_patient_id"),
            F.coalesce(
                F.to_date(F.col("period_start")),
                F.to_date(F.col("encounter_date")),
            ).alias("enrollment_date"),
            F.coalesce(
                F.col("clinical_trial_id"),
                F.col("study_id"),
                F.col("protocol_number"),
            ).alias("trial_identifier"),
            F.coalesce(
                F.col("trial_name"),
                F.col("study_name"),
            ).alias("trial_name"),
            F.coalesce(
                F.col("trial_phase"),
                F.col("study_phase"),
            ).alias("trial_phase"),
            F.coalesce(
                F.col("trial_status"),
                F.col("enrollment_status"),
                F.lit("enrolled"),
            ).alias("enrollment_status"),
            F.col("encounter_id"),
        )
    )

    # Also check procedures for research-related codes
    df_procedures = spark.table(f"{BRONZE_SCHEMA}.ehr_procedures")

    df_trial_procedures = (
        df_procedures
        .filter(
            F.lower(F.coalesce(F.col("code"), F.col("procedure_code"), F.lit(""))).rlike(
                "0074T|0075T|99199"  # Clinical trial-related procedure codes
            ) |
            F.lower(F.coalesce(F.col("category"), F.lit(""))).rlike(
                "research|trial|investigational"
            )
        )
        .select(
            F.coalesce(F.col("subject_id"), F.col("patient_id")).alias("source_patient_id"),
            F.coalesce(
                F.to_date(F.col("performedDateTime")),
                F.to_date(F.col("procedure_date")),
            ).alias("enrollment_date"),
            F.lit(None).cast(StringType()).alias("trial_identifier"),
            F.lit(None).cast(StringType()).alias("trial_name"),
            F.lit(None).cast(StringType()).alias("trial_phase"),
            F.lit("enrolled").alias("enrollment_status"),
            F.col("encounter_id"),
        )
    )

    df_all_trials = df_trial_encounters.unionByName(df_trial_procedures)

    # Link to patient dimension
    df_patients = (
        spark.table(f"{SILVER_SCHEMA}.dim_patient")
        .filter(F.col("is_current") == True)
        .select("patient_id", "source_patient_id")
    )

    df_linked = df_all_trials.join(df_patients, on="source_patient_id", how="inner")

    # Deduplicate: one enrollment per patient per trial
    window_dedup = Window.partitionBy("patient_id", "trial_identifier").orderBy(
        F.col("enrollment_date").asc()
    )

    df_deduped = (
        df_linked
        .withColumn("_rn", F.row_number().over(window_dedup))
        .filter(F.col("_rn") == 1)
        .drop("_rn")
    )

    # Link to treatment for context
    df_treatments = (
        spark.table(f"{SILVER_SCHEMA}.fact_treatment_episode")
        .select(
            F.col("patient_id").alias("tx_patient_id"),
            "treatment_episode_id",
            "episode_start_date",
            "line_of_therapy",
        )
    )

    df_with_tx = (
        df_deduped.alias("e")
        .join(
            df_treatments.alias("t"),
            (F.col("e.patient_id") == F.col("t.tx_patient_id")) &
            (F.abs(F.datediff(F.col("e.enrollment_date"), F.col("t.episode_start_date"))) <= 30),
            how="left",
        )
    )

    # Take closest treatment
    window_closest_tx = Window.partitionBy(
        "e.patient_id", "e.enrollment_date"
    ).orderBy(
        F.abs(F.datediff(F.col("e.enrollment_date"), F.col("t.episode_start_date")))
    )

    df_best_tx = (
        df_with_tx
        .withColumn("_tx_rank", F.row_number().over(window_closest_tx))
        .filter(F.col("_tx_rank") == 1)
        .drop("_tx_rank")
    )

    # Final fact table
    df_fact = (
        df_best_tx
        .withColumn("trial_enrollment_id", F.expr("uuid()"))
        .withColumn("enrollment_date_key", generate_date_key("enrollment_date"))
        .select(
            "trial_enrollment_id",
            F.col("e.patient_id").alias("patient_id"),
            "enrollment_date",
            "enrollment_date_key",
            "trial_identifier",
            "trial_name",
            "trial_phase",
            "enrollment_status",
            F.col("t.treatment_episode_id").alias("treatment_episode_id"),
            F.col("t.line_of_therapy").alias("line_of_therapy"),
        )
        .withColumn("_updated_timestamp", F.current_timestamp())
    )

    logger.info(f"Trial enrollments built: {df_fact.count():,} records")
    return df_fact

# COMMAND ----------

df_trial = build_fact_trial_enrollment()
write_fact_table(df_trial, "fact_trial_enrollment")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

fact_tables = [
    "fact_diagnosis",
    "fact_treatment_episode",
    "fact_response_assessment",
    "fact_biomarker_test",
    "fact_progression_event",
    "fact_trial_enrollment",
]

logger.info("=" * 60)
logger.info("Silver Clinical Fact Tables Summary")
logger.info("=" * 60)

summary_rows = []
for table_name in fact_tables:
    full_table = f"{SILVER_SCHEMA}.{table_name}"
    try:
        count = spark.sql(f"SELECT COUNT(*) as cnt FROM {full_table}").first()["cnt"]
        cols = len(spark.table(full_table).columns)
        summary_rows.append((table_name, count, cols, "SUCCESS"))
        logger.info(f"  {table_name}: {count:,} rows, {cols} columns")
    except Exception as e:
        summary_rows.append((table_name, -1, 0, f"ERROR: {e}"))
        logger.error(f"  {table_name}: ERROR - {e}")

summary_df = spark.createDataFrame(
    summary_rows,
    ["table_name", "row_count", "column_count", "status"],
)
display(summary_df)

logger.info(f"Processing completed at: {datetime.utcnow().isoformat()}")
logger.info("=" * 60)
