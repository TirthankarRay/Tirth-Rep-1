"""Initial schema for SCLC dashboard

Revision ID: 001
Revises: None
Create Date: 2026-02-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patients",
        sa.Column("patient_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("external_id", sa.String(50), unique=True),
        sa.Column("date_of_birth", sa.Date),
        sa.Column("gender", sa.String(10)),
        sa.Column("race_ethnicity", sa.String(50)),
        sa.Column("state", sa.String(2)),
        sa.Column("county", sa.String(100)),
        sa.Column("zip_code", sa.String(10)),
        sa.Column("insurance_type", sa.String(50)),
        sa.Column("urban_rural", sa.String(20)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "facilities",
        sa.Column("facility_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("facility_name", sa.String(200)),
        sa.Column("facility_type", sa.String(50)),
        sa.Column("state", sa.String(2)),
        sa.Column("city", sa.String(100)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "diagnoses",
        sa.Column("diagnosis_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.patient_id"), nullable=False),
        sa.Column("diagnosis_date", sa.Date, nullable=False),
        sa.Column("stage", sa.String(20)),
        sa.Column("histology", sa.String(100)),
        sa.Column("ecog_status", sa.Integer),
        sa.Column("smoking_status", sa.String(50)),
        sa.Column("diagnosing_facility_id", UUID(as_uuid=True)),
        sa.Column("diagnosed_by_physician_id", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "biomarker_tests",
        sa.Column("test_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.patient_id"), nullable=False),
        sa.Column("test_date", sa.Date),
        sa.Column("result_date", sa.Date),
        sa.Column("biomarker_type", sa.String(50)),
        sa.Column("test_result", sa.String(100)),
        sa.Column("pdl1_percentage", sa.Numeric(5, 2)),
        sa.Column("tmb_score", sa.Numeric(5, 2)),
        sa.Column("testing_facility_id", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "treatment_episodes",
        sa.Column("episode_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.patient_id"), nullable=False),
        sa.Column("line_of_therapy", sa.Integer),
        sa.Column("treatment_start_date", sa.Date),
        sa.Column("treatment_end_date", sa.Date),
        sa.Column("regimen_name", sa.String(200)),
        sa.Column("regimen_category", sa.String(100)),
        sa.Column("includes_immunotherapy", sa.Boolean),
        sa.Column("treating_facility_id", UUID(as_uuid=True)),
        sa.Column("treating_physician_id", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "response_assessments",
        sa.Column("assessment_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("episode_id", UUID(as_uuid=True), sa.ForeignKey("treatment_episodes.episode_id"), nullable=False),
        sa.Column("assessment_date", sa.Date),
        sa.Column("response_type", sa.String(50)),
        sa.Column("assessment_method", sa.String(50)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "progression_events",
        sa.Column("progression_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.patient_id"), nullable=False),
        sa.Column("progression_date", sa.Date),
        sa.Column("line_before_progression", sa.Integer),
        sa.Column("pfs_days", sa.Integer),
        sa.Column("progression_site", sa.String(100)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "trial_enrollments",
        sa.Column("enrollment_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.patient_id"), nullable=False),
        sa.Column("trial_id", sa.String(100)),
        sa.Column("trial_phase", sa.String(10)),
        sa.Column("enrollment_date", sa.Date),
        sa.Column("trial_status", sa.String(50)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Indexes for common query patterns
    op.create_index("ix_patients_state", "patients", ["state"])
    op.create_index("ix_diagnoses_patient_id", "diagnoses", ["patient_id"])
    op.create_index("ix_diagnoses_stage", "diagnoses", ["stage"])
    op.create_index("ix_diagnoses_date", "diagnoses", ["diagnosis_date"])
    op.create_index("ix_treatment_episodes_patient_id", "treatment_episodes", ["patient_id"])
    op.create_index("ix_treatment_episodes_line", "treatment_episodes", ["line_of_therapy"])
    op.create_index("ix_biomarker_tests_patient_id", "biomarker_tests", ["patient_id"])


def downgrade() -> None:
    op.drop_table("trial_enrollments")
    op.drop_table("progression_events")
    op.drop_table("response_assessments")
    op.drop_table("treatment_episodes")
    op.drop_table("biomarker_tests")
    op.drop_table("diagnoses")
    op.drop_table("facilities")
    op.drop_table("patients")
