"""Human-readable trace helpers.

Used by the gateway and the console to render why a verdict was reached.
The trace itself is just a list of RuleEvaluation; this module formats it.
"""

from __future__ import annotations

from .types import RuleEvaluation, Verdict


def format_trace_lines(trace: list[RuleEvaluation]) -> list[str]:
    """Return one line per rule evaluation, prefixed with ✓ or ·."""
    lines = []
    for entry in trace:
        marker = "✓" if entry.matched else "·"
        lines.append(f"  {marker} {entry.rule}: {entry.reason}")
    return lines


def format_verdict(verdict: Verdict) -> str:
    header = f"[{verdict.label.upper()}] {verdict.rule} — {verdict.reason}"
    parts = [header]
    if verdict.co_sign:
        parts.append(f"  co-sign: {', '.join(verdict.co_sign)}")
    if verdict.route:
        parts.append(f"  route: {verdict.route}")
    parts.append("  trace:")
    parts.extend(format_trace_lines(verdict.trace))
    return "\n".join(parts)
