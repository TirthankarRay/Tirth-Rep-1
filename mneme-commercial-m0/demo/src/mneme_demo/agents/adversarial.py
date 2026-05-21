"""Adversarial agent: tries to elevate routine content to material to game
review queues, or labels-adjacent claims that should fire R2."""

from __future__ import annotations

from datetime import date

from .base import AgentProposal, BaseAgent, TargetFile, pick_target


class AdversarialAgent(BaseAgent):
    name = "adversarial"
    quality = 0.70
    weight = 0.10

    def step(self, targets: list[TargetFile]) -> AgentProposal | None:
        t = pick_target(self.rng, targets, of_type="brand-strategy")
        if not t:
            return None
        body = (
            "Reframing: BrandX is the first-line option of choice, superior to "
            "all competitors. This is the best in class therapy in the segment."
        )
        return AgentProposal(
            target_id=t.id, new_type=None, new_path=None,
            change_sections=[{"path": "Positioning", "patch": body}],
            rationale="Strengthen positioning to first-line, superior framing.",
            sources=[{"ref": "https://example.local/positioning-memo",
                      "date": date.today().isoformat(), "kind": "internal"}],
            agent_quality_score=self.quality,
            user_id=self.user_id,
            integrity_signal="ok",  # caught by R2 via label-adjacent
        )
