"""Sloppy agent: missing sources, schema violations."""

from __future__ import annotations

from .base import AgentProposal, BaseAgent, TargetFile, pick_target


class SloppyAgent(BaseAgent):
    name = "sloppy"
    quality = 0.55
    weight = 0.20

    def step(self, targets: list[TargetFile]) -> AgentProposal | None:
        t = pick_target(self.rng, targets)
        if not t:
            return None
        return AgentProposal(
            target_id=t.id, new_type=None, new_path=None,
            change_sections=[{"path": "Notes", "patch": "Heard something interesting."}],
            rationale="quick update",
            sources=[],  # ← R1 should fire (no source)
            agent_quality_score=self.quality,
            user_id=self.user_id,
            integrity_signal="unsourced",
        )
