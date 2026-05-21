# Mneme — pharma commercial knowledge vault (M0)

An enterprise agent knowledge vault: a git-backed markdown vault, indexed into
Postgres (metadata + tsvector + pgvector + graph), exposed via MCP, with every
write opening a proposal that a pure-Python rule classifier routes to
auto-merge, attention, or co-sign review.

## Architecture at a glance

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
   │   agents (MCP clients)    │                       │  asyncpg
   └─────────────┬─────────────┘                       │
                 │ MCP / HTTP + X-Mneme-User           │
                 ▼                                     │
   ┌─────────────────────────────────────┐             │
   │   services/gateway (FastMCP+HTTP)   │             │
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
         │  POST /sync          │  upsert
         ▼                      │
   ┌─────────────────────────────────────┐
   │   services/index_sync (FastAPI)     │
   │   /rebuild · /sync           :8003  │
   │   parse → chunk → embed             │
   │   (sentence-transformers, local)    │
   └─────────────────────────────────────┘
```

## Quick start

```bash
cd mneme-commercial-m0
cp .env.example .env

make up        # builds + starts postgres, gateway, index-sync, console-api, console
make seed      # validates 21 seed files, git-inits the vault, rebuilds indices
make demo      # runs the three-mode comparison + 12 live proposals into the gateway
```

Open **`http://localhost:5173/queue`** for the reviewer console. Switch identity
via the sidebar to play each role; sign off the proposals the demo created.

## What this is

- **Three repos**: vault (markdown), manifest (schemas/templates/ontology/rules),
  monorepo (services + apps + libs).
- **Four services**: gateway (MCP), index-sync (git→Postgres), console-api
  (JSON for the React app), validator (schema/source/entity + merge worker).
- **Four indices in one Postgres**: metadata, full-text (tsvector), vector
  (pgvector 384-dim MiniLM), graph (entity edges).
- **The classifier** is a pure Python function over a structured Proposal;
  10 rules, every evaluation traced. See `libs/classifier/`.

## Demo script

The 12-minute narrative for the CTO + pharma-CIO meeting lives in
[`docs/demo-script.md`](./docs/demo-script.md).

## Architecture decisions

Each is one page; read these first.

- [ADR-001 — Files are truth, the database is a derived index](./docs/adr/001-files-as-truth.md)
- [ADR-002 — Materiality classifier is pure rules, not an LLM](./docs/adr/002-pure-rule-classifier.md)
- [ADR-003 — Postgres-first for all derived indices](./docs/adr/003-postgres-first.md)
- [ADR-004 — Every write is a proposal, never a direct commit](./docs/adr/004-no-llm-in-critical-path.md)

## What this is not

Section-level redaction, OAuth, hash-chained audit, the other five curation
agents, real source connectors, persona/episodic memory — all explicitly
deferred. See [`docs/future-work.md`](./docs/future-work.md) for the milestone
each belongs to. Decisions made along the way are in
[`docs/decisions-made.md`](./docs/decisions-made.md).

## Repository layout

```
mneme-commercial-m0/
├── README.md, Makefile, docker-compose.yml, .env.example
├── vault/                     # the markdown vault — files are truth
├── manifest/                  # schemas, templates, ontology, rule packs
├── services/
│   ├── gateway/               # MCP server :8001 (7 tools + write lifecycle)
│   ├── index_sync/            # git → Postgres :8003
│   ├── validator/             # schema/source checks + merge-after-signoff
│   └── console_api/           # JSON backend for the React console :8002
├── libs/
│   ├── classifier/            # pure-rule materiality engine (R1..R10)
│   └── schemas/               # JSON Schema loader
├── apps/console/              # React 19 + Tailwind reviewer console :5173
├── demo/                      # 6 agents × 3 modes runner + seed loader
├── deploy/docker/             # Dockerfiles, postgres-init.sql
└── docs/                      # ADRs, runbook, demo script, future work
```

## Tests

```bash
make classifier-test    # 19 classifier unit tests, no Docker needed
make test               # full test suite inside the gateway container
```

## Contributing

Edit a markdown file under `vault/`. Validation runs on `make seed`. If your
edits don't validate, the seed script prints per-file errors.

For service changes, the source folders are bind-mounted into the containers
(see compose file); `docker compose restart <service>` picks up Python edits.
The React console hot-reloads via Vite.

## Operations

- Runbook: [`docs/runbook.md`](./docs/runbook.md) — common commands, health
  checks, troubleshooting.
- Architecture overview: [`docs/architecture.md`](./docs/architecture.md).
