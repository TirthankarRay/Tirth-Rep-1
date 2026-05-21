# ADR-004 — Every write is a proposal, never a direct commit

## Status

Accepted (M0).

## Context

There are two governance philosophies for a write-heavy knowledge system:

1. **Optimistic** — let the agent write, then review (or roll back). This is
   how most knowledge bases work. It's easy to build and easy to abuse.
2. **Mandatory proposal** — every write opens a branch, is classified, and is
   routed. The vault main branch is never written to directly.

Optimistic systems have a recurring failure mode: an agent or a person writes
a plausible-sounding but wrong claim into a central document. Downstream
agents read it as truth. By the time someone notices, the bad claim has
been quoted in a slide deck, a regulatory submission, and three emails.
The audit log says "it was written" but offers no chance to have caught it.

In a pharma commercial vault that pattern is unacceptable. An MLR-boundary
write that bypasses review is a regulatory liability.

## Decision

Every write goes through `vault.propose_edit`. The lifecycle is:

```
agent.propose_edit → branch → commit → validate → classify → route
                                                      ↓
              ┌───────────────────────────────────────┼────────────────────┐
              ↓                                       ↓                    ↓
          reject                              routine / attention      material
       (close branch)                          (merge to main)      (review_queue)
                                                                            ↓
                                                                       co-sign
                                                                            ↓
                                                                       merge to main
```

`main` is only ever updated by the validator (routine + attention) or after
reviewer co-sign (material). Agents do not have direct push.

This is enforced architecturally by the deployment topology, not by
convention: the vault repo is reachable through the gateway only.

## Consequences

**Wins.**

- Governance happens at the write path, not after. The trace and the
  verdict are recorded for every change, including rejected ones.
- The reviewer queue is a real queue with real SLA semantics. Reviewers
  see only what they need to see, ordered by urgency.
- The system supports both autonomous agents and human editors with the
  same primitive — there is no separate "human path."

**Costs.**

- Every write is slower. Routine writes complete in seconds (branch + commit
  + index sync), not milliseconds. We accept this; the alternative is the
  failure mode above.
- The gateway can become a bottleneck. M0 runs the validator inline; if we
  ever see queue depth under load, we'll separate the validator into a worker
  and have `propose_edit` return a `pending` state.

## Alternatives considered

- **Soft governance with audit.** Rejected. The failure mode is the entire
  reason this system exists.
- **Per-path policy (some paths governed, some not).** Rejected for M0;
  simpler to govern uniformly. Per-path policy can be added later by
  short-circuiting the classifier on specific path patterns.

## Related

- ADR-002: the classifier is pure rules.
- See `services/gateway/src/mneme_gateway/tools/propose_edit.py` for the lifecycle.
