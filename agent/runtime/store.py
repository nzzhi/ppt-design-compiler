from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any


_PROJECT_ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,79}$")


class ProjectStore:
    """Durable, path-safe project state with atomic JSON writes."""

    def __init__(self, projects_root: str | Path, project_id: str):
        if not _PROJECT_ID.fullmatch(project_id):
            raise ValueError("project_id must contain 2-80 lowercase letters, numbers, or hyphens")
        self.projects_root = Path(projects_root).resolve()
        self.project_id = project_id
        self.root = (self.projects_root / project_id).resolve()
        if self.projects_root not in self.root.parents:
            raise ValueError("Project path escaped the configured projects root")
        for directory in ("input", "plan", "qa", "outputs", "revisions"):
            (self.root / directory).mkdir(parents=True, exist_ok=True)

    def write_json(self, relative_path: str | Path, document: dict[str, Any]) -> Path:
        path = self._path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as file:
            file.write(text)
            temporary = Path(file.name)
        os.replace(temporary, path)
        return path

    def read_json(self, relative_path: str | Path) -> dict[str, Any]:
        return json.loads(self._path(relative_path).read_text(encoding="utf-8"))

    def exists(self, relative_path: str | Path) -> bool:
        return self._path(relative_path).is_file()

    def output_path(self, version: int) -> Path:
        return self._path(f"outputs/presentation-v{version:03d}.pptx")

    def next_output_version(self) -> int:
        versions = []
        for path in (self.root / "outputs").glob("presentation-v*.pptx"):
            match = re.search(r"v(\d+)\.pptx$", path.name)
            if match:
                versions.append(int(match.group(1)))
        return max(versions, default=0) + 1

    def next_revision_id(self) -> str:
        numbers = []
        for path in (self.root / "revisions").glob("revision-*.json"):
            match = re.fullmatch(r"revision-(\d{3})\.json", path.name)
            if match:
                numbers.append(int(match.group(1)))
        return f"revision-{max(numbers, default=0) + 1:03d}"

    def _path(self, relative_path: str | Path) -> Path:
        path = (self.root / relative_path).resolve()
        if path != self.root and self.root not in path.parents:
            raise ValueError(f"Path escaped project root: {relative_path}")
        return path
