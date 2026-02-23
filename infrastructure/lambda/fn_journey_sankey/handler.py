"""
Lambda handler for GET /api/v1/patients/journey/sankey

Returns Sankey diagram data (nodes and links) representing the SCLC
patient journey flow from diagnosis through treatment stages.
Reads from the pre-aggregated ``sclc_analytics.agg_sankey_journey`` table.

Query parameters
----------------
stage : str, optional
    Filter by SCLC stage (e.g. ``LS-SCLC``, ``ES-SCLC``).
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
            "snapshot_date = (SELECT MAX(snapshot_date) FROM sclc_analytics.agg_sankey_journey)"
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
                source_node,
                target_node,
                patient_count,
                source_category,
                target_category
            FROM sclc_analytics.agg_sankey_journey
            WHERE {where_clause}
            ORDER BY patient_count DESC
        """

        # ------------------------------------------------------------------
        # Execute and transform
        # ------------------------------------------------------------------
        rows = execute_query(sql, sql_params if sql_params else None)

        # Build a unique node list from source and target columns
        node_map: dict[str, dict] = {}

        for row in rows:
            source = row.get("source_node", "")
            target = row.get("target_node", "")
            source_cat = row.get("source_category", "")
            target_cat = row.get("target_category", "")

            if source and source not in node_map:
                node_map[source] = {
                    "id": source,
                    "name": source,
                    "category": source_cat or "",
                }
            if target and target not in node_map:
                node_map[target] = {
                    "id": target,
                    "name": target,
                    "category": target_cat or "",
                }

        nodes = list(node_map.values())

        # Build links (already sorted by patient_count DESC from query)
        links = []
        for row in rows:
            links.append({
                "source": row.get("source_node", ""),
                "target": row.get("target_node", ""),
                "value": row.get("patient_count", 0) or 0,
            })

        body = {
            "nodes": nodes,
            "links": links,
        }

        logger.info("Returning sankey data: %d nodes, %d links", len(nodes), len(links))
        return build_response(200, body)

    except Exception as exc:
        logger.exception("Error fetching sankey journey data")
        return build_response(500, {"error": str(exc)})
