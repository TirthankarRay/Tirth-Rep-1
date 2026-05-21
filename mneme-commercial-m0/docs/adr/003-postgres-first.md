# ADR-003 — Postgres-first for all derived indices

## Status

Accepted (M0).

## Context

We need four indices on top of the vault:

- **Metadata** — frontmatter as queryable structured data.
- **Full-text** — keyword retrieval over file bodies.
- **Vector** — semantic retrieval over chunk embeddings.
- **Graph** — entity edges between files.

A modern stack would default to four products: Postgres + Elasticsearch +
Pinecone (or pgvector) + Neo4j. Each adds an operator burden, a backup story,
and a cross-store consistency problem at merge time.

## Decision

All four indices live in one Postgres 16 instance with the pgvector extension.
- `files` — one row per file, frontmatter as JSONB.
- `chunks` — one row per heading-bounded chunk, `body_tsv` GENERATED column
  for full-text, `embedding vector(384)` for semantic.
- `edges` — `(src_id, dst_id, edge_type)` triples; cheap enough that walking
  depth-3 from a file is sub-millisecond at vault scale.
- `proposals`, `review_queue`, `audit_events` — operational state.

Hybrid retrieval is BM25 (tsvector) + cosine (pgvector) fused with reciprocal
rank fusion (k=60), all in SQL with a thin Python layer for fusion math.

## Consequences

**Wins.**

- One operator, one backup, one transactional boundary. A merge in the
  validator service can write to all four indices in the same transaction.
- pgvector is mature enough for vault-scale corpora (tens of thousands of
  chunks). We're not anywhere near the ceiling for M0–M2.
- A single connection pool. Predictable latency profile.

**Costs.**

- We will hit a scaling ceiling. At ~1M chunks per tenant the vector lane
  starts to feel the lack of HNSW (M0 uses ivfflat). The plan is to upgrade
  the index type, then add a dedicated vector store, then split full-text —
  in that order, each only when measured.
- pgvector's recall/latency tradeoff is good but not best-in-class. We
  accept this for M0; M3 evaluates the alternatives with real workload data.

## Alternatives considered

- **Elasticsearch + Pinecone + Neo4j + Postgres.** Rejected: four products
  for a problem that doesn't yet have four problems.
- **Postgres + dedicated vector store (Qdrant, Weaviate).** Rejected for M0;
  re-evaluate once we have a real corpus and real query mix.

## Related

- ADR-001: files as truth — indices are rebuildable from git.
- See `deploy/docker/postgres-init.sql` for the schema.
