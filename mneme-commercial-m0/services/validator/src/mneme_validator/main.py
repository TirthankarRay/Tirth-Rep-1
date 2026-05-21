"""Validator service HTTP entry (library-only at M0).

The gateway invokes the validator inline (schema_check, source_check,
classifier) so this process exists primarily as a library deployment
target. We still bind a small FastAPI app so docker-compose can health-check
it; the only meaningful endpoints are /healthz and /resolve.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

from .entity_resolve import resolve as do_resolve
from .schema_check import check as do_schema
from .source_check import check as do_source


app = FastAPI(title="mneme-validator")


@app.get("/healthz")
async def healthz():
    return {"ok": True}


class ResolveBody(BaseModel):
    frontmatter: dict


@app.post("/resolve")
async def resolve(body: ResolveBody):
    return {
        "warnings": do_resolve(body.frontmatter),
    }


class ValidateBody(BaseModel):
    type: str
    frontmatter: dict
    body: str = ""


@app.post("/validate")
async def validate(body: ValidateBody):
    return {
        "schema_errors": do_schema(body.type, body.frontmatter),
        "source_errors": do_source(body.frontmatter, body.body),
        "entity_warnings": do_resolve(body.frontmatter),
    }


def main() -> None:
    host = os.environ.get("VALIDATOR_HOST", "0.0.0.0")
    port = int(os.environ.get("VALIDATOR_PORT", "8004"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
