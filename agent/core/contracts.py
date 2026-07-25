from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


SCHEMA_ROOT = Path(__file__).resolve().parents[1] / "schemas"


@dataclass(frozen=True)
class ContractRef:
    name: str
    version: str
    path: Path


_CONTRACTS = {
    ("brief", "1.0.0"): SCHEMA_ROOT / "brief.schema.json",
    ("outline", "1.0.0"): SCHEMA_ROOT / "outline.schema.json",
    ("design-system", "1.0.0"): SCHEMA_ROOT / "design-system.schema.json",
    ("slide-plan", "1.0.0"): SCHEMA_ROOT / "slide-plan.schema.json",
    ("qa-report", "1.0.0"): SCHEMA_ROOT / "qa-report.schema.json",
    ("revision-log", "1.0.0"): SCHEMA_ROOT / "revision-log.schema.json",
    ("design-system", "2.0.0"): SCHEMA_ROOT / "v2" / "design-system.schema.json",
    ("slide-plan", "2.0.0"): SCHEMA_ROOT / "v2" / "slide-plan.schema.json",
    ("design-plan", "2.0.0"): SCHEMA_ROOT / "v2" / "design-plan.schema.json",
    ("layout-registry", "2.0.0"): SCHEMA_ROOT / "v2" / "layout-registry.schema.json",
    ("render-plan", "2.0.0"): SCHEMA_ROOT / "v2" / "render-plan.schema.json",
}


def get_contract(name: str, version: str) -> ContractRef:
    try:
        path = _CONTRACTS[(name, version)]
    except KeyError as error:
        raise ValueError(f"Unknown contract: {name}@{version}") from error
    if not path.is_file():
        raise FileNotFoundError(path)
    return ContractRef(name=name, version=version, path=path)


def list_contracts() -> tuple[ContractRef, ...]:
    return tuple(
        ContractRef(name=name, version=version, path=path)
        for (name, version), path in sorted(_CONTRACTS.items())
    )
