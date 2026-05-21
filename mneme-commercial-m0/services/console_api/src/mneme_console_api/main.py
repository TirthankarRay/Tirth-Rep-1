"""Console API entry."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from . import queue as queue_mod
from . import proposal as proposal_mod
from . import signoff as signoff_mod
from . import audit as audit_mod
from .db import close_pool, get_pool


@asynccontextmanager
async def lifespan(_: FastAPI):
    await get_pool()
    yield
    await close_pool()


app = FastAPI(title="mneme-console-api", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _user(value: str | None) -> str:
    v = (value or "u:anonymous").strip()
    if not v.startswith("u:"):
        v = f"u:{v}"
    return v


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.get("/api/queue")
async def get_queue(role: str | None = None):
    return await queue_mod.list_open(role)


@app.get("/api/proposals/{proposal_id}")
async def get_proposal(proposal_id: str):
    return await proposal_mod.get_detail(proposal_id)


class SignOffBody(BaseModel):
    role: str
    comment: str | None = None


@app.post("/api/proposals/{proposal_id}/signoff")
async def post_signoff(
    proposal_id: str,
    body: SignOffBody,
    x_mneme_user: str | None = Header(default=None),
):
    return await signoff_mod.sign_off(proposal_id, body.role, _user(x_mneme_user), body.comment)


class RejectBody(BaseModel):
    role: str
    comment: str


@app.post("/api/proposals/{proposal_id}/reject")
async def post_reject(
    proposal_id: str,
    body: RejectBody,
    x_mneme_user: str | None = Header(default=None),
):
    return await signoff_mod.reject(proposal_id, body.role, _user(x_mneme_user), body.comment)


@app.get("/api/audit")
async def get_audit(event_type: str | None = None, subject: str | None = None, limit: int = 200):
    return await audit_mod.list_events(event_type, subject, limit)


def main() -> None:
    host = os.environ.get("CONSOLE_API_HOST", "0.0.0.0")
    port = int(os.environ.get("CONSOLE_API_PORT", "8002"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
