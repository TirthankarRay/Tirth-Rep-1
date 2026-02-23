"""
Lambda handler for GET /api/v1/metrics/treatment-patterns

Returns treatment pattern breakdowns grouped by line of therapy.
Reads from the pre-aggregated ``sclc_analytics.agg_treatment_patterns`` table.

Query parameters
----------------
stage : str, optional
    Filter by stage (e.g. ``LS-SCLC``, ``ES-SCLC``).
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

        # ------------------------------------------------------------------
        # Build SQL query
        # ------------------------------------------------------------------
        conditions = [
            "snapshot_date = (SELECT MAX(snapshot_date) FROM sclc_analytics.agg_treatment_patterns)"
        ]
        sql_params: list[dict] = []

        if stage:
            conditions.append("stage_filter = :stage")
            sql_params.append({"name": "stage", "value": stage})
        else:
            conditions.append("stage_filter IS NULL")

        where_clause = " AND ".join(conditions)

        sql = f"""
            SELECT
                line_of_therapy,
                regimen_name,
                regimen_category,
                patient_count,
                percentage
            FROM sclc_analytics.agg_treatment_patterns
            WHERE {where_clause}
            ORDER BY line_of_therapy, patient_count DESC
        """

        # ------------------------------------------------------------------
        # Execute and transform
        # ------------------------------------------------------------------
        rows = execute_query(sql, sql_params if sql_params else None)

        # Group results by line_of_therapy
        first_line: list[dict] = []
        second_line: list[dict] = []

        for row in rows:
            item = {
                "regimenName": row.get("regimen_name", "Unknown"),
                "category": row.get("regimen_category", "Other"),
                "patientCount": row.get("patient_count", 0) or 0,
                "percentage": row.get("percentage", 0) or 0,
            }

            lot = row.get("line_of_therapy", "")
            if lot == "1st line":
                first_line.append(item)
            elif lot == "2nd line":
                second_line.append(item)
            # 3rd line+ rows are excluded per the API contract
            # but could be added to a thirdLine array if needed

        body = {
            "firstLine": first_line,
            "secondLine": second_line,
        }

        logger.info(
            "Returning treatment patterns: %d first-line, %d second-line",
            len(first_line),
            len(second_line),
        )
        return build_response(200, body)

    except Exception as exc:
        logger.exception("Error fetching treatment patterns")
        return build_response(500, {"error": str(exc)})
