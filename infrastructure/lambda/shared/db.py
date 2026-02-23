"""
Shared Redshift Data API helper for Lambda functions.

Provides a thin wrapper around the boto3 redshift-data client to execute
queries against Amazon Redshift Serverless and return results as a list
of dictionaries.  Also includes a utility for building API Gateway proxy
integration responses with CORS headers.
"""

import json
import logging
import os
import time
from decimal import Decimal

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Configuration from environment variables
# ---------------------------------------------------------------------------
REDSHIFT_WORKGROUP = os.environ.get("REDSHIFT_WORKGROUP", "")
REDSHIFT_DATABASE = os.environ.get("REDSHIFT_DATABASE", "")

# Maximum time (seconds) to wait for a Redshift Data API statement to finish.
_QUERY_TIMEOUT_SECONDS = 30
_POLL_INTERVAL_SECONDS = 0.3

# boto3 client – instantiated once per Lambda cold start
_client = boto3.client("redshift-data")


# ---------------------------------------------------------------------------
# JSON encoder that handles Decimal and date/datetime objects
# ---------------------------------------------------------------------------
class _RedshiftEncoder(json.JSONEncoder):
    """Custom JSON encoder for types returned by the Redshift Data API."""

    def default(self, o):
        if isinstance(o, Decimal):
            # Return int when there is no fractional part, float otherwise.
            if o == o.to_integral_value():
                return int(o)
            return float(o)
        # date / datetime
        if hasattr(o, "isoformat"):
            return o.isoformat()
        return super().default(o)


# ---------------------------------------------------------------------------
# Core query execution
# ---------------------------------------------------------------------------
def execute_query(sql: str, parameters: list[dict] | None = None) -> list[dict]:
    """Execute a SQL statement via the Redshift Data API and return rows as
    a list of dictionaries.

    Parameters
    ----------
    sql : str
        The SQL statement to execute.  Use named parameters (e.g. ``:stage``)
        when ``parameters`` is supplied.
    parameters : list[dict] | None
        Optional list of ``{"name": "<param_name>", "value": "<param_value>"}``
        dictionaries passed to ``execute_statement``.

    Returns
    -------
    list[dict]
        Each row is represented as a dictionary keyed by column name.

    Raises
    ------
    RuntimeError
        If the statement fails or times out.
    """

    logger.info("Executing Redshift query: %s", sql[:200])
    if parameters:
        logger.info("Parameters: %s", parameters)

    # Build the execute_statement kwargs
    kwargs = {
        "WorkgroupName": REDSHIFT_WORKGROUP,
        "Database": REDSHIFT_DATABASE,
        "Sql": sql,
    }
    if parameters:
        kwargs["Parameters"] = parameters

    response = _client.execute_statement(**kwargs)
    statement_id = response["Id"]
    logger.info("Statement submitted: %s", statement_id)

    # Poll until the statement reaches a terminal state
    deadline = time.time() + _QUERY_TIMEOUT_SECONDS
    while time.time() < deadline:
        desc = _client.describe_statement(Id=statement_id)
        status = desc["Status"]

        if status == "FINISHED":
            return _fetch_results(statement_id)

        if status == "FAILED":
            error = desc.get("Error", "Unknown error")
            logger.error("Query FAILED (%s): %s", statement_id, error)
            raise RuntimeError(f"Redshift query failed: {error}")

        if status in ("ABORTED",):
            raise RuntimeError(f"Redshift query was aborted: {statement_id}")

        time.sleep(_POLL_INTERVAL_SECONDS)

    # If we exit the loop the query has timed out
    raise RuntimeError(
        f"Redshift query timed out after {_QUERY_TIMEOUT_SECONDS}s "
        f"(statement_id={statement_id})"
    )


def _fetch_results(statement_id: str) -> list[dict]:
    """Paginate through ``get_statement_result`` and return all rows as a list
    of dictionaries."""

    rows: list[dict] = []
    kwargs = {"Id": statement_id}

    while True:
        result = _client.get_statement_result(**kwargs)

        # Column metadata – only need to read once
        columns = [col["name"] for col in result["ColumnMetadata"]]

        for record in result["Records"]:
            row = {}
            for idx, field in enumerate(record):
                # Each field is a dict with exactly one key indicating its type
                # e.g. {"longValue": 42}, {"stringValue": "CA"}, {"isNull": True}
                if "isNull" in field and field["isNull"]:
                    row[columns[idx]] = None
                elif "longValue" in field:
                    row[columns[idx]] = field["longValue"]
                elif "doubleValue" in field:
                    row[columns[idx]] = field["doubleValue"]
                elif "stringValue" in field:
                    row[columns[idx]] = field["stringValue"]
                elif "booleanValue" in field:
                    row[columns[idx]] = field["booleanValue"]
                elif "blobValue" in field:
                    row[columns[idx]] = field["blobValue"]
                else:
                    row[columns[idx]] = None
            rows.append(row)

        # Handle pagination
        next_token = result.get("NextToken")
        if not next_token:
            break
        kwargs["NextToken"] = next_token

    logger.info("Query returned %d rows", len(rows))
    return rows


# ---------------------------------------------------------------------------
# API Gateway response builder
# ---------------------------------------------------------------------------
def build_response(status_code: int, body: dict | list | str) -> dict:
    """Return an API Gateway proxy integration response with CORS headers.

    Parameters
    ----------
    status_code : int
        HTTP status code (e.g. 200, 400, 404, 500).
    body : dict | list | str
        Response payload.  Dicts and lists are JSON-serialised automatically.

    Returns
    -------
    dict
        A properly formatted API Gateway Lambda proxy response.
    """

    if isinstance(body, (dict, list)):
        body_str = json.dumps(body, cls=_RedshiftEncoder)
    else:
        body_str = body

    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
        "body": body_str,
    }
