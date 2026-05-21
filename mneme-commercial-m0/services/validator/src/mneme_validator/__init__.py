"""Mneme validator service.

Two responsibilities:
 1. Library helpers used inline by the gateway's propose_edit (schema_check,
    source_check, classifier wrapper).
 2. A merge-after-signoff worker: when all required reviewers have signed off,
    materialize the merge of the proposal branch into main.

For M0, both live in this package; the gateway imports the helpers, and the
console-api invokes the merge worker after the last sign-off.
"""
