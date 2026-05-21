"""Three demo modes:

  Mode 1 — auto-merge: every schema-valid proposal fast-forward merges. The
  classifier is *not* consulted. This is what most knowledge-management
  systems do today.

  Mode 2 — review-everything: every schema-valid proposal goes to a single
  reviewer queue, processed at 2 per simulated 10s. Backlog grows.

  Mode 3 — materiality-routed: production behavior. The classifier decides;
  routine auto-merges, attention routes by role, material co-signs.

For M0 we *simulate* the three modes locally rather than reconfiguring the
live gateway — that keeps the demo deterministic from a single seed and
side-steps real DB writes for the comparison run. The headline metric is
the visible delta between the three integrity scores.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from mneme_classifier import Proposal, classify

from .agents import PROFILE_WEIGHTS, AgentProposal
from .agents.base import TargetFile
from .metrics import ModeMetrics


# Synthetic vault snapshot the demo agents edit (no real files touched).
DEMO_TARGETS: list[TargetFile] = [
    TargetFile("kb-brandx-overall-strategy", "brand-strategy/brandx-overall-strategy.md",
               "brand-strategy", "BrandX overall commercial strategy"),
    TargetFile("kb-brandx-vs-brandy-nsclc", "competitive-landscape/brandx-vs-brandy-nsclc.md",
               "competitive-landscape", "BrandX vs BrandY"),
    TargetFile("kb-brandx-united-healthcare", "payer-coverage/brandx-united-healthcare.md",
               "payer-coverage", "BrandX coverage UHC"),
    TargetFile("kb-brandx-academic-medical-centers", "hcp-segmentation/brandx-academic-medical-centers.md",
               "hcp-segmentation", "BrandX academic centers"),
    TargetFile("kb-2026-04-asco-debrief", "msl-insights/2026-q2/2026-04-asco-debrief.md",
               "msl-insight", "MSL ASCO 2026 debrief"),
]


@dataclass
class SimClock:
    seconds: float = 0.0

    def tick(self, delta: float) -> None:
        self.seconds += delta


def _build_proposal(ap: AgentProposal, target: TargetFile) -> Proposal:
    combined = " ".join(s.get("patch", "") for s in ap.change_sections) + " " + ap.rationale
    return Proposal(
        target_path=target.path,
        target_type=target.type,
        target_frontmatter={"id": target.id, "type": target.type},
        change_sections=ap.change_sections,
        body_delta_pct=5.0,
        rationale=ap.rationale,
        claimed_sources=ap.sources,
        agent_id=ap.user_id,
        agent_quality_score=ap.agent_quality_score,
        contradictions=[],
        touches_competitor_data=(target.type == "competitive-landscape"),
        asserts_regulatory_change=("fda" in combined.lower() or "label" in combined.lower()),
        changes_governance_fields=False,
        has_label_adjacent_claim=any(t in combined.lower() for t in (
            "first-line", "superior", "best in class",
        )),
        requires_source=True,
    )


def _emit_agent_proposals(rng: random.Random, total: int, user_prefix: str) -> list[tuple[AgentProposal, TargetFile]]:
    """Emit `total` proposals from the weighted agent population."""
    classes = [cls for cls, _ in PROFILE_WEIGHTS]
    weights = [w for _, w in PROFILE_WEIGHTS]
    out: list[tuple[AgentProposal, TargetFile]] = []
    instances = {cls: cls(rng, f"{user_prefix}:{cls.name}-1") for cls in classes}
    for _ in range(total):
        cls = rng.choices(classes, weights=weights, k=1)[0]
        agent = instances[cls]
        ap = agent.step(DEMO_TARGETS)
        if not ap:
            continue
        target = next((t for t in DEMO_TARGETS if t.id == ap.target_id), None)
        if not target:
            continue
        out.append((ap, target))
    return out


# Integrity scoring deltas (per proposal that gets MERGED into the vault).
# Per spec §9: score starts at 100 and only decreases — "ok" merges are
# neutral. Negative signals dock points when bad content slips through.
INTEGRITY_DELTAS = {
    "ok":             0.0,
    "contradiction": -4.0,
    "unsourced":     -2.0,
    "stale":         -1.0,
    "schema_bad":    -3.0,
}


def run_mode_auto_merge(rng: random.Random, ticks: int) -> ModeMetrics:
    m = ModeMetrics(mode="auto-merge")
    clock = SimClock()
    work = _emit_agent_proposals(rng, ticks, "auto")
    for ap, target in work:
        clock.tick(0.1)
        # Schema sanity stub (in real gateway this is enforced). Sloppy
        # agents that omit sources WILL still merge here — that's the point.
        # We treat unsourced + contradiction as having slipped through.
        m.record_proposal(
            state="merged",
            ttm_seconds=clock.seconds,
            integrity_delta=INTEGRITY_DELTAS.get(ap.integrity_signal, 0.0),
        )
        m.snapshot_queue(0)
    return m


def run_mode_review_all(rng: random.Random, ticks: int) -> ModeMetrics:
    m = ModeMetrics(mode="review-everything")
    clock = SimClock()
    queue: list[tuple[AgentProposal, float]] = []
    work = _emit_agent_proposals(rng, ticks, "review-all")
    for i, (ap, _target) in enumerate(work):
        clock.tick(0.1)
        queue.append((ap, clock.seconds))
        # Reviewer drains 2 every 10 simulated seconds → 1 every 5
        if int(clock.seconds) % 5 == 0 and queue:
            drained = queue.pop(0)
            ttm = clock.seconds - drained[1]
            m.record_proposal(
                state="merged",
                ttm_seconds=ttm,
                integrity_delta=INTEGRITY_DELTAS.get(drained[0].integrity_signal, 0.0) * 0.5,
                # reviewers catch some bad content — halve the integrity hit
            )
        else:
            # Still pending — count as queued for the snapshot only
            m.snapshot_queue(len(queue))
    # Flush remaining queue at end-of-run as queued
    for _ in queue:
        m.proposals_total += 1
        m.queued += 1
    return m


def run_mode_materiality_routed(rng: random.Random, ticks: int) -> ModeMetrics:
    m = ModeMetrics(mode="materiality-routed")
    clock = SimClock()
    work = _emit_agent_proposals(rng, ticks, "routed")
    for ap, target in work:
        clock.tick(0.1)
        proposal = _build_proposal(ap, target)
        verdict = classify(proposal)
        # Integrity delta: rejected/queued bad content does NOT enter the vault,
        # so it doesn't hurt the score. Only merged content moves the score.
        delta = 0.0
        if verdict.label == "routine":
            state = "merged"
            ttm = clock.seconds
            delta = INTEGRITY_DELTAS.get(ap.integrity_signal, 0.0)
        elif verdict.label == "attention":
            # Auto-merge with notification; reviewer catches contradictions/unsourced
            state = "merged"
            ttm = clock.seconds
            sig = ap.integrity_signal
            # attention reviewers catch unsourced + contradiction; halve the hit
            delta = INTEGRITY_DELTAS.get(sig, 0.0)
            if sig in ("contradiction", "unsourced"):
                delta = delta * 0.5
        elif verdict.label == "material":
            state = "needs_review"
            ttm = None
            delta = 0.0
        else:  # reject
            state = "rejected"
            ttm = None
            delta = 0.0
        m.record_proposal(state=state, ttm_seconds=ttm, integrity_delta=delta)
        m.snapshot_queue(m.queued)
    return m


def run_three_modes(seed: int = 7, ticks: int = 60) -> list[ModeMetrics]:
    """Run all three modes from the same seed; return their metrics."""
    return [
        run_mode_auto_merge(random.Random(seed), ticks),
        run_mode_review_all(random.Random(seed), ticks),
        run_mode_materiality_routed(random.Random(seed), ticks),
    ]
