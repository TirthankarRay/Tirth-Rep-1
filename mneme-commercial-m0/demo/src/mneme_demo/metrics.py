"""Per-mode metrics: integrity score, queue depth, time-to-merge."""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field


@dataclass
class ModeMetrics:
    mode: str
    proposals_total: int = 0
    auto_merged: int = 0
    queued: int = 0
    rejected: int = 0
    times_to_merge_seconds: list[float] = field(default_factory=list)
    integrity_score: float = 100.0  # starts perfect, decreases on slipped-through bad content
    queue_depth_samples: list[int] = field(default_factory=list)

    def record_proposal(self, *, state: str, ttm_seconds: float | None,
                        integrity_delta: float) -> None:
        self.proposals_total += 1
        if state == "merged":
            self.auto_merged += 1
        elif state == "needs_review":
            self.queued += 1
        elif state == "rejected":
            self.rejected += 1
        if ttm_seconds is not None:
            self.times_to_merge_seconds.append(ttm_seconds)
        self.integrity_score = max(0.0, self.integrity_score + integrity_delta)

    def snapshot_queue(self, depth: int) -> None:
        self.queue_depth_samples.append(depth)

    def summary(self) -> dict:
        return {
            "mode": self.mode,
            "proposals_total": self.proposals_total,
            "auto_merged": self.auto_merged,
            "queued": self.queued,
            "rejected": self.rejected,
            "median_ttm_seconds": (
                statistics.median(self.times_to_merge_seconds)
                if self.times_to_merge_seconds else None
            ),
            "integrity_score": round(self.integrity_score, 2),
            "max_queue_depth": (
                max(self.queue_depth_samples) if self.queue_depth_samples else 0
            ),
        }
