"""Hybrid retrieval = BM25 (tsvector) + cosine (pgvector), fused by RRF.

Pure DB-side: both lanes are SQL queries, fused in Python with the standard
reciprocal-rank-fusion score (1 / (k + rank)). Filters (type, entities,
updated_after) flow into both lanes identically.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

import asyncpg

from mneme_index_sync.embedder import embed


RRF_K = 60  # standard RRF constant


@dataclass
class SearchHit:
    file_id: str
    path: str
    type: str
    title: str
    section_path: str
    snippet: str
    score: float
    frontmatter: dict[str, Any]


def _vec_literal(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


def _build_filter_clause(filters: dict[str, Any] | None) -> tuple[str, list[Any]]:
    """Return (extra WHERE clause, params) used inside both lanes' queries.
    Both lanes reference `f.frontmatter` and `f.type`/`f.updated_at`.
    """
    if not filters:
        return "", []
    clauses: list[str] = []
    params: list[Any] = []
    if "type" in filters and filters["type"]:
        params.append(filters["type"])
        clauses.append(f"f.type = ${len(params)}")
    if "classification" in filters and filters["classification"]:
        params.append(filters["classification"])
        clauses.append(f"f.frontmatter->>'classification' = ${len(params)}")
    if "updated_after" in filters and filters["updated_after"]:
        params.append(filters["updated_after"])
        clauses.append(f"f.updated_at > ${len(params)}::timestamptz")
    if "entities" in filters and filters["entities"]:
        # entities filter: {brand: ["brandx"], indication: ["nsclc"]} — any-of match
        ent = filters["entities"]
        if isinstance(ent, dict):
            for kind, vals in ent.items():
                if not vals:
                    continue
                params.append(json.dumps({kind: list(vals)}))
                clauses.append(f"f.frontmatter->'entities' @> ${len(params)}::jsonb")
    where = (" AND " + " AND ".join(clauses)) if clauses else ""
    return where, params


async def search(
    conn: asyncpg.Connection,
    query: str,
    filters: dict[str, Any] | None = None,
    mode: Literal["hybrid", "semantic", "lexical"] = "hybrid",
    top_k: int = 10,
) -> list[SearchHit]:
    extra_where, extra_params = _build_filter_clause(filters)

    lexical: list[asyncpg.Record] = []
    semantic: list[asyncpg.Record] = []

    if mode in ("hybrid", "lexical"):
        lexical_sql = f"""
        SELECT c.id AS chunk_id, c.file_id, c.section_path, c.body,
               f.path, f.type, f.title, f.frontmatter,
               ts_rank_cd(c.body_tsv, plainto_tsquery('english', $1)) AS rank
        FROM chunks c
        JOIN files f ON f.id = c.file_id
        WHERE c.body_tsv @@ plainto_tsquery('english', $1)
              {extra_where}
        ORDER BY rank DESC
        LIMIT $2
        """
        lex_limit = max(top_k * 4, 20)
        lexical = await conn.fetch(lexical_sql, query, lex_limit, *extra_params)

    if mode in ("hybrid", "semantic"):
        emb = embed([query])[0]
        sem_limit = max(top_k * 4, 20)
        sem_params = [_vec_literal(emb), sem_limit, *extra_params]
        semantic_sql = f"""
        SELECT c.id AS chunk_id, c.file_id, c.section_path, c.body,
               f.path, f.type, f.title, f.frontmatter,
               (c.embedding <=> $1::vector) AS distance
        FROM chunks c
        JOIN files f ON f.id = c.file_id
        WHERE c.embedding IS NOT NULL
              {extra_where}
        ORDER BY c.embedding <=> $1::vector
        LIMIT $2
        """
        semantic = await conn.fetch(semantic_sql, *sem_params)

    # RRF fusion (or single-lane pass-through)
    if mode == "lexical":
        ranked = list(lexical)
    elif mode == "semantic":
        ranked = list(semantic)
    else:
        ranked = _rrf_merge(lexical, semantic)

    hits: list[SearchHit] = []
    seen_chunks: set[int] = set()
    for r in ranked:
        if r["chunk_id"] in seen_chunks:
            continue
        seen_chunks.add(r["chunk_id"])
        snippet = r["body"]
        if len(snippet) > 280:
            snippet = snippet[:277] + "..."
        fm = r["frontmatter"]
        if isinstance(fm, str):
            fm = json.loads(fm)
        hits.append(SearchHit(
            file_id=r["file_id"],
            path=r["path"],
            type=r["type"],
            title=r["title"],
            section_path=r["section_path"],
            snippet=snippet,
            score=float(r.get("_rrf", r.get("rank") or (1.0 - (r.get("distance") or 0.0)))),
            frontmatter=fm,
        ))
        if len(hits) >= top_k:
            break
    return hits


def _rrf_merge(
    lexical: list[asyncpg.Record],
    semantic: list[asyncpg.Record],
) -> list[dict[str, Any]]:
    scores: dict[int, dict[str, Any]] = {}
    for rank, rec in enumerate(lexical):
        cid = rec["chunk_id"]
        scores.setdefault(cid, dict(rec)).setdefault("_rrf", 0.0)
        scores[cid]["_rrf"] += 1.0 / (RRF_K + rank + 1)
    for rank, rec in enumerate(semantic):
        cid = rec["chunk_id"]
        scores.setdefault(cid, dict(rec)).setdefault("_rrf", 0.0)
        scores[cid]["_rrf"] += 1.0 / (RRF_K + rank + 1)
    return sorted(scores.values(), key=lambda r: r["_rrf"], reverse=True)
