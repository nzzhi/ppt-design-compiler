from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover - exercised only in minimal environments
    Draft202012Validator = None

from .contracts import get_contract


def validate_document(document: dict[str, Any], name: str, version: str) -> list[str]:
    """Return deterministic, human-readable schema errors for a contract document."""
    contract = get_contract(name, version)
    schema = json.loads(contract.path.read_text(encoding="utf-8"))
    if Draft202012Validator is None:
        return _basic_validate(document, schema, name)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(document), key=lambda error: list(error.path))
    return [f"{_path(error.path)}: {error.message}" for error in errors]


def validate_or_raise(document: dict[str, Any], name: str, version: str) -> None:
    errors = validate_document(document, name, version)
    if errors:
        details = "\n".join(f"- {error}" for error in errors[:20])
        suffix = "\n- ..." if len(errors) > 20 else ""
        raise ValueError(f"Invalid {name}@{version}:\n{details}{suffix}")


def _path(parts: Any) -> str:
    path = "".join(f"[{part}]" if isinstance(part, int) else f".{part}" for part in parts)
    return path[1:] if path else "$"


def _basic_validate(document: dict[str, Any], schema: dict[str, Any], name: str) -> list[str]:
    """Keep the CLI usable without third-party packages; full validation is preferred."""
    errors = []
    if not isinstance(document, dict):
        return ["$: expected an object"]
    for field in schema.get("required", []):
        if field not in document:
            errors.append(f"$.{field}: required property")
    expected_version = schema.get("properties", {}).get("schema_version", {}).get("const")
    if expected_version is not None and document.get("schema_version") != expected_version:
        errors.append(f"$.schema_version: expected {expected_version!r}")
    if name == "layout-registry":
        for index, layout in enumerate(document.get("layouts", [])):
            for field in ("layout_id", "family", "slots", "density_budget", "typography_budget", "renderer_key"):
                if field not in layout:
                    errors.append(f"$.layouts[{index}].{field}: required property")
    if name in {"design-plan", "render-plan"}:
        for index, slide in enumerate(document.get("slides", [])):
            required = ("slide_id", "layout", "visual_type", "information_density") if name == "design-plan" else ("slide_id", "layout_id", "elements", "fit_status")
            for field in required:
                if field not in slide:
                    errors.append(f"$.slides[{index}].{field}: required property")
    return errors
