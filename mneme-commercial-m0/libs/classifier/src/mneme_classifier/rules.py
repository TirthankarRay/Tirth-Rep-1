"""Rule definitions for the materiality classifier.

Each rule has a code (R1..R10 plus DEFAULT), a `condition` callable that takes
a Proposal and returns a bool, and a `verdict_factory` that returns the verdict
fields (label, co_sign, route, reason) when fired. Rules are evaluated in
list order; the first match wins. The classifier records every evaluation
in the trace regardless of which one fired.

This file reads like the rule table on purpose. If you need to change MLR
behavior, you change this file.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .types import Proposal, VerdictLabel


@dataclass(frozen=True)
class Rule:
    code: str
    description: str
    condition: Callable[[Proposal], bool]
    verdict_factory: Callable[[Proposal], dict[str, Any]]


def _has_no_source(p: Proposal) -> bool:
    return p.requires_source and len(p.claimed_sources) == 0


def _competitive_landscape(p: Proposal) -> bool:
    return p.target_type == "competitive-landscape"


def _label_adjacent_claim(p: Proposal) -> bool:
    return bool(p.has_label_adjacent_claim)


def _touches_competitor_data(p: Proposal) -> bool:
    return bool(p.touches_competitor_data)


def _payer_coverage_tier_change(p: Proposal) -> bool:
    if p.target_type != "payer-coverage":
        return False
    for section in p.change_sections:
        # Either an explicit marker, or a coverage_tier path/field name in the patch.
        if section.get("changes_coverage_tier"):
            return True
        path = (section.get("path") or "").lower()
        if "coverage_tier" in path or "tier" in path:
            return True
    return False


def _pricing_record(p: Proposal) -> bool:
    return p.target_type == "pricing-record"


def _asserts_regulatory_change(p: Proposal) -> bool:
    return bool(p.asserts_regulatory_change)


def _has_contradictions(p: Proposal) -> bool:
    return len(p.contradictions) > 0


def _msl_insight(p: Proposal) -> bool:
    return p.target_type == "msl-insight"


def _low_agent_quality(p: Proposal) -> bool:
    return p.agent_quality_score < 0.7


def _large_body_delta(p: Proposal) -> bool:
    return p.body_delta_pct > 20.0


def _v(label: VerdictLabel, *, co_sign: list[str] | None = None,
       route: str | None = None, reason: str) -> dict[str, Any]:
    return {
        "label": label,
        "co_sign": list(co_sign or []),
        "route": route,
        "reason": reason,
    }


RULES: list[Rule] = [
    Rule(
        code="R1-no-source",
        description="Proposal that requires a source has no source attached.",
        condition=_has_no_source,
        verdict_factory=lambda p: _v(
            "reject",
            reason="No source provided for a change that requires one.",
        ),
    ),
    Rule(
        code="R2-mlr-boundary",
        description="Touches MLR-sensitive surface (competitive landscape or label-adjacent claim).",
        condition=lambda p: _competitive_landscape(p) or _label_adjacent_claim(p),
        verdict_factory=lambda p: _v(
            "material",
            co_sign=["brand", "medical", "mlr"],
            reason=(
                "Competitive-landscape edits cross the MLR boundary; "
                "brand, medical, and MLR must co-sign."
            ),
        ),
    ),
    Rule(
        code="R3-competitor-data",
        description="Edit touches competitor data outside competitive-landscape files.",
        condition=_touches_competitor_data,
        verdict_factory=lambda p: _v(
            "material",
            co_sign=["brand", "medical"],
            reason="Changes to competitor data require brand and medical co-sign.",
        ),
    ),
    Rule(
        code="R4-payer-tier-change",
        description="Payer-coverage edit changes a coverage tier.",
        condition=_payer_coverage_tier_change,
        verdict_factory=lambda p: _v(
            "material",
            route="market-access",
            reason="Coverage-tier change routed to market access.",
        ),
    ),
    Rule(
        code="R5-pricing",
        description="Any edit to a pricing-record.",
        condition=_pricing_record,
        verdict_factory=lambda p: _v(
            "material",
            co_sign=["legal", "market-access"],
            reason="Pricing edits require legal and market-access co-sign.",
        ),
    ),
    Rule(
        code="R6-regulatory",
        description="Asserts a regulatory change (label, indication, post-marketing requirement).",
        condition=_asserts_regulatory_change,
        verdict_factory=lambda p: _v(
            "material",
            route="regulatory-affairs",
            reason="Regulatory assertion routed to regulatory affairs.",
        ),
    ),
    Rule(
        code="R7-contradiction",
        description="Upstream contradiction check flagged a conflict.",
        condition=_has_contradictions,
        verdict_factory=lambda p: _v(
            "material",
            reason=(
                f"Contradiction detected against {len(p.contradictions)} existing claim(s)."
            ),
        ),
    ),
    Rule(
        code="R8-msl-insight",
        description="MSL insight — always attention so medical sees it.",
        condition=_msl_insight,
        verdict_factory=lambda p: _v(
            "attention",
            route="medical",
            reason="MSL insight; notify medical.",
        ),
    ),
    Rule(
        code="R9-agent-quality",
        description="Proposing agent has a quality score below 0.7.",
        condition=_low_agent_quality,
        verdict_factory=lambda p: _v(
            "attention",
            reason=f"Agent quality {p.agent_quality_score:.2f} below 0.70 threshold.",
        ),
    ),
    Rule(
        code="R10-large-delta",
        description="Body delta exceeds 20% of the file.",
        condition=_large_body_delta,
        verdict_factory=lambda p: _v(
            "attention",
            reason=f"Body delta {p.body_delta_pct:.1f}% exceeds 20% threshold.",
        ),
    ),
]


DEFAULT_RULE = Rule(
    code="DEFAULT-routine",
    description="No rule fired; proposal is routine.",
    condition=lambda p: True,
    verdict_factory=lambda p: _v(
        "routine",
        reason="No material or attention rule fired; auto-mergeable.",
    ),
)
