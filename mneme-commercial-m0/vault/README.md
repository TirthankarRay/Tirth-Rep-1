# BrandX commercial vault

This is a git-backed markdown vault. Files are truth. Every write goes through
a proposal branch. See `.mneme.yml` for vault-level config and `CODEOWNERS` for
reviewer routing.

## Layout

- `brand-strategy/` — positioning, plays, KPIs
- `competitive-landscape/` — vs-competitor analyses (MLR-sensitive)
- `payer-coverage/` — payer-specific coverage notes
- `hcp-segmentation/` — HCP segments and engagement
- `msl-insights/<quarter>/` — field intelligence
- `launch-milestones/` — gating events
- `pricing/` — list, GTN, rationale (restricted)
- `entities/` — canonical entity profiles (brands, molecules, indications, payers)

Indices in Postgres are derived from this tree. They rebuild from `git log`.
