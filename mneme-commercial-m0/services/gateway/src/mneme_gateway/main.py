"""Mneme gateway entry point.

Hosts:
  - The MCP server (streamable-HTTP transport)
  - A small JSON shim under /mcp/* so the demo runner and console can call
    the same tools without an MCP client library
  - /healthz for the compose healthcheck

The trusted-header SSO simulation reads `X-Mneme-User` on every request.
"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from . import migrate
from .auth import parse_user_header
from .db import close_pool, get_pool
from .identity import resolve
from .tools.search import search as t_search
from .tools.read import read as t_read
from .tools.list import list_files as t_list
from .tools.related import related as t_related
from .tools.history import history as t_history
from .tools.propose_edit import propose_edit as t_propose_edit
from .tools.proposal_status import proposal_status as t_proposal_status


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Apply migrations idempotently
    try:
        await migrate.run()
    except Exception as e:
        print(f"warn: migration failed (will retry on next start): {e}")
    await get_pool()
    yield
    await close_pool()


app = FastAPI(title="mneme-gateway", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _identity(user_header: str | None):
    return resolve(parse_user_header(user_header))


@app.get("/healthz")
async def healthz():
    return {"ok": True}


# === MCP-style JSON endpoints (a thin shim so the demo + console can drive
# === the same tools without spinning up a full MCP client). The actual MCP
# === server registers these same tools below.

class SearchBody(BaseModel):
    query: str
    filters: dict[str, Any] | None = None
    mode: str = "hybrid"
    top_k: int = 10


@app.post("/mcp/vault.search")
async def http_search(body: SearchBody, x_mneme_user: str | None = Header(default=None)):
    ident = _identity(x_mneme_user)
    return await t_search(ident, body.query, body.filters, body.mode, body.top_k)


class ReadBody(BaseModel):
    id: str
    sections: list[str] | None = None
    include: list[str] | None = None


@app.post("/mcp/vault.read")
async def http_read(body: ReadBody, x_mneme_user: str | None = Header(default=None)):
    ident = _identity(x_mneme_user)
    return await t_read(ident, body.id, body.sections, body.include)


class ListBody(BaseModel):
    domain: str | None = None
    type: str | None = None
    filters: dict[str, Any] | None = None


@app.post("/mcp/vault.list")
async def http_list(body: ListBody, x_mneme_user: str | None = Header(default=None)):
    ident = _identity(x_mneme_user)
    return await t_list(ident, body.domain, body.type, body.filters)


class RelatedBody(BaseModel):
    id: str
    depth: int = 1
    edge_types: list[str] | None = None


@app.post("/mcp/vault.related")
async def http_related(body: RelatedBody, x_mneme_user: str | None = Header(default=None)):
    ident = _identity(x_mneme_user)
    return await t_related(ident, body.id, body.depth, body.edge_types)


class HistoryBody(BaseModel):
    id: str
    section: str | None = None
    since: str | None = None


@app.post("/mcp/vault.history")
async def http_history(body: HistoryBody, x_mneme_user: str | None = Header(default=None)):
    ident = _identity(x_mneme_user)
    return await t_history(ident, body.id, body.section, body.since)


class ProposeBody(BaseModel):
    id: str | None = None
    new_type: str | None = None
    new_path: str | None = None
    change: dict[str, Any]
    rationale: str
    sources: list[dict[str, Any]] = []
    agent_quality_score: float = 0.95


@app.post("/mcp/vault.propose_edit")
async def http_propose(body: ProposeBody, x_mneme_user: str | None = Header(default=None)):
    ident = _identity(x_mneme_user)
    return await t_propose_edit(
        ident,
        id=body.id,
        new_type=body.new_type,
        new_path=body.new_path,
        change=body.change,
        rationale=body.rationale,
        sources=body.sources,
        agent_quality_score=body.agent_quality_score,
    )


class StatusBody(BaseModel):
    proposal_id: str


@app.post("/mcp/vault.proposal_status")
async def http_status(body: StatusBody, x_mneme_user: str | None = Header(default=None)):
    ident = _identity(x_mneme_user)
    return await t_proposal_status(ident, body.proposal_id)


# === MCP server (streamable-HTTP). Tools wrap the same handlers.
# === In M0 we mount it at /sse via the SDK helper; clients that prefer
# === the JSON shim above can use those routes instead.

def _mount_mcp(app: FastAPI) -> None:
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception as e:
        print(f"warn: MCP SDK not available, JSON shim only: {e}")
        return

    mcp = FastMCP("mneme-gateway")

    @mcp.tool(name="vault.search", description="Hybrid retrieval across the vault.")
    async def mcp_search(query: str, filters: dict | None = None,
                         mode: str = "hybrid", top_k: int = 10):
        # MCP tool calls don't carry per-request headers; the gateway runs as
        # one identity from MCP_USER env, demo runner uses the JSON shim.
        ident = _identity(os.environ.get("MCP_DEFAULT_USER", "u:brand-lead-brandx"))
        return await t_search(ident, query, filters, mode, top_k)

    @mcp.tool(name="vault.read", description="Read a vault file with optional sections / includes.")
    async def mcp_read(id: str, sections: list[str] | None = None,
                       include: list[str] | None = None):
        ident = _identity(os.environ.get("MCP_DEFAULT_USER", "u:brand-lead-brandx"))
        return await t_read(ident, id, sections, include)

    @mcp.tool(name="vault.list", description="List vault frontmatter records.")
    async def mcp_list(domain: str | None = None, type: str | None = None,
                       filters: dict | None = None):
        ident = _identity(os.environ.get("MCP_DEFAULT_USER", "u:brand-lead-brandx"))
        return await t_list(ident, domain, type, filters)

    @mcp.tool(name="vault.related", description="Walk graph edges from a file.")
    async def mcp_related(id: str, depth: int = 1, edge_types: list[str] | None = None):
        ident = _identity(os.environ.get("MCP_DEFAULT_USER", "u:brand-lead-brandx"))
        return await t_related(ident, id, depth, edge_types)

    @mcp.tool(name="vault.history", description="Git history for a file.")
    async def mcp_history(id: str, section: str | None = None, since: str | None = None):
        ident = _identity(os.environ.get("MCP_DEFAULT_USER", "u:brand-lead-brandx"))
        return await t_history(ident, id, section, since)

    @mcp.tool(name="vault.propose_edit", description="Open a proposal branch + classify + route.")
    async def mcp_propose(id: str | None = None, new_type: str | None = None,
                          new_path: str | None = None, change: dict = None,
                          rationale: str = "", sources: list[dict] = None,
                          agent_quality_score: float = 0.95):
        ident = _identity(os.environ.get("MCP_DEFAULT_USER", "u:brand-lead-brandx"))
        return await t_propose_edit(
            ident, id=id, new_type=new_type, new_path=new_path,
            change=change or {}, rationale=rationale, sources=sources or [],
            agent_quality_score=agent_quality_score,
        )

    @mcp.tool(name="vault.proposal_status", description="Read state of a proposal.")
    async def mcp_status(proposal_id: str):
        ident = _identity(os.environ.get("MCP_DEFAULT_USER", "u:brand-lead-brandx"))
        return await t_proposal_status(ident, proposal_id)

    # Mount streamable-HTTP transport. The path is `/mcp`.
    try:
        sub = mcp.streamable_http_app()
        app.mount("/mcp-sdk", sub)
    except Exception as e:
        print(f"warn: streamable HTTP transport not mountable: {e}")


_mount_mcp(app)


def main() -> None:
    host = os.environ.get("GATEWAY_HOST", "0.0.0.0")
    port = int(os.environ.get("GATEWAY_PORT", "8001"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
