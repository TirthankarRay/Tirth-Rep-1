"""Unit tests for every classifier rule.

One test per rule (R1–R10) asserting the label, the firing rule code, and
trace completeness. Plus tests for the default rule, priority order, and
determinism.
"""

from __future__ import annotations

from mneme_classifier import classify, RULES


def _trace_codes(verdict):
    return [t.rule for t in verdict.trace]


def test_r1_no_source_rejects(base_proposal):
    p = base_proposal(claimed_sources=[])
    v = classify(p)
    assert v.label == "reject"
    assert v.rule == "R1-no-source"
    assert v.trace[0].matched is True
    assert "source" in v.reason.lower()


def test_r2_competitive_landscape_material(base_proposal):
    p = base_proposal(
        target_path="competitive-landscape/brandx-vs-brandy-nsclc.md",
        target_type="competitive-landscape",
    )
    v = classify(p)
    assert v.label == "material"
    assert v.rule == "R2-mlr-boundary"
    assert v.co_sign == ["brand", "medical", "mlr"]


def test_r2_label_adjacent_claim_material(base_proposal):
    p = base_proposal(has_label_adjacent_claim=True)
    v = classify(p)
    assert v.label == "material"
    assert v.rule == "R2-mlr-boundary"
    assert v.co_sign == ["brand", "medical", "mlr"]


def test_r3_competitor_data_material(base_proposal):
    p = base_proposal(touches_competitor_data=True)
    v = classify(p)
    assert v.label == "material"
    assert v.rule == "R3-competitor-data"
    assert v.co_sign == ["brand", "medical"]


def test_r4_payer_tier_change_material(base_proposal):
    p = base_proposal(
        target_path="payer-coverage/brandx-united-healthcare.md",
        target_type="payer-coverage",
        change_sections=[{
            "path": "coverage_tier",
            "before": "tier3",
            "after": "tier2",
            "changes_coverage_tier": True,
        }],
    )
    v = classify(p)
    assert v.label == "material"
    assert v.rule == "R4-payer-tier-change"
    assert v.route == "market-access"


def test_r5_pricing_material(base_proposal):
    p = base_proposal(
        target_path="pricing/brandx-list-price.md",
        target_type="pricing-record",
    )
    v = classify(p)
    assert v.label == "material"
    assert v.rule == "R5-pricing"
    assert v.co_sign == ["legal", "market-access"]


def test_r6_regulatory_material(base_proposal):
    p = base_proposal(asserts_regulatory_change=True)
    v = classify(p)
    assert v.label == "material"
    assert v.rule == "R6-regulatory"
    assert v.route == "regulatory-affairs"


def test_r7_contradiction_material(base_proposal):
    p = base_proposal(contradictions=[{"existing": "claim-a", "proposed": "claim-b"}])
    v = classify(p)
    assert v.label == "material"
    assert v.rule == "R7-contradiction"


def test_r8_msl_insight_attention(base_proposal):
    p = base_proposal(
        target_path="msl-insights/2026-q2/2026-04-asco-debrief.md",
        target_type="msl-insight",
    )
    v = classify(p)
    assert v.label == "attention"
    assert v.rule == "R8-msl-insight"
    assert v.route == "medical"


def test_r9_low_agent_quality_attention(base_proposal):
    p = base_proposal(agent_quality_score=0.55)
    v = classify(p)
    assert v.label == "attention"
    assert v.rule == "R9-agent-quality"


def test_r10_large_delta_attention(base_proposal):
    p = base_proposal(body_delta_pct=42.0)
    v = classify(p)
    assert v.label == "attention"
    assert v.rule == "R10-large-delta"


def test_default_routine(base_proposal):
    v = classify(base_proposal())
    assert v.label == "routine"
    assert v.rule == "DEFAULT-routine"
    assert v.co_sign == []


def test_priority_order_r1_before_r2(base_proposal):
    """A competitive-landscape edit with no source must reject (R1), not material (R2)."""
    p = base_proposal(
        target_path="competitive-landscape/brandx-vs-brandy-nsclc.md",
        target_type="competitive-landscape",
        claimed_sources=[],
    )
    v = classify(p)
    assert v.rule == "R1-no-source"
    assert v.label == "reject"


def test_priority_order_r2_before_r3(base_proposal):
    """A competitive-landscape edit also touching competitor data fires R2, not R3."""
    p = base_proposal(
        target_path="competitive-landscape/brandx-vs-brandy-nsclc.md",
        target_type="competitive-landscape",
        touches_competitor_data=True,
    )
    v = classify(p)
    assert v.rule == "R2-mlr-boundary"


def test_priority_order_material_before_attention(base_proposal):
    """A pricing edit by a low-quality agent fires R5 material, not R9 attention."""
    p = base_proposal(
        target_path="pricing/brandx-list-price.md",
        target_type="pricing-record",
        agent_quality_score=0.30,
    )
    v = classify(p)
    assert v.label == "material"
    assert v.rule == "R5-pricing"


def test_trace_records_every_rule(base_proposal):
    """The trace must contain an entry for every rule (matched or not), in order."""
    v = classify(base_proposal())
    codes_in_trace = _trace_codes(v)
    expected_codes = [r.code for r in RULES] + ["DEFAULT-routine"]
    assert codes_in_trace == expected_codes


def test_trace_marks_only_first_match(base_proposal):
    """When R5 fires, only R5 should be marked matched=True (plus the DEFAULT is absent)."""
    p = base_proposal(
        target_path="pricing/brandx-list-price.md",
        target_type="pricing-record",
    )
    v = classify(p)
    matched = [t for t in v.trace if t.matched]
    assert len(matched) == 1
    assert matched[0].rule == "R5-pricing"


def test_determinism(base_proposal):
    """Same input must produce identical verdicts (including trace)."""
    p = base_proposal(
        target_path="competitive-landscape/brandx-vs-brandy-nsclc.md",
        target_type="competitive-landscape",
    )
    v1 = classify(p)
    v2 = classify(p)
    assert v1.to_dict() == v2.to_dict()


def test_verdict_has_human_reason(base_proposal):
    """Every verdict carries a non-empty reason string."""
    for p_kwargs in [
        {"claimed_sources": []},  # R1
        {"target_type": "competitive-landscape"},  # R2
        {"touches_competitor_data": True},  # R3
        {"target_type": "pricing-record"},  # R5
        {},  # default
    ]:
        v = classify(base_proposal(**p_kwargs))
        assert v.reason and len(v.reason) > 0
