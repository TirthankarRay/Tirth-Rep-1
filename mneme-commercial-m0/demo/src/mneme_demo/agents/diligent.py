"""Diligent agent: well-sourced, schema-clean, infrequent."""

from __future__ import annotations

from datetime import date

from .base import AgentProposal, BaseAgent, TargetFile, pick_target


class DiligentAgent(BaseAgent):
    name = "diligent"
    quality = 0.95
    weight = 0.30

    def step(self, targets: list[TargetFile]) -> AgentProposal | None:
        t = pick_target(self.rng, targets, of_type="brand-strategy")
        if not t:
            t = pick_target(self.rng, targets)
        if not t:
            return None
        body = (
            f"Updated KPI tracking note ({date.today().isoformat()}): adjusted Q2 "
            f"forecast for {t.title} to reflect April pull-through data; trending "
            f"in line with plan."
        )
        return AgentProposal(
            target_id=t.id, new_type=None, new_path=None,
            change_sections=[{"path": "KPIs", "patch": body}],
            rationale="Q2 forecast refresh from April pull-through.",
            sources=[{"ref": "https://example.local/q2-fcst-2026",
                      "date": date.today().isoformat(), "kind": "internal"}],
            agent_quality_score=self.quality,
            user_id=self.user_id,
            integrity_signal="ok",
        )
