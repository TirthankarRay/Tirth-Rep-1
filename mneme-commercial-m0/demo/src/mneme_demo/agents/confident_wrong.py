"""Confident-wrong agent: well-sourced citations but the *claim* contradicts
existing vault truth. The integrity signal flags this so the local scoring
system can dock points if it slipped through.
"""

from __future__ import annotations

from datetime import date

from .base import AgentProposal, BaseAgent, TargetFile, pick_target


class ConfidentWrongAgent(BaseAgent):
    name = "confident_wrong"
    quality = 0.85
    weight = 0.20

    def step(self, targets: list[TargetFile]) -> AgentProposal | None:
        # Target a competitive-landscape file with a counter-factual edit.
        t = pick_target(self.rng, targets, of_type="competitive-landscape")
        if not t:
            return None
        body = (
            "Updated commercial framing: BrandY has been shown in real-world "
            "evidence to outperform BrandX on durability by a wide margin. "
            "Field teams should adjust positioning accordingly."
        )
        return AgentProposal(
            target_id=t.id, new_type=None, new_path=None,
            change_sections=[{"path": "Commercial Implications", "patch": body}],
            rationale="RWE update from a third-party analytics vendor.",
            sources=[{"ref": "https://example.local/vendor/rwe-claim",
                      "date": date.today().isoformat(), "kind": "external"}],
            agent_quality_score=self.quality,
            user_id=self.user_id,
            integrity_signal="contradiction",
        )
