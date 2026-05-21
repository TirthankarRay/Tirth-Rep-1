# Mneme M0 — 12-minute demo script

The audience is a CTO and a Fortune-50 pharma CIO. The artifact is the
running system + this repository. Everything below assumes
`make up && make seed && make demo` has run successfully.

---

## 0:00 – 1:30 · Why this exists

> Pharma commercial teams have knowledge problems no chatbot will solve.
> A brand lead, a market-access lead, an MSL, and a launch PM each carry
> different mental models of the same drug. When agents start writing
> back — and they will — the failure mode is silent contamination: a
> plausible-sounding wrong claim merges into a central document, agents
> read it as truth, and by the time someone notices it's been quoted in
> a regulatory submission.
>
> Mneme is the vault that makes that failure mode impossible. Files are
> truth. Every write is a proposal. Materiality is a transparent rule
> engine. Reviewers see a queue, not a haystack.

(Open the README's ASCII diagram. Point to the three repos and four indices.)

## 1:30 – 3:00 · The vault as a file

Open `vault/competitive-landscape/brandx-vs-brandy-nsclc.md` in an editor.

> This is what knowledge looks like. Markdown body, YAML frontmatter, real
> sources. A CTO can read it. A reviewer can diff it. A compliance officer
> can audit who changed what. There is no opaque database row here. The
> database does exist — for speed — but it's a derived index that we can
> rebuild from `git log --all` in minutes.

(Optional: `git -C vault log --oneline -10` to show the audit trail is git.)

## 3:00 – 5:00 · The seven MCP tools

> Agents speak to this vault through one contract: MCP. Seven tools.
> Read paths and one write path.

Demonstrate from a terminal:

```bash
curl -s -X POST http://localhost:8001/mcp/vault.search \
  -H 'X-Mneme-User: u:brand-lead-brandx' -H 'Content-Type: application/json' \
  -d '{"query":"BrandX nsclc competitive","top_k":3}' | jq '.results[].title'
```

> Hybrid retrieval — BM25 for exact terms, vector for semantic, fused with
> reciprocal rank fusion. Local embeddings, no external API.

```bash
curl -s -X POST http://localhost:8001/mcp/vault.read \
  -H 'X-Mneme-User: u:brand-lead-brandx' -H 'Content-Type: application/json' \
  -d '{"id":"kb-brandx-vs-brandy-nsclc","include":["provenance"]}' | jq '.title, .frontmatter.sources'
```

## 5:00 – 7:30 · The write path (the demo's centerpiece)

> Watch what happens when an agent tries to edit the competitive-landscape file.

```bash
curl -s -X POST http://localhost:8001/mcp/vault.propose_edit \
  -H 'X-Mneme-User: agent:diligent-1' -H 'Content-Type: application/json' \
  -d '{
    "id":"kb-brandx-vs-brandy-nsclc",
    "change":{"sections":[{"path":"Commercial Implications",
      "patch":"Updated May 2026: Anthem appeals success rate is improving."}]},
    "rationale":"Reflect Anthem appeals progress from market-access debrief.",
    "sources":[{"ref":"https://example.local/anthem-debrief-may2026","kind":"internal"}]
  }' | jq '.verdict, .state'
```

> Verdict: `material`, rule `R2-mlr-boundary`, co-sign list
> `["brand", "medical", "mlr"]`. The change is committed to a real branch.
> Main is untouched. The proposal is in the queue.

Switch to the browser, `http://localhost:5173/queue`.

> Here it is. The reviewer sees the diff, the cited source, and the rule
> trace — every rule that was evaluated, with a checkmark on the one that
> fired. The R2-mlr-boundary explanation reads in English.

Click into the proposal. Show the three panels.

> Brand lead signs off.

(Switch identity to "Medical Lead" via the sidebar selector; sign off again.)

> Medical signs off.

(Switch to "MLR Reviewer"; sign off.)

> All three required signatures. The merge happens. The file is updated;
> the index rebuilds within seconds. The audit log records every step:
> the proposal, the three signatures, the merge.

## 7:30 – 9:30 · The three-mode comparison

> The whole point of the rule engine is that materiality routing isn't
> just nicer — it's the difference between a usable vault and a useless one.

Run from the host terminal:

```bash
make demo
```

(The runner prints the three-mode comparison table.)

> Same six agents, same population mix, same random seed. Same starting
> vault.
>
> **Auto-merge mode**: every change merges. Integrity score drops to ~22.
> The vault is corrupted because the contradictions, the unsourced claims,
> and the stale updates all landed.
>
> **Review-everything mode**: every change goes to a queue. Integrity is
> better (~85) because reviewers catch problems — but queue depth is 40
> and growing. This is what happens when companies try "human in the loop
> for everything."
>
> **Materiality-routed mode**: 98. Three rejected outright. 25 in a queue
> that the right reviewer can actually work through. The bad content
> doesn't enter the vault.

## 9:30 – 11:00 · The architecture is the artifact

(Switch back to the IDE.)

> Four ADRs live in `docs/adr/`. The CTO can read them in five minutes:
>
> 1. Files are truth, the database is a derived index.
> 2. The materiality classifier is pure rules, not an LLM.
> 3. Postgres-first for all four indices.
> 4. Every write is a proposal.
>
> Every architectural choice has a one-page rationale. The rule table is
> in `libs/classifier/src/mneme_classifier/rules.py` — 200 lines of Python
> that compliance can audit. The same rules are mirrored as YAML in
> `manifest/rule-packs/commercial-mlr-strict.yml` for non-engineering
> review.

## 11:00 – 12:00 · What this is and what it isn't

> This is M0. Walking skeleton. It runs on a laptop, it demos in twelve
> minutes, and it makes every architectural commitment the production
> system will make. It does not have OAuth — auth is a trusted header.
> It does not have section-level redaction — that's M1. It does not have
> hash-chained audit — that's M3. Every M0 limitation is listed in
> `docs/future-work.md` with the milestone it belongs to.
>
> The next milestone (M1) adds the other five curation agents: provenance,
> staleness, contradiction, synthesis, coverage, ingestion. The
> materiality engine, the file-as-truth model, and the MCP contract carry
> through unchanged.
>
> Thank you. Questions.
