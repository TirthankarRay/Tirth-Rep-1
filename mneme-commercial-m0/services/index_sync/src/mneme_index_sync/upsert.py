"""Upsert parsed files + chunks + edges into Postgres."""

from __future__ import annotations

import json
from typing import Iterable

import asyncpg

from .chunker import Chunk
from .parser import ParsedFile


def _vec_literal(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


async def upsert_file(
    conn: asyncpg.Connection,
    parsed: ParsedFile,
    last_commit: str,
    chunks: list[Chunk],
    embeddings: list[list[float]],
) -> None:
    async with conn.transaction():
        await conn.execute(
            """
            INSERT INTO files (id, path, type, title, frontmatter, body, last_commit, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
            ON CONFLICT (id) DO UPDATE SET
                path = EXCLUDED.path,
                type = EXCLUDED.type,
                title = EXCLUDED.title,
                frontmatter = EXCLUDED.frontmatter,
                body = EXCLUDED.body,
                last_commit = EXCLUDED.last_commit,
                updated_at = NOW()
            """,
            parsed.id, parsed.path, parsed.type, parsed.title,
            json.dumps(parsed.frontmatter, default=str),
            parsed.body, last_commit,
        )
        # Replace chunks atomically
        await conn.execute("DELETE FROM chunks WHERE file_id = $1", parsed.id)
        if chunks:
            await conn.executemany(
                """
                INSERT INTO chunks (file_id, section_path, body, embedding, section_meta)
                VALUES ($1, $2, $3, $4::vector, $5)
                """,
                [
                    (
                        parsed.id,
                        c.section_path,
                        c.body,
                        _vec_literal(e),
                        json.dumps({"section_path": c.section_path}),
                    )
                    for c, e in zip(chunks, embeddings)
                ],
            )
        # Rebuild entity edges from frontmatter.entities
        await conn.execute(
            "DELETE FROM edges WHERE src_id = $1 AND edge_type = 'entity'",
            parsed.id,
        )
        entities = parsed.frontmatter.get("entities") or {}
        if isinstance(entities, dict):
            edges = []
            for kind, values in entities.items():
                if not isinstance(values, (list, tuple)):
                    continue
                for v in values:
                    edges.append((parsed.id, f"entity:{kind}:{v}", "entity"))
            if edges:
                await conn.executemany(
                    """
                    INSERT INTO edges (src_id, dst_id, edge_type) VALUES ($1, $2, $3)
                    ON CONFLICT DO NOTHING
                    """,
                    edges,
                )


async def delete_file(conn: asyncpg.Connection, file_id: str) -> None:
    await conn.execute("DELETE FROM files WHERE id = $1", file_id)
    # chunks + edges cascade or get cleaned by FK and edge upsert paths
    await conn.execute("DELETE FROM edges WHERE src_id = $1", file_id)
