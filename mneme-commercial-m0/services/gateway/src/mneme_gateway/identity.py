"""Identity → attribute resolution for M0.

A hard-coded role map. Realistic enough for the demo, simple enough that
we don't need an IdP. M3 swaps this out for OIDC / SCIM.
"""

from __future__ import annotations

from .auth import Identity


ROLE_MAP: dict[str, Identity] = {
    "u:brand-lead-brandx": Identity(
        user_id="u:brand-lead-brandx",
        roles=["brand", "commercial-onco"],
        audience=["bu:commercial-onco"],
    ),
    "u:medical-lead-brandx": Identity(
        user_id="u:medical-lead-brandx",
        roles=["medical", "commercial-onco"],
        audience=["bu:commercial-onco", "bu:medical-affairs"],
    ),
    "u:mlr-reviewer": Identity(
        user_id="u:mlr-reviewer",
        roles=["mlr"],
        audience=["bu:commercial-onco", "bu:medical-affairs"],
    ),
    "u:market-access-lead": Identity(
        user_id="u:market-access-lead",
        roles=["market-access", "commercial-onco"],
        audience=["bu:commercial-onco", "bu:market-access"],
    ),
    "u:legal-lead": Identity(
        user_id="u:legal-lead",
        roles=["legal"],
        audience=["bu:legal"],
    ),
    "u:msl-lead": Identity(
        user_id="u:msl-lead",
        roles=["medical"],
        audience=["bu:medical-affairs"],
    ),
    "u:launch-pm": Identity(
        user_id="u:launch-pm",
        roles=["launch-pm", "commercial-onco"],
        audience=["bu:commercial-onco"],
    ),
    "u:regulatory-affairs": Identity(
        user_id="u:regulatory-affairs",
        roles=["regulatory-affairs"],
        audience=["bu:regulatory"],
    ),
    "u:ontology-curator": Identity(
        user_id="u:ontology-curator",
        roles=["ontology-curator"],
        audience=["bu:commercial-onco"],
    ),
    # Agent identities for the demo runner
    "agent:diligent-1": Identity(
        user_id="agent:diligent-1",
        roles=["agent"],
        audience=["bu:commercial-onco"],
    ),
}


def resolve(user_id: str) -> Identity:
    if user_id in ROLE_MAP:
        return ROLE_MAP[user_id]
    # Default: an unknown user gets read-only commercial access
    return Identity(user_id=user_id, roles=["reader"], audience=["bu:commercial-onco"])
