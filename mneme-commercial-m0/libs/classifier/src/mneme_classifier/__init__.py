"""Mneme materiality classifier.

Pure rule engine. Deterministic. Same input always produces same output
and same rule trace. No I/O in the hot path.
"""

from .types import Proposal, Verdict, RuleEvaluation
from .classify import classify
from .rules import RULES, Rule

__all__ = [
    "Proposal",
    "Verdict",
    "RuleEvaluation",
    "classify",
    "RULES",
    "Rule",
]
