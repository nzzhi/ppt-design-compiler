from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class TemplateRecord:
    theme_id: str
    name: str
    path: Path
    use_cases: tuple[str, ...]
    audience: tuple[str, ...]
    default_slide_types: tuple[str, ...]


@dataclass(frozen=True)
class Capability:
    name: str
    description: str
    operations: tuple[str, ...]


class TemplateCatalog:
    """Discover file-backed themes and executable layout registries."""

    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root)
        self.theme_root = self.project_root / "design-library" / "themes"
        self.layout_registry_path = self.project_root / "design-library" / "layouts" / "layout-registry.v2.json"

    def themes(self) -> tuple[TemplateRecord, ...]:
        records = []
        for path in sorted(self.theme_root.glob("*.json")):
            data = _read_json(path)
            records.append(
                TemplateRecord(
                    theme_id=data["theme_id"],
                    name=data["name"],
                    path=path,
                    use_cases=tuple(data.get("use_cases", [])),
                    audience=tuple(data.get("audience", [])),
                    default_slide_types=tuple(data.get("default_slide_types", [])),
                )
            )
        return tuple(records)

    def select_theme(self, use_case: str, requested_theme: str | None = None) -> TemplateRecord:
        records = self.themes()
        if requested_theme and requested_theme != "auto":
            for record in records:
                if record.theme_id == requested_theme:
                    return record
            raise ValueError(f"Unknown theme: {requested_theme}")

        preferred = {
            "classroom": "academic-defense.v1",
            "defense": "academic-defense.v1",
            "roadshow": "tech-roadshow.v1",
            "client_briefing": "business-report.v1",
            "work_report": "business-report.v1",
        }.get(use_case, "business-report.v1")
        for record in records:
            if record.theme_id == preferred:
                return record
        if not records:
            raise FileNotFoundError(f"No theme files found in {self.theme_root}")
        return records[0]

    def layouts(self) -> tuple[dict[str, Any], ...]:
        registry = _read_json(self.layout_registry_path)
        return tuple(registry["layouts"])


class SkillRegistry:
    """Register optional local or remote abilities without coupling the pipeline."""

    def __init__(self):
        self._entries: dict[str, tuple[Capability, Callable[..., Any] | None]] = {}

    def register(
        self, capability: Capability, handler: Callable[..., Any] | None = None
    ) -> None:
        if capability.name in self._entries:
            raise ValueError(f"Capability already registered: {capability.name}")
        self._entries[capability.name] = (capability, handler)

    def capabilities(self) -> tuple[Capability, ...]:
        return tuple(entry[0] for entry in self._entries.values())

    def invoke(self, name: str, operation: str, **kwargs: Any) -> Any:
        try:
            capability, handler = self._entries[name]
        except KeyError as error:
            raise ValueError(f"Unknown capability: {name}") from error
        if operation not in capability.operations:
            raise ValueError(f"Unsupported operation for {name}: {operation}")
        if handler is None:
            raise RuntimeError(f"Capability {name} is registered but has no runtime handler")
        return handler(operation=operation, **kwargs)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
