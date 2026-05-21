"""The classifier entry point.

`classify(proposal)` iterates RULES in priority order, records every
evaluation in the trace, and returns the verdict from the first rule
that fires. If none fire, DEFAULT_RULE returns `routine`.

The function is pure: no I/O, no clocks, no globals beyond the immutable
RULES list. Same input always returns same output and same trace.
"""

from __future__ import annotations

from .rules import RULES, DEFAULT_RULE, Rule
from .types import Proposal, RuleEvaluation, Verdict


def classify(proposal: Proposal) -> Verdict:
    trace: list[RuleEvaluation] = []
    matched_rule: Rule | None = None

    for rule in RULES:
        if matched_rule is None and rule.condition(proposal):
            matched_rule = rule
            trace.append(RuleEvaluation(
                rule=rule.code,
                matched=True,
                reason=rule.description,
            ))
        else:
            trace.append(RuleEvaluation(
                rule=rule.code,
                matched=False,
                reason=rule.description,
            ))

    if matched_rule is None:
        matched_rule = DEFAULT_RULE
        trace.append(RuleEvaluation(
            rule=DEFAULT_RULE.code,
            matched=True,
            reason=DEFAULT_RULE.description,
        ))

    fields = matched_rule.verdict_factory(proposal)
    return Verdict(
        label=fields["label"],
        rule=matched_rule.code,
        co_sign=fields.get("co_sign", []),
        route=fields.get("route"),
        reason=fields["reason"],
        trace=trace,
    )
