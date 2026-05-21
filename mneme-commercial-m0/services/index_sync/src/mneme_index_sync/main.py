"""Index-sync HTTP service.

Exposes:
  POST /rebuild       — synchronous full rebuild (returns counts)
  POST /sync          — re-sync a single file by repo-relative path
  GET  /healthz       — liveness

The gateway calls /sync after a merge so the new content is searchable
within seconds.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from .chunker import chunk_body
from .db import connect
from .embedder import embed
from .git_client import get_repo, head_sha, list_tracked_md, last_commit_for_path
from .parser import parse_file
from .upsert import upsert_file, delete_file


app = FastAPI(title="mneme-index-sync")


class SyncRequest(BaseModel):
    path: str


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.post("/rebuild")
async def http_rebuild():
    from .rebuild import rebuild
    code = await rebuild()
    return {"ok": code == 0}


@app.post("/sync")
async def http_sync(req: SyncRequest):
    vault_path = Path(os.environ.get("VAULT_PATH", "/vault"))
    repo = get_repo(vault_path)
    full = vault_path / req.path
    conn = await connect()
    try:
        if not full.exists():
            # Removed in the merge — delete from indices
            # Use the path-derived id if we can't open the file
            await conn.execute("DELETE FROM files WHERE path = $1", req.path)
            return {"ok": True, "action": "deleted", "path": req.path}
        parsed = parse_file(vault_path, req.path)
        chunks = chunk_body(parsed.body)
        embeddings = embed(c.body for c in chunks)
        last_commit = last_commit_for_path(repo, req.path)
        await upsert_file(conn, parsed, last_commit, chunks, embeddings)
        return {
            "ok": True,
            "action": "upserted",
            "id": parsed.id,
            "chunks": len(chunks),
        }
    finally:
        await conn.close()


def main() -> None:
    host = os.environ.get("INDEX_SYNC_HOST", "0.0.0.0")
    port = int(os.environ.get("INDEX_SYNC_PORT", "8003"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
