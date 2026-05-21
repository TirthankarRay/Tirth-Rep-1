"""Base classes for simulated proposer agents."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentProposal:
    """A proposal a simulated agent emits. Maps to the gateway's
    propose_edit body.
    """
    target_id: str | None
    new_type: str | None
    new_path: str | None
    change_sections: list[dict[str, Any]]
    rationale: str
    sources: list[dict[str, Any]]
    agent_quality_score: float
    user_id: str
    # Used by the local scoring system in modes.py to assess integrity impact
    integrity_signal: str = "ok"  # ok | contradiction | unsourced | schema_bad | stale


@dataclass
class TargetFile:
    """A snapshot of a vault file the agent can edit."""
    id: str
    path: str
    type: str
    title: str


class BaseAgent:
    name: str = "base"
    quality: float = 0.80
    weight: float = 0.10

    def __init__(self, rng: random.Random, user_id: str):
        self.rng = rng
        self.user_id = user_id

    def step(self, targets: list[TargetFile]) -> AgentProposal | None:
        raise NotImplementedError


def pick_target(rng: random.Random, targets: list[TargetFile],
                of_type: str | None = None) -> TargetFile | None:
    pool = [t for t in targets if (of_type is None or t.type == of_type)]
    if not pool:
        return None
    return rng.choice(pool)
