CREATE EXTENSION IF NOT EXISTS vector;

-- One row per knowledge file
CREATE TABLE IF NOT EXISTS files (
    id            TEXT PRIMARY KEY,
    path          TEXT NOT NULL,
    type          TEXT NOT NULL,
    title         TEXT NOT NULL,
    frontmatter   JSONB NOT NULL,
    body          TEXT NOT NULL,
    last_commit   TEXT NOT NULL,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS files_type_idx ON files(type);
CREATE INDEX IF NOT EXISTS files_frontmatter_gin ON files USING GIN (frontmatter);

-- One row per chunk (heading-boundary section)
CREATE TABLE IF NOT EXISTS chunks (
    id            BIGSERIAL PRIMARY KEY,
    file_id       TEXT NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    section_path  TEXT NOT NULL,
    body          TEXT NOT NULL,
    body_tsv      TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', body)) STORED,
    embedding     vector(384),
    section_meta  JSONB
);
CREATE INDEX IF NOT EXISTS chunks_tsv_idx ON chunks USING GIN (body_tsv);
-- ivfflat needs data before training; create it but it'll be a small index until populated
CREATE INDEX IF NOT EXISTS chunks_embedding_idx
    ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Graph edges
CREATE TABLE IF NOT EXISTS edges (
    src_id     TEXT NOT NULL,
    dst_id     TEXT NOT NULL,
    edge_type  TEXT NOT NULL,
    PRIMARY KEY (src_id, dst_id, edge_type)
);

-- Proposals
CREATE TABLE IF NOT EXISTS proposals (
    id              TEXT PRIMARY KEY,
    branch          TEXT NOT NULL,
    target_id       TEXT,
    target_path     TEXT,
    agent_id        TEXT NOT NULL,
    rationale       TEXT NOT NULL,
    verdict_label   TEXT NOT NULL,
    verdict_rule    TEXT NOT NULL,
    verdict_trace   JSONB NOT NULL,
    diff            JSONB NOT NULL DEFAULT '[]'::jsonb,
    sources         JSONB NOT NULL DEFAULT '[]'::jsonb,
    state           TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decided_at      TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS proposals_state_idx ON proposals(state);

-- Reviewer queue
CREATE TABLE IF NOT EXISTS review_queue (
    proposal_id   TEXT REFERENCES proposals(id) ON DELETE CASCADE,
    reviewer_role TEXT NOT NULL,
    signed_off    BOOLEAN NOT NULL DEFAULT FALSE,
    signed_by     TEXT,
    signed_at     TIMESTAMPTZ,
    comment       TEXT,
    PRIMARY KEY (proposal_id, reviewer_role)
);

-- Audit (M0: plain append-only)
CREATE TABLE IF NOT EXISTS audit_events (
    id          BIGSERIAL PRIMARY KEY,
    event_type  TEXT NOT NULL,
    subject     TEXT NOT NULL,
    target      TEXT,
    metadata    JSONB,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS audit_events_type_idx ON audit_events(event_type);
CREATE INDEX IF NOT EXISTS audit_events_subject_idx ON audit_events(subject);
