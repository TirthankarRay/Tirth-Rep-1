# ADR-002 — Materiality classifier is pure rules, not an LLM

## Status

Accepted (M0).

## Context

Every proposed write into the vault has to be routed. There are three plausible
designs:

1. **Pure rules.** A deterministic function `Proposal → Verdict` driven by a
   readable rule pack.
2. **LLM classifier.** Hand the proposal to a model, get back a label.
3. **Hybrid.** Rules for the obvious cases, model for the gray ones.

The MLR-boundary case is the ground-truth test. If a competitor-claim change
to `competitive-landscape/brandx-vs-brandy-nsclc.md` ever skips the
brand + medical + MLR co-sign because the classifier was "uncertain," the
sponsor takes a real regulatory hit.

## Decision

The classifier is option 1: a pure Python function over a structured `Proposal`
dataclass. Rules R1..R10 are defined as a list of `(condition, verdict)` pairs;
the first match wins. Every evaluation appears in the trace whether it fires
or not.

LLMs are still useful upstream — for content extraction, contradiction signal
generation, summary writing — but they don't make the routing call.

## Consequences

**Wins.**

- The verdict is reproducible. Same input always → same trace. A reviewer can
  read why a proposal was material.
- The rule table is a single Python file (`libs/classifier/src/mneme_classifier/rules.py`)
  that compliance + MLR + legal can audit. A YAML mirror lives in
  `manifest/rule-packs/commercial-mlr-strict.yml` for the same audience.
- Unit tests are trivial: one test per rule.
- No model dependency, no inference cost, sub-millisecond classification.

**Costs.**

- Semantic distinctions become harder. "Does this paragraph make a
  label-adjacent claim?" is a coarse string check in M0 (`has_label_adjacent_claim`
  bool set upstream); a model would be more nuanced.
- The rule table has to be maintained explicitly as the business evolves.
  This is a feature, not a bug — every change is a tracked artifact — but
  it does mean compliance and engineering have to stay in sync.

## Alternatives considered

- **LLM classifier.** Rejected: non-determinism, cost, and the inability to
  give a reviewer a "why" that isn't model output. We also can't ask a CIO
  to trust an LLM to be the gatekeeper for MLR-boundary content.
- **Hybrid.** Rejected for M0: the moment any LLM influences the routing,
  we lose the reproducibility property. Revisit in M2 once the upstream
  signal generators are themselves auditable.

## Related

- See `libs/classifier/src/mneme_classifier/rules.py` for the rule table.
- See `libs/classifier/tests/test_rules.py` for one test per rule.
