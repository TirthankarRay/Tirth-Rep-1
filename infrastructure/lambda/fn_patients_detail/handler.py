"""
Lambda handler for GET /api/v1/patients/{id}

Returns a single patient with all related clinical records: diagnoses,
treatment episodes, biomarker tests, progression events, and trial
enrollments.

Path parameters
---------------
id : str
    The patient_id (UUID) to retrieve.
"""

import logging
import sys

# Lambda Layer imports
sys.path.insert(0, "/opt/python")

from shared.db import execute_query, build_response  # noqa: E402

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def lambda_handler(event: dict, context) -> dict:
    """AWS Lambda entry point."""

    logger.info("Event: %s", event)

    try:
        # ------------------------------------------------------------------
        # Extract path parameter
        # ------------------------------------------------------------------
        path_params = event.get("pathParameters") or {}
        patient_id = path_params.get("id")

        if not patient_id:
            return build_response(400, {"error": "Missing patient id in path"})

        # ------------------------------------------------------------------
        # Fetch patient demographics
        # ------------------------------------------------------------------
        patient_sql = """
            SELECT
                patient_id,
                external_id,
                date_of_birth,
                gender,
                race_ethnicity,
                state,
                county,
                zip_code,
                insurance_type,
                urban_rural,
                created_at,
                updated_at
            FROM sclc_core.dim_patient
            WHERE patient_id = :patient_id
        """
        patient_params = [{"name": "patient_id", "value": patient_id}]
        patient_rows = execute_query(patient_sql, patient_params)

        if not patient_rows:
            return build_response(404, {"error": "Patient not found"})

        patient = patient_rows[0]

        # ------------------------------------------------------------------
        # Fetch related records in parallel-style (sequential in Lambda,
        # but each is a separate lightweight query)
        # ------------------------------------------------------------------

        # Diagnoses
        diagnoses_sql = """
            SELECT
                diagnosis_id,
                diagnosis_date,
                stage,
                histology,
                ecog_status,
                smoking_status
            FROM sclc_core.fact_diagnosis
            WHERE patient_id = :patient_id
            ORDER BY diagnosis_date DESC
        """
        diagnosis_rows = execute_query(diagnoses_sql, patient_params)

        # Treatment episodes
        treatments_sql = """
            SELECT
                episode_id,
                line_of_therapy,
                treatment_start_date,
                treatment_end_date,
                regimen_name,
                regimen_category,
                includes_immunotherapy
            FROM sclc_core.fact_treatment_episode
            WHERE patient_id = :patient_id
            ORDER BY treatment_start_date DESC
        """
        treatment_rows = execute_query(treatments_sql, patient_params)

        # Biomarker tests
        biomarkers_sql = """
            SELECT
                test_id,
                test_date,
                result_date,
                biomarker_type,
                test_result,
                pdl1_percentage,
                tmb_score
            FROM sclc_core.fact_biomarker_test
            WHERE patient_id = :patient_id
            ORDER BY test_date DESC
        """
        biomarker_rows = execute_query(biomarkers_sql, patient_params)

        # Progression events
        progressions_sql = """
            SELECT
                event_id,
                progression_date,
                line_before_progression,
                pfs_days,
                progression_site
            FROM sclc_core.fact_progression_event
            WHERE patient_id = :patient_id
            ORDER BY progression_date DESC
        """
        progression_rows = execute_query(progressions_sql, patient_params)

        # Trial enrollments
        trials_sql = """
            SELECT
                enrollment_id,
                trial_id,
                trial_phase,
                enrollment_date,
                trial_status
            FROM sclc_core.fact_trial_enrollment
            WHERE patient_id = :patient_id
            ORDER BY enrollment_date DESC
        """
        trial_rows = execute_query(trials_sql, patient_params)

        # ------------------------------------------------------------------
        # Build response
        # ------------------------------------------------------------------
        body = {
            "patientId": patient.get("patient_id"),
            "externalId": patient.get("external_id"),
            "dateOfBirth": patient.get("date_of_birth"),
            "gender": patient.get("gender"),
            "raceEthnicity": patient.get("race_ethnicity"),
            "state": patient.get("state"),
            "county": patient.get("county"),
            "zipCode": patient.get("zip_code"),
            "insuranceType": patient.get("insurance_type"),
            "urbanRural": patient.get("urban_rural"),
            "createdAt": patient.get("created_at"),
            "updatedAt": patient.get("updated_at"),
            "diagnoses": [
                {
                    "diagnosisId": r.get("diagnosis_id"),
                    "diagnosisDate": r.get("diagnosis_date"),
                    "stage": r.get("stage"),
                    "histology": r.get("histology"),
                    "ecogStatus": r.get("ecog_status"),
                    "smokingStatus": r.get("smoking_status"),
                }
                for r in diagnosis_rows
            ],
            "treatmentEpisodes": [
                {
                    "episodeId": r.get("episode_id"),
                    "lineOfTherapy": r.get("line_of_therapy"),
                    "treatmentStartDate": r.get("treatment_start_date"),
                    "treatmentEndDate": r.get("treatment_end_date"),
                    "regimenName": r.get("regimen_name"),
                    "regimenCategory": r.get("regimen_category"),
                    "includesImmunotherapy": r.get("includes_immunotherapy"),
                }
                for r in treatment_rows
            ],
            "biomarkerTests": [
                {
                    "testId": r.get("test_id"),
                    "testDate": r.get("test_date"),
                    "resultDate": r.get("result_date"),
                    "biomarkerType": r.get("biomarker_type"),
                    "testResult": r.get("test_result"),
                    "pdl1Percentage": r.get("pdl1_percentage"),
                    "tmbScore": r.get("tmb_score"),
                }
                for r in biomarker_rows
            ],
            "progressionEvents": [
                {
                    "eventId": r.get("event_id"),
                    "progressionDate": r.get("progression_date"),
                    "lineBeforeProgression": r.get("line_before_progression"),
                    "pfsDays": r.get("pfs_days"),
                    "progressionSite": r.get("progression_site"),
                }
                for r in progression_rows
            ],
            "trialEnrollments": [
                {
                    "enrollmentId": r.get("enrollment_id"),
                    "trialId": r.get("trial_id"),
                    "trialPhase": r.get("trial_phase"),
                    "enrollmentDate": r.get("enrollment_date"),
                    "trialStatus": r.get("trial_status"),
                }
                for r in trial_rows
            ],
        }

        logger.info("Returning patient detail for %s", patient_id)
        return build_response(200, body)

    except Exception as exc:
        logger.exception("Error fetching patient detail")
        return build_response(500, {"error": str(exc)})
