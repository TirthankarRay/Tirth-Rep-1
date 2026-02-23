"""
Lambda handler for GET /api/v1/metrics/overview

Returns top-level KPI metrics for the SCLC Patient Journey Dashboard
overview cards.  Reads from the pre-aggregated ``sclc_analytics.agg_overview_metrics``
table and returns the most recent snapshot.

Query parameters
----------------
stage : str, optional
    Filter by stage (e.g. ``LS-SCLC``, ``ES-SCLC``).
state : str, optional
    Filter by US state abbreviation (e.g. ``CA``, ``TX``).
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
        # Extract query parameters
        # ------------------------------------------------------------------
        params = event.get("queryStringParameters") or {}
        stage = params.get("stage")
        state = params.get("state")

        # ------------------------------------------------------------------
        # Build SQL query
        # ------------------------------------------------------------------
        conditions = ["snapshot_date = (SELECT MAX(snapshot_date) FROM sclc_analytics.agg_overview_metrics)"]
        sql_params: list[dict] = []

        if stage:
            conditions.append("stage_filter = :stage")
            sql_params.append({"name": "stage", "value": stage})
        else:
            conditions.append("stage_filter IS NULL")

        if state:
            conditions.append("state_filter = :state")
            sql_params.append({"name": "state", "value": state})
        else:
            conditions.append("state_filter IS NULL")

        where_clause = " AND ".join(conditions)

        sql = f"""
            SELECT
                total_patients,
                new_diagnoses_mtd,
                new_diagnoses_qtd,
                new_diagnoses_ytd,
                median_time_to_treatment,
                biomarker_testing_rate,
                immunotherapy_uptake_rate,
                clinical_trial_rate
            FROM sclc_analytics.agg_overview_metrics
            WHERE {where_clause}
            LIMIT 1
        """

        # ------------------------------------------------------------------
        # Execute and transform
        # ------------------------------------------------------------------
        rows = execute_query(sql, sql_params if sql_params else None)

        if not rows:
            # Return zeroed-out metrics when no data matches the filters
            body = {
                "totalPatients": 0,
                "newDiagnosesMTD": 0,
                "newDiagnosesQTD": 0,
                "newDiagnosesYTD": 0,
                "medianTimeToTreatment": 0,
                "biomarkerTestingRate": 0,
                "immunotherapyUptakeRate": 0,
                "clinicalTrialRate": 0,
            }
            return build_response(200, body)

        row = rows[0]
        body = {
            "totalPatients": row.get("total_patients", 0) or 0,
            "newDiagnosesMTD": row.get("new_diagnoses_mtd", 0) or 0,
            "newDiagnosesQTD": row.get("new_diagnoses_qtd", 0) or 0,
            "newDiagnosesYTD": row.get("new_diagnoses_ytd", 0) or 0,
            "medianTimeToTreatment": row.get("median_time_to_treatment", 0) or 0,
            "biomarkerTestingRate": row.get("biomarker_testing_rate", 0) or 0,
            "immunotherapyUptakeRate": row.get("immunotherapy_uptake_rate", 0) or 0,
            "clinicalTrialRate": row.get("clinical_trial_rate", 0) or 0,
        }

        logger.info("Returning overview metrics")
        return build_response(200, body)

    except Exception as exc:
        logger.exception("Error fetching overview metrics")
        return build_response(500, {"error": str(exc)})
