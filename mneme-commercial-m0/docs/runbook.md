# Runbook

## First run

```bash
cd mneme-commercial-m0
cp .env.example .env       # tweak if you want to change ports
make up                    # builds images, brings postgres + 4 services up
make seed                  # validates 21 seed files, git-inits vault, builds indices
make demo                  # runs the headline 3-mode demo
```

Open `http://localhost:5173/queue` to see the reviewer console.

## Common operations

| Need to...                 | Do this                                         |
|----------------------------|-------------------------------------------------|
| Reset everything           | `make reset` (drops DB, recreates vault)        |
| See live logs              | `make logs` (or `docker compose logs -f gateway`)|
| Re-run just the demo       | `make demo`                                     |
| Re-validate seed schemas   | `docker compose exec gateway python -m mneme_demo.seed.seed_vault` |
| Re-build vector index      | `docker compose exec index-sync python -m mneme_index_sync.rebuild` |
| Run unit tests             | `make test`                                     |

## Health checks

- Gateway:     `curl -s http://localhost:8001/healthz`
- Console API: `curl -s http://localhost:8002/healthz`
- Index sync:  `curl -s http://localhost:8003/healthz`

## Direct MCP-shim calls

The gateway exposes both a FastMCP transport (`/mcp-sdk`) and a JSON shim
(`/mcp/<tool>`). For quick agent-style calls:

```bash
curl -s -X POST http://localhost:8001/mcp/vault.search \
  -H 'Content-Type: application/json' \
  -H 'X-Mneme-User: u:brand-lead-brandx' \
  -d '{"query":"BrandX nsclc competitive","top_k":5}' | jq
```

```bash
curl -s -X POST http://localhost:8001/mcp/vault.propose_edit \
  -H 'Content-Type: application/json' \
  -H 'X-Mneme-User: agent:diligent-1' \
  -d '{
    "id":"kb-brandx-vs-brandy-nsclc",
    "change":{"sections":[{"path":"Commercial Implications",
                            "patch":"Added new payer pull-through note from May 2026."}]},
    "rationale":"Reinforce Anthem step-edit playbook.",
    "sources":[{"ref":"https://example.local/may-2026-payer-note","kind":"internal"}]
  }' | jq
```

## Troubleshooting

- **`docker compose up` hangs on console**: first run does `npm install` inside
  the container; takes ~60s. Subsequent runs are fast.
- **`make seed` says schema errors**: check your edits to vault files; run
  `python -m mneme_demo.seed.seed_vault` directly to see line-level diagnostics.
- **Search returns nothing**: rerun `docker compose exec index-sync python -m mneme_index_sync.rebuild`.
- **Proposal stuck in `needs_review`**: open the console as the role from the
  proposal's `co_sign` list, sign off; the merge happens on the last signoff.
