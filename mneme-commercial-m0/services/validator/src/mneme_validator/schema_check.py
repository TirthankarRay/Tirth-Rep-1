"""Schema check — wraps mneme_schemas.SchemaSet for one-shot validation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mneme_schemas import load as load_schemas, normalize


_MANIFEST = Path(os.environ.get("MNEME_MANIFEST_PATH", "/manifest"))


def check(type_name: str, frontmatter: dict[str, Any]) -> list[str]:
    schemas = load_schemas(_MANIFEST)
    return schemas.validate(type_name, normalize(frontmatter))
