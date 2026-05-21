"""Stale agent: updates past review_cycle with old data."""

from __future__ import annotations

from datetime import date, timedelta

from .base import AgentProposal, BaseAgent, TargetFile, pick_target


class StaleAgent(BaseAgent):
    name = "stale"
    quality = 0.60
    weight = 0.05

    def step(self, targets: list[TargetFile]) -> AgentProposal | None:
        t = pick_target(self.rng, targets, of_type="msl-insight")
        if not t:
            return None
        old_date = (date.today() - timedelta(days=180)).isoformat()
        return AgentProposal(
            target_id=t.id, new_type=None, new_path=None,
            change_sections=[{
                "path": "Implications",
                "patch": f"Note (dated {old_date}): no new insights to add.",
            }],
            rationale="Touch-up; no real new content.",
            sources=[{"ref": "https://example.local/msl-archive",
                      "date": old_date, "kind": "internal"}],
            agent_quality_score=self.quality,
            user_id=self.user_id,
            integrity_signal="stale",
        )
