"""Input and output contracts for the classifier."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Literal


VerdictLabel = Literal["routine", "attention", "material", "reject"]


@dataclass
class Proposal:
    """Structured payload the classifier evaluates.

    All fields are required; callers are responsible for filling them. The
    classifier never reaches outside this struct, which is what makes it
    deterministic and unit-testable.
    """

    target_path: str
    target_type: str
    target_frontmatter: dict[str, Any]
    change_sections: list[dict[str, Any]]
    body_delta_pct: float
    rationale: str
    claimed_sources: list[dict[str, Any]]
    agent_id: str
    agent_quality_score: float
    contradictions: list[dict[str, Any]] = field(default_factory=list)
    touches_competitor_data: bool = False
    asserts_regulatory_change: bool = False
    changes_governance_fields: bool = False
    # Optional: marker set by upstream NLP / source-check that the change
    # contains a competitive-claim-adjacent label (e.g. "first-line", "superior").
    has_label_adjacent_claim: bool = False
    # Optional: explicit signal that this proposal requires a source. We
    # default-true for any non-entity write; the validator can override.
    requires_source: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RuleEvaluation:
    """One entry in the trace — what rule was tried and what happened."""

    rule: str
    matched: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"rule": self.rule, "matched": self.matched, "reason": self.reason}


@dataclass
class Verdict:
    label: VerdictLabel
    rule: str
    co_sign: list[str] = field(default_factory=list)
    route: str | None = None
    reason: str = ""
    trace: list[RuleEvaluation] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "rule": self.rule,
            "co_sign": list(self.co_sign),
            "route": self.route,
            "reason": self.reason,
            "trace": [t.to_dict() for t in self.trace],
        }
