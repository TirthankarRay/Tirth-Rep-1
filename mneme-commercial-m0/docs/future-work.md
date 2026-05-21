# Future work — what M0 deferred

Per spec §12, the following are explicitly NOT in M0. Each is tagged with
its target milestone.

## M1 — Curation engine

- Six curation agents (M0 ships only the validator agent):
  - **Provenance agent** — links every claim to a source on ingest, flags
    drift when source changes.
  - **Staleness agent** — surfaces files past `review_cycle`.
  - **Contradiction agent** — populates `Proposal.contradictions` upstream
    of the classifier (M0 leaves the field empty).
  - **Synthesis agent** — collapses duplicate insights from multiple
    insights/* files.
  - **Coverage agent** — flags missing entities, missing types per
    domain area.
  - **Ingestion agent** — pulls from external sources (Veeva, IQVIA…)
    *not in scope until M2 source connectors land*.
- Section-level ABAC redaction (M0 has file-level classification gate only).
- Reviewer-thread comments + @mention notifications.

## M2 — Source connectors

- Veeva CRM (MSL notes, sales-rep call notes).
- IQVIA Xponent / DDD data.
- Payer-bulletin RSS / scraping.
- Internal SharePoint / Confluence ingest with provenance lineage.

## M3 — Governance hardening

- OAuth 2.1 + OIDC SSO (M0 uses trusted `X-Mneme-User` header).
- SCIM / Okta for identity/role provisioning.
- Hash-chained audit log with periodic notarization (M0 = plain Postgres table).
- WORM / object-lock storage for the audit + the vault tarballs.
- Part 11 e-signature workflow (the M0 sign-off is functional, not Part-11).
- Residency cells: one vault per region with cell-local indices, cross-cell
  read federation.

## M4 — Production observability + scale

- OpenTelemetry tracing across all services.
- Prometheus + Grafana dashboards (queue depth, SLA breach rate, integrity,
  classifier verdict distribution).
- HNSW vector index for ≥1M chunks per tenant; option to migrate to a
  dedicated vector store if measured.
- pre-receive git hook on the vault repo to block direct pushes.
- Multi-vault tenancy + cross-tenant guards.
- k8s / Helm / Terraform for managed deployment.

## Already deferred decisions logged in M0

See `docs/decisions-made.md` D1–D7.
