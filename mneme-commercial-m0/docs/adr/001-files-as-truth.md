# ADR-001 — Files are truth, the database is a derived index

## Status

Accepted (M0).

## Context

A pharma commercial knowledge vault has three properties that fight each other:

1. It must be **forwardable to a CTO** — they want to read it, diff it, comment on it.
2. It must be **auditable** — every change needs a who, when, why, and a rollback.
3. It must be **searchable in milliseconds** by agents reading on behalf of users.

Most knowledge-management products solve (3) by making a database the system of
record. They then bolt on (1) and (2) via export and audit-log table; the result
is a database row that is impossible to read out of context, and an audit log
that can be silently truncated.

We have an opposite model available: git. Git already does (1) and (2) better
than any database we could build. It just doesn't do (3).

## Decision

The vault is a git repository of markdown files with YAML frontmatter. Git is
the system of record. Postgres holds **derived indices** (metadata, full-text,
vector embeddings, graph edges), all of which can be rebuilt from
`git log --all` in minutes.

Every read path goes through the indices for speed. Every write path goes
through git for durability — a write is a branch, a commit, and (after
classification) a merge.

## Consequences

**Wins.**

- The vault is human-readable. A CTO can read a markdown file, diff a proposal,
  and understand a 14-day-old change without our help.
- Audit is intrinsic: every change has an author, a parent commit, and a
  signed merge. We don't have to build it.
- Time-travel is free. `git show HEAD~14:competitive-landscape/brandx-vs-brandy.md`
  is what the vault said two weeks ago.
- The system survives Postgres loss; we lose search speed, not knowledge.

**Costs.**

- Search is eventually consistent. After a merge, the index has to catch up.
  M0 takes seconds; production tuning may be needed for sub-second.
- Schema enforcement happens at the validator, not the database. A
  hand-edited file that bypasses the validator can corrupt the vault. M1
  mitigates with pre-receive hooks on the git server.
- Database joins across vault content require Postgres to be in sync. We
  document this in the runbook.

## Alternatives considered

- **Postgres-as-source-of-truth, export markdown for review.** Inverts the
  trust model: the export is always lossy and the database becomes the audit
  source, which moves us back to "trust me, the log is intact."
- **Object store + sidecar git.** Adds an opaque hop; everything we'd gain
  in performance we'd lose in operator complexity.

## Related

- ADR-003: Postgres-first for all derived indices.
- ADR-004: Every write is a proposal, never a direct commit.
