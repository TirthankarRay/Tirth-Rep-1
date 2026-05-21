"""Demo runner.

Two parts:
  1. The headline three-mode comparison (purely local, deterministic from a
     single seed). Runs in ~1 real second and produces a side-by-side table
     and JSON dump that the console can render.
  2. A "live" run that ALSO drives the real gateway over HTTP, so the
     reviewer console populates with real proposals. This part requires the
     gateway to be up on port 8001.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Iterable

import httpx

from .modes import DEMO_TARGETS, run_three_modes
from .reporter import print_summary
from .agents import PROFILE_WEIGHTS


GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://gateway:8001")
LIVE_PROPOSALS = int(os.environ.get("DEMO_LIVE_PROPOSALS", "12"))


def _maybe_live_run(seed: int = 7) -> None:
    """Drive the gateway with a small number of real proposals so the console
    has something to display. If the gateway isn't reachable, we skip
    gracefully — the local mode comparison still ran."""
    try:
        r = httpx.get(f"{GATEWAY_URL}/healthz", timeout=2)
        r.raise_for_status()
    except Exception as e:
        print(f"\nGateway not reachable at {GATEWAY_URL}; skipping live run ({e}).")
        return

    print(f"\nDriving gateway at {GATEWAY_URL} with {LIVE_PROPOSALS} real proposals...")
    import random
    rng = random.Random(seed)
    classes = [cls for cls, _ in PROFILE_WEIGHTS]
    weights = [w for _, w in PROFILE_WEIGHTS]
    instances = {cls: cls(rng, f"agent:{cls.name}-1") for cls in classes}

    sent = 0
    with httpx.Client(timeout=15) as client:
        for _ in range(LIVE_PROPOSALS):
            cls = rng.choices(classes, weights=weights, k=1)[0]
            agent = instances[cls]
            ap = agent.step(DEMO_TARGETS)
            if not ap:
                continue
            body = {
                "id": ap.target_id,
                "new_type": ap.new_type,
                "new_path": ap.new_path,
                "change": {"sections": ap.change_sections},
                "rationale": ap.rationale,
                "sources": ap.sources,
                "agent_quality_score": ap.agent_quality_score,
            }
            try:
                resp = client.post(
                    f"{GATEWAY_URL}/mcp/vault.propose_edit",
                    json=body,
                    headers={"X-Mneme-User": ap.user_id},
                )
                resp.raise_for_status()
                data = resp.json()
                verdict = data.get("verdict", {})
                print(
                    f"  {cls.name:<18} → {data.get('state'):<14} "
                    f"verdict={verdict.get('label'):<10} rule={verdict.get('rule')}"
                )
                sent += 1
            except Exception as e:
                print(f"  {cls.name}: error {e}")
            time.sleep(0.05)
    print(f"\nSent {sent} live proposals. Check the console at http://localhost:5173/queue.")


def run() -> int:
    print("=" * 72)
    print(" Mneme M0 demo — three modes (same agent population, same seed)")
    print("=" * 72)
    metrics = run_three_modes(seed=7, ticks=60)
    print_summary(metrics)
    _maybe_live_run(seed=7)
    return 0


if __name__ == "__main__":
    sys.exit(run())
