"""
Lambda handler for GET /api/v1/geographic/states

Returns state-level aggregated metrics for the geographic choropleth map.
Reads from the pre-aggregated ``sclc_analytics.agg_geographic_metrics`` table.

Query parameters
----------------
None required.
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
        # Build SQL query
        # ------------------------------------------------------------------
        sql = """
            SELECT
                state,
                state_name,
                patient_count,
                avg_time_to_treatment,
                immunotherapy_rate,
                trial_enrollment_rate
            FROM sclc_analytics.agg_geographic_metrics
            WHERE snapshot_date = (
                SELECT MAX(snapshot_date) FROM sclc_analytics.agg_geographic_metrics
            )
            ORDER BY patient_count DESC
        """

        # ------------------------------------------------------------------
        # Execute and transform
        # ------------------------------------------------------------------
        rows = execute_query(sql)

        states = []
        for row in rows:
            states.append({
                "state": row.get("state", ""),
                "stateName": row.get("state_name", ""),
                "patientCount": row.get("patient_count", 0) or 0,
                "avgTimeToTreatment": row.get("avg_time_to_treatment", 0) or 0,
                "immunotherapyRate": row.get("immunotherapy_rate", 0) or 0,
                "trialEnrollmentRate": row.get("trial_enrollment_rate", 0) or 0,
            })

        body = {"states": states}

        logger.info("Returning geographic metrics for %d states", len(states))
        return build_response(200, body)

    except Exception as exc:
        logger.exception("Error fetching geographic metrics")
        return build_response(500, {"error": str(exc)})
