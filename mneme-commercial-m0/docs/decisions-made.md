# Decisions made while building M0

A running log of judgment calls. The spec said to make decisions and keep moving
(§16); this file is where I record them.

## D1 — Git server: no GitLab/Gitea container

Spec offered either self-hosted GitLab or a Gitea sidecar for the vault repo.
**Chose neither**: the vault is a real git repo at `vault/`, bind-mounted into
the gateway and index-sync containers. Gateway shells out to `git` against
`/vault` directly. Justification: M0 must be laptop-runnable; an extra git
server adds 1–2GB of RAM, slower startup, and no demo value. The architecture
(files-as-truth, branch-per-proposal) is preserved exactly — just hosted on the
local filesystem.

## D2 — Python `requires-python` relaxed to >=3.11 for local dev

Spec mandates Python 3.12 (kept in Dockerfiles). Local dev box has 3.11, so
`pyproject.toml` files set `requires-python = ">=3.11"` to allow local
`pytest` runs without a container build. Production target remains 3.12.

## D3 — Single Console API process

Spec wants a "thin React console". The simplest realization is a dedicated
FastAPI process (`console_api/`, port 8002) so the React app speaks plain
JSON, leaving the gateway as MCP-only. No reverse proxy.

## D4 — Embedding model: lazy load + baked into image

`sentence-transformers/all-MiniLM-L6-v2` downloads on first use. The
Dockerfile pre-downloads it at build time so the first `make demo` doesn't
wait on a network round trip.

## D5 — Diff generation server-side via stdlib `difflib`

No third-party diff lib client- or server-side. Diff is computed when the
console API serves the proposal detail; the React component just renders
the before/after blocks.

## D6 — Rule pack YAML mirrors `rules.py`, doesn't drive it

`manifest/rule-packs/commercial-mlr-strict.yml` is for humans (CTO / compliance
review). The runtime rules live in `libs/classifier/src/mneme_classifier/rules.py`
because data-driven rules make the trace and unit tests harder. M1 can switch
to YAML-driven if a need arises.

## D7 — Demo mode timing: 10× sim clock, 60 sim-seconds per mode

Per spec §9. Three modes × 6 real seconds = 18 seconds for the headline demo
chart, plus setup/teardown. The single-seed-shared property is preserved by
seeding `random.Random` from a constant per run.
