"""Schema loader + validator for Mneme knowledge files.

The manifest repo ships JSON Schema definitions under `manifest/schemas/`.
This module loads them, sets up a `referencing` registry so the per-type
schemas can `$ref` `_core.schema.json`, and exposes a `validate(type, doc)`
function used by the index-sync parser and the validator service.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012


def normalize(value: Any) -> Any:
    """Coerce dates/datetimes to ISO strings so JSON Schema string-typed
    fields (with format: date / date-time) accept YAML-loaded date literals.
    Recursive; safe to call on any frontmatter dict.
    """
    if isinstance(value, _dt.datetime):
        return value.isoformat()
    if isinstance(value, _dt.date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: normalize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize(v) for v in value]
    return value


DEFAULT_MANIFEST_PATH = Path(
    os.environ.get("MNEME_MANIFEST_PATH", "/manifest")
)


class SchemaError(Exception):
    pass


@lru_cache(maxsize=1)
def _load_schemas(manifest_path: str) -> tuple[Registry, dict[str, dict[str, Any]]]:
    base = Path(manifest_path) / "schemas"
    if not base.exists():
        raise SchemaError(f"Manifest schemas directory not found: {base}")

    files = {p.name: json.loads(p.read_text()) for p in base.glob("*.schema.json")}
    if "_core.schema.json" not in files:
        raise SchemaError("_core.schema.json is required")

    resources = []
    for fname, doc in files.items():
        uri = f"_core.schema.json" if fname == "_core.schema.json" else fname
        resources.append((uri, Resource(contents=doc, specification=DRAFT202012)))

    registry = Registry().with_resources(resources)

    by_type: dict[str, dict[str, Any]] = {}
    for fname, doc in files.items():
        if fname == "_core.schema.json":
            continue
        # Derive type name from filename: "brand-strategy.schema.json" -> "brand-strategy"
        type_name = fname.replace(".schema.json", "")
        by_type[type_name] = doc

    return registry, by_type


def load(manifest_path: Path | str = DEFAULT_MANIFEST_PATH) -> "SchemaSet":
    registry, by_type = _load_schemas(str(manifest_path))
    return SchemaSet(registry=registry, schemas=by_type)


class SchemaSet:
    def __init__(self, registry: Registry, schemas: dict[str, dict[str, Any]]):
        self._registry = registry
        self._schemas = schemas

    def types(self) -> list[str]:
        return sorted(self._schemas.keys())

    def validate(self, type_name: str, doc: dict[str, Any]) -> list[str]:
        """Return a list of error messages, empty if valid."""
        if type_name not in self._schemas:
            return [f"unknown type '{type_name}' (valid: {self.types()})"]
        validator = Draft202012Validator(
            self._schemas[type_name],
            registry=self._registry,
        )
        normalized = normalize(doc)
        errors = []
        for err in sorted(validator.iter_errors(normalized), key=lambda e: list(e.absolute_path)):
            path = "/".join(str(p) for p in err.absolute_path) or "(root)"
            errors.append(f"{path}: {err.message}")
        return errors


__all__ = ["load", "SchemaSet", "SchemaError", "normalize"]
