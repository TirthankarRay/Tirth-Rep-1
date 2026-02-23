"""
Lambda handler for GET /api/v1/metrics/time-to-treatment

Returns the time-to-treatment distribution, median/mean days, and the
percentage of patients treated within the 21-day clinical target.
Reads from the pre-aggregated ``sclc_analytics.agg_time_to_treatment`` table.

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
        conditions = [
            "snapshot_date = (SELECT MAX(snapshot_date) FROM sclc_analytics.agg_time_to_treatment)"
        ]
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
                bucket_label,
                bucket_order,
                patient_count,
                percentage,
                median_days,
                mean_days,
                within_target_pct
            FROM sclc_analytics.agg_time_to_treatment
            WHERE {where_clause}
            ORDER BY bucket_order ASC
        """

        # ------------------------------------------------------------------
        # Execute and transform
        # ------------------------------------------------------------------
        rows = execute_query(sql, sql_params if sql_params else None)

        if not rows:
            body = {
                "distribution": [],
                "medianDays": 0,
                "meanDays": 0,
                "withinTargetPercentage": 0,
            }
            return build_response(200, body)

        # Build the distribution array from the bucket rows
        distribution = []
        for row in rows:
            distribution.append({
                "label": row.get("bucket_label", ""),
                "count": row.get("patient_count", 0) or 0,
                "percentage": row.get("percentage", 0) or 0,
            })

        # Summary metrics are the same across all bucket rows within a
        # single snapshot/filter combination — take from the first row.
        first = rows[0]
        body = {
            "distribution": distribution,
            "medianDays": first.get("median_days", 0) or 0,
            "meanDays": first.get("mean_days", 0) or 0,
            "withinTargetPercentage": first.get("within_target_pct", 0) or 0,
        }

        logger.info("Returning time-to-treatment metrics (%d buckets)", len(distribution))
        return build_response(200, body)

    except Exception as exc:
        logger.exception("Error fetching time-to-treatment metrics")
        return build_response(500, {"error": str(exc)})
