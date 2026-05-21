"""Aggressive agent: many edits, including some material ones."""

from __future__ import annotations

from datetime import date

from .base import AgentProposal, BaseAgent, TargetFile, pick_target


class AggressiveAgent(BaseAgent):
    name = "aggressive"
    quality = 0.78
    weight = 0.15

    def step(self, targets: list[TargetFile]) -> AgentProposal | None:
        # Aggressive: 50/50 between a routine update and a material payer tier-change
        if self.rng.random() < 0.5:
            t = pick_target(self.rng, targets, of_type="payer-coverage")
            if t:
                body = "coverage_tier changed to tier1 per provider bulletin."
                return AgentProposal(
                    target_id=t.id, new_type=None, new_path=None,
                    change_sections=[{
                        "path": "Current Coverage",
                        "patch": body,
                        "changes_coverage_tier": True,
                    }],
                    rationale="Heard tier-1 placement from a provider rep.",
                    sources=[{"ref": "https://example.local/rep-note",
                              "date": date.today().isoformat(), "kind": "internal"}],
                    agent_quality_score=self.quality,
                    user_id=self.user_id,
                    integrity_signal="ok",
                )
        t = pick_target(self.rng, targets, of_type="hcp-segmentation")
        if not t:
            return None
        return AgentProposal(
            target_id=t.id, new_type=None, new_path=None,
            change_sections=[{
                "path": "Engagement Strategy",
                "patch": "Boost MSL cadence in tier-2 accounts.",
            }],
            rationale="Increase MSL touchpoints.",
            sources=[{"ref": "https://example.local/segmentation",
                      "date": date.today().isoformat(), "kind": "internal"}],
            agent_quality_score=self.quality,
            user_id=self.user_id,
            integrity_signal="ok",
        )
