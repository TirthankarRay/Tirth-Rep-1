# Mneme M0 — Architecture overview

```
                                      ┌─────────────────────────────────────┐
                                      │   apps/console (React 19 + TS)      │
                                      │    Queue · Proposal · Audit         │
                                      │    :5173 — React state only         │
                                      └────────────────┬────────────────────┘
                                                       │ HTTP/JSON
                                                       ▼
                                      ┌─────────────────────────────────────┐
                                      │   services/console_api (FastAPI)    │
                                      │    /api/queue · /api/proposals/…    │
                                      │    /api/signoff · /api/audit  :8002 │
                                      └────────────────┬────────────────────┘
                                                       │
   ┌───────────────────────────┐                       │
   │   agents                  │                       │  asyncpg
   │   (live demo + headless)  │                       │
   └─────────────┬─────────────┘                       │
                 │ MCP / HTTP + X-Mneme-User           │
                 ▼                                     │
   ┌─────────────────────────────────────┐             │
   │   services/gateway (FastMCP/HTTP)   │             │
   │   vault.search · read · list ·      │             │
   │   related · history · propose_edit  │─────────────┤
   │   · proposal_status            :8001│             │
   └─────┬──────────────────────┬────────┘             │
         │ git                  │ asyncpg              │
         ▼                      ▼                      ▼
   ┌──────────────┐    ┌──────────────────────────────────────┐
   │ vault/       │    │  postgres 16 + pgvector  :5432       │
   │ (real .git)  │    │  files · chunks · edges              │
   │ branch       │    │  proposals · review_queue · audit    │
   │  proposal/.. │    └──────────────────────────────────────┘
   │ main         │             ▲
   └─────┬────────┘             │
         │                      │
         │  POST /sync          │  upsert
         ▼                      │
   ┌─────────────────────────────────────┐
   │   services/index_sync (FastAPI)     │
   │   /rebuild · /sync           :8003  │
   │   parse → chunk → embed             │
   │   (sentence-transformers, local)    │
   └─────────────────────────────────────┘
```

## Components

- **vault** — a real git repo. Markdown files with YAML frontmatter. Files are
  truth; the .git directory is initialized at first `make seed`.
- **manifest** — JSON Schemas, templates, ontology CSVs, and the YAML rule pack.
  Source of *configuration* truth.
- **services/gateway** — the MCP gateway. Seven tools; trusted-header SSO; runs
  the validator + classifier inline on `vault.propose_edit`.
- **services/index_sync** — git → Postgres worker. Heading-boundary chunker,
  local MiniLM embedder, transactional upsert.
- **services/validator** — schema/source/entity checks, plus the
  merge-after-signoff router invoked by console-api when the last co-signer
  signs off.
- **services/console_api** — JSON backend for the React console.
- **apps/console** — React 19 + Tailwind reviewer console; React state only,
  no browser storage.
- **libs/classifier** — pure-rule materiality engine (R1–R10). The most
  important code in the system.
- **libs/schemas** — JSON Schema loader with cross-file `$ref` registry.
- **demo** — six simulated agents, three modes, integrity scoring.

## Read path

1. Agent calls `vault.search(query)` via MCP.
2. Gateway runs hybrid retrieval (BM25 tsvector + cosine pgvector), fuses with RRF.
3. Returns chunk snippets with file metadata, classification-gated.

## Write path

1. Agent calls `vault.propose_edit(id, change, rationale, sources)`.
2. Gateway opens branch `proposal/<agent>/<yyyymmdd-NNN>`, applies patch,
   commits with agent's identity.
3. Validator runs schema_check + source_check.
4. Classifier evaluates rules R1..R10, returns `Verdict(label, rule, co_sign, route, trace)`.
5. Router:
   - reject → leave branch, return reasons
   - routine / attention → merge to main, fire `/sync` to index-sync
   - material → leave on branch, write rows to `review_queue`
6. `proposals` + `audit_events` rows persisted.
7. On co-sign completion, console-api → `mneme_validator.router.merge_proposal` →
   `git merge` + `/sync`.
