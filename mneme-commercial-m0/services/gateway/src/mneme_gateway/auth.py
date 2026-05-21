"""Trusted-header SSO simulation for M0.

The client sends `X-Mneme-User: u:brand-lead-brandx`. We trust it. Real
OAuth 2.1 federation belongs to M3.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Identity:
    user_id: str            # e.g. "u:brand-lead-brandx"
    roles: list[str]        # e.g. ["brand", "commercial"]
    audience: list[str]     # e.g. ["bu:commercial-onco"]


ANONYMOUS = Identity(user_id="u:anonymous", roles=[], audience=[])


def parse_user_header(value: str | None) -> str:
    if not value:
        return "u:anonymous"
    value = value.strip()
    if not value.startswith("u:"):
        value = f"u:{value}"
    return value
