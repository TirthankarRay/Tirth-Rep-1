"""One-shot full rebuild: walk every tracked .md in the vault, re-parse,
re-chunk, re-embed, re-upsert. Run after `make seed` and any time the
indices look stale.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from .chunker import chunk_body
from .db import connect
from .embedder import embed
from .git_client import get_repo, head_sha, list_tracked_md, last_commit_for_path
from .parser import parse_file
from .upsert import upsert_file


async def rebuild() -> int:
    vault_path = Path(os.environ.get("VAULT_PATH", "/vault"))
    repo = get_repo(vault_path)
    head = head_sha(repo)
    print(f"Rebuilding indices from vault HEAD {head[:8]}...")

    conn = await connect()
    try:
        # Wipe and rebuild
        await conn.execute("DELETE FROM files")  # cascades chunks; edges separate
        await conn.execute("DELETE FROM edges WHERE edge_type IN ('entity','related','wikilink')")

        paths = list_tracked_md(repo)
        print(f"Found {len(paths)} tracked .md files")

        for rel_path in paths:
            parsed = parse_file(vault_path, rel_path)
            chunks = chunk_body(parsed.body)
            embeddings = embed(c.body for c in chunks)
            last_commit = last_commit_for_path(repo, rel_path)
            await upsert_file(conn, parsed, last_commit, chunks, embeddings)
            print(f"  + {parsed.id} ({len(chunks)} chunks)")

        # Stats
        file_count = await conn.fetchval("SELECT count(*) FROM files")
        chunk_count = await conn.fetchval("SELECT count(*) FROM chunks")
        edge_count = await conn.fetchval("SELECT count(*) FROM edges")
        print(f"Done. files={file_count} chunks={chunk_count} edges={edge_count}")
    finally:
        await conn.close()
    return 0


def main() -> int:
    return asyncio.run(rebuild())


if __name__ == "__main__":
    sys.exit(main())
