"""Thin re-export of the materiality classifier so callers in this service
have a stable import path.
"""

from mneme_classifier import classify, Proposal, Verdict

__all__ = ["classify", "Proposal", "Verdict"]
