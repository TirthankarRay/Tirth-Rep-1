"""
Lambda handler for GET /api/v1/patients

Returns a paginated list of patients with optional filtering and sorting.
Queries ``sclc_core.dim_patient`` joined with the latest diagnosis and
first-line treatment episode.

Query parameters
----------------
page : int, optional
    Page number (default 1).
pageSize : int, optional
    Number of records per page (default 25, max 100).
stage : str, optional
    Filter by SCLC stage (e.g. ``LS-SCLC``, ``ES-SCLC``).
state : str, optional
    Filter by US state abbreviation.
insuranceType : str, optional
    Filter by insurance type (e.g. ``Medicare``, ``Commercial``).
sortBy : str, optional
    Column to sort by (default ``created_at``).
sortOrder : str, optional
    Sort direction: ``asc`` or ``desc`` (default ``desc``).
"""

import logging
import math
import sys

# Lambda Layer imports
sys.path.insert(0, "/opt/python")

from shared.db import execute_query, build_response  # noqa: E402

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Allowed sort columns to prevent SQL injection via sort parameter
_ALLOWED_SORT_COLUMNS = {
    "created_at": "p.created_at",
    "external_id": "p.external_id",
    "date_of_birth": "p.date_of_birth",
    "gender": "p.gender",
    "state": "p.state",
    "insurance_type": "p.insurance_type",
    "stage": "d.stage",
    "days_to_treatment": "days_to_treatment",
}


def lambda_handler(event: dict, context) -> dict:
    """AWS Lambda entry point."""

    logger.info("Event: %s", event)

    try:
        # ------------------------------------------------------------------
        # Extract and validate query parameters
        # ------------------------------------------------------------------
        params = event.get("queryStringParameters") or {}

        try:
            page = max(1, int(params.get("page", "1")))
        except (ValueError, TypeError):
            return build_response(400, {"error": "Invalid 'page' parameter; must be a positive integer"})

        try:
            page_size = min(100, max(1, int(params.get("pageSize", "25"))))
        except (ValueError, TypeError):
            return build_response(400, {"error": "Invalid 'pageSize' parameter; must be 1-100"})

        stage = params.get("stage")
        state = params.get("state")
        insurance_type = params.get("insuranceType")
        sort_by = params.get("sortBy", "created_at")
        sort_order = params.get("sortOrder", "desc").lower()

        if sort_order not in ("asc", "desc"):
            return build_response(400, {"error": "sortOrder must be 'asc' or 'desc'"})

        sort_column = _ALLOWED_SORT_COLUMNS.get(sort_by, "p.created_at")

        # ------------------------------------------------------------------
        # Build WHERE clause
        # ------------------------------------------------------------------
        conditions: list[str] = []
        sql_params: list[dict] = []

        if stage:
            conditions.append("d.stage = :stage")
            sql_params.append({"name": "stage", "value": stage})
        if state:
            conditions.append("p.state = :state")
            sql_params.append({"name": "state", "value": state})
        if insurance_type:
            conditions.append("p.insurance_type = :insurance_type")
            sql_params.append({"name": "insurance_type", "value": insurance_type})

        where_clause = (" WHERE " + " AND ".join(conditions)) if conditions else ""

        # ------------------------------------------------------------------
        # Count query
        # ------------------------------------------------------------------
        count_sql = f"""
            SELECT COUNT(DISTINCT p.patient_id) AS total
            FROM sclc_core.dim_patient p
            LEFT JOIN sclc_core.fact_diagnosis d
                ON p.patient_id = d.patient_id
            {where_clause}
        """

        count_rows = execute_query(count_sql, sql_params if sql_params else None)
        total = count_rows[0]["total"] if count_rows else 0

        total_pages = math.ceil(total / page_size) if total > 0 else 0
        offset = (page - 1) * page_size

        # ------------------------------------------------------------------
        # Data query with pagination
        # ------------------------------------------------------------------
        data_sql = f"""
            SELECT
                p.patient_id        AS id,
                p.external_id       AS external_id,
                p.date_of_birth     AS date_of_birth,
                p.gender            AS gender,
                p.state             AS state,
                p.insurance_type    AS insurance_type,
                d.stage             AS stage,
                t.regimen_name      AS current_treatment,
                DATEDIFF(day, d.diagnosis_date, t.treatment_start_date) AS days_to_treatment
            FROM sclc_core.dim_patient p
            LEFT JOIN (
                SELECT patient_id, stage, diagnosis_date,
                       ROW_NUMBER() OVER (PARTITION BY patient_id ORDER BY diagnosis_date DESC) AS rn
                FROM sclc_core.fact_diagnosis
            ) d ON p.patient_id = d.patient_id AND d.rn = 1
            LEFT JOIN (
                SELECT patient_id, regimen_name, treatment_start_date,
                       ROW_NUMBER() OVER (PARTITION BY patient_id ORDER BY treatment_start_date DESC) AS rn
                FROM sclc_core.fact_treatment_episode
            ) t ON p.patient_id = t.patient_id AND t.rn = 1
            {where_clause}
            ORDER BY {sort_column} {sort_order}
            LIMIT :page_size OFFSET :offset
        """

        data_params = list(sql_params)  # copy filter params
        data_params.append({"name": "page_size", "value": str(page_size)})
        data_params.append({"name": "offset", "value": str(offset)})

        rows = execute_query(data_sql, data_params)

        # ------------------------------------------------------------------
        # Transform to camelCase response
        # ------------------------------------------------------------------
        patients = []
        for row in rows:
            patients.append({
                "id": row.get("id", ""),
                "externalId": row.get("external_id", ""),
                "dateOfBirth": row.get("date_of_birth"),
                "gender": row.get("gender"),
                "state": row.get("state"),
                "insuranceType": row.get("insurance_type"),
                "stage": row.get("stage"),
                "currentTreatment": row.get("current_treatment"),
                "daysToTreatment": row.get("days_to_treatment"),
            })

        body = {
            "patients": patients,
            "total": total,
            "page": page,
            "pageSize": page_size,
            "totalPages": total_pages,
        }

        logger.info("Returning %d patients (page %d/%d)", len(patients), page, total_pages)
        return build_response(200, body)

    except Exception as exc:
        logger.exception("Error fetching patient list")
        return build_response(500, {"error": str(exc)})
