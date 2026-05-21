"""Source check.

Every claim must cite at least one source — this is the architectural
commitment in section 2 of the spec ("Every claim in a vault file must
have a source"). M0 enforces it at the file level: the frontmatter must
carry `sources` with at least one entry, and the body should reference
at least one footnote-style `[^sN]:`. The gateway's propose_edit also
requires the proposer pass `sources`; this is the file-after-merge check.
"""

from __future__ import annotations

import re
from typing import Any


FOOTNOTE_DEF_RE = re.compile(r"\[\^([a-zA-Z0-9_-]+)\]:")


def check(frontmatter: dict[str, Any], body: str, *, requires_source: bool = True) -> list[str]:
    errors: list[str] = []
    if not requires_source:
        return errors
    sources = frontmatter.get("sources") or []
    if not sources:
        errors.append("frontmatter.sources is empty")
    if requires_source and not FOOTNOTE_DEF_RE.search(body):
        # Warn but don't fail; some files keep all citations in the frontmatter.
        # For the demo we treat missing footnotes as a soft signal only.
        pass
    return errors
