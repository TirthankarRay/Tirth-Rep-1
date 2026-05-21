"""Section-level redaction stub for M0.

Real ABAC + section-level masking belongs to M1. For M0 we honor only the
file-level `classification` field: anything `restricted` is hidden from
identities without one of the access-granting roles.
"""

from __future__ import annotations

from typing import Any

from ..auth import Identity


PRIVILEGED_ROLES = {"market-access", "legal", "mlr"}


def can_read(identity: Identity, frontmatter: dict[str, Any]) -> bool:
    classification = (frontmatter.get("classification") or "internal").lower()
    if classification in ("public", "internal", "confidential"):
        return True
    # restricted
    return any(r in PRIVILEGED_ROLES for r in identity.roles)


def redact_body(identity: Identity, frontmatter: dict[str, Any], body: str) -> str:
    if can_read(identity, frontmatter):
        return body
    return (
        "[REDACTED — this file is classified `restricted` and is not visible "
        "to your role. Contact market-access@brandx.local for access.]"
    )
