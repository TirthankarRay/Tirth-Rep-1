"""Shared fixtures for classifier tests."""

from __future__ import annotations

import pytest

from mneme_classifier import Proposal


def _base_proposal(**overrides) -> Proposal:
    defaults = dict(
        target_path="brand-strategy/brandx-overall-strategy.md",
        target_type="brand-strategy",
        target_frontmatter={"id": "kb-test", "type": "brand-strategy"},
        change_sections=[{"path": "Positioning", "before": "old", "after": "new"}],
        body_delta_pct=2.0,
        rationale="Adjust positioning per Q2 plan.",
        claimed_sources=[{"ref": "https://example.local/doc", "kind": "internal"}],
        agent_id="agent:diligent-1",
        agent_quality_score=0.95,
        contradictions=[],
        touches_competitor_data=False,
        asserts_regulatory_change=False,
        changes_governance_fields=False,
        has_label_adjacent_claim=False,
        requires_source=True,
    )
    defaults.update(overrides)
    return Proposal(**defaults)


@pytest.fixture
def base_proposal():
    """Returns a factory for proposals with sensible routine defaults."""
    return _base_proposal
