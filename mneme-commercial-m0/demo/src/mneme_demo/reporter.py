"""Pretty-print mode summaries to stdout (the demo runs in a terminal)."""

from __future__ import annotations

import json
from typing import Iterable

from .metrics import ModeMetrics


def print_summary(metrics: Iterable[ModeMetrics]) -> None:
    rows = [m.summary() for m in metrics]
    if not rows:
        return
    cols = [
        ("mode", 22), ("proposals_total", 8), ("auto_merged", 8),
        ("queued", 8), ("rejected", 8), ("median_ttm_seconds", 8),
        ("integrity_score", 10), ("max_queue_depth", 8),
    ]
    header = "  ".join(f"{name:<{w}}" for name, w in cols)
    print()
    print(header)
    print("  ".join("-" * w for _, w in cols))
    for r in rows:
        out = []
        for name, w in cols:
            v = r.get(name)
            if isinstance(v, float):
                s = f"{v:.2f}"
            elif v is None:
                s = "-"
            else:
                s = str(v)
            out.append(f"{s:<{w}}")
        print("  ".join(out))
    print()
    print("Raw JSON:")
    print(json.dumps(rows, indent=2))
