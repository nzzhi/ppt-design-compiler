from __future__ import annotations

import importlib.util
import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agent.core import validate_or_raise
from agent.skills.layout_engine import RenderPlanCompiler

from .providers import ContractGenerator, ModelProvider
from .store import ProjectStore
from .workflow import PresentationAgent, RevisionScope


@dataclass(frozen=True)
class RunResult:
    project_id: str
    status: str
    next_action: str
    project_path: Path
    output_path: Path | None = None
    qa_report_path: Path | None = None


class AgentRunner:
    """Connect intake, model planning, deterministic design, render, and QA."""

    def __init__(
        self,
        project_root: str | Path,
        provider: ModelProvider,
        *,
        projects_root: str | Path | None = None,
        max_model_attempts: int = 3,
    ):
        self.project_root = Path(project_root).resolve()
        self.projects_root = Path(projects_root or self.project_root / "projects").resolve()
        self.agent = PresentationAgent(self.project_root)
        self.generator = ContractGenerator(provider, max_attempts=max_model_attempts)

    def start(self, **intake_kwargs: Any) -> RunResult:
        intake = self.agent.intake(**intake_kwargs)
        store = ProjectStore(self.projects_root, intake.brief["project_id"])
        store.write_json("plan/brief.json", intake.brief)
        store.write_json(
            "input/session.json",
            {
                "status": intake.status,
                "next_action": intake.next_action,
                "selected_theme_id": intake.selected_theme_id,
            },
        )
        if intake.status != "ready_for_outline":
            return RunResult(
                project_id=store.project_id,
                status=intake.status,
                next_action=intake.next_action,
                project_path=store.root,
            )
        return self.prepare_outline(intake.brief)

    def run_brief(self, brief: dict[str, Any]) -> RunResult:
        """One-shot programmatic path for callers that waive outline confirmation."""
        prepared = self.prepare_outline(brief)
        if prepared.status != "awaiting_outline_confirmation":
            return prepared
        return self.confirm_outline(brief["project_id"])

    def prepare_outline(self, brief: dict[str, Any]) -> RunResult:
        validate_or_raise(brief, "brief", "1.0.0")
        store = ProjectStore(self.projects_root, brief["project_id"])
        store.write_json("plan/brief.json", brief)
        theme = self.agent.templates.select_theme(
            brief["use_case"], brief.get("style", {}).get("theme_hint", "auto")
        )
        design_system = self._design_system(brief["project_id"], theme.path)
        store.write_json("plan/design-system.json", design_system)

        outline = self.generator.generate(
            task="Create a concise presentation outline for confirmation before rendering.",
            payload={"brief": brief},
            contract_name="outline",
            contract_version="1.0.0",
        )
        store.write_json("plan/outline.json", outline)
        store.write_json(
            "input/session.json",
            {"status": "awaiting_outline_confirmation", "next_action": "confirm_outline"},
        )
        return RunResult(
            project_id=store.project_id,
            status="awaiting_outline_confirmation",
            next_action="confirm_outline",
            project_path=store.root,
        )

    def confirm_outline(self, project_id: str) -> RunResult:
        store = ProjectStore(self.projects_root, project_id)
        brief = store.read_json("plan/brief.json")
        outline = store.read_json("plan/outline.json")
        design_system = store.read_json("plan/design-system.json")
        slide_plan = self.generator.generate(
            task="Create a complete editable slide plan from the confirmed brief and outline. Do not invent evidence or numeric data.",
            payload={"brief": brief, "outline": outline, "design_system": design_system},
            contract_name="slide-plan",
            contract_version="1.0.0",
        )
        slide_plan = self._normalize_slide_plan(slide_plan, brief, design_system)
        validate_or_raise(slide_plan, "slide-plan", "1.0.0")
        store.write_json("plan/slide-plan.json", slide_plan)
        return self._compile_and_render(store, brief, slide_plan)

    def revise(self, project_id: str, request: str) -> RunResult:
        store = ProjectStore(self.projects_root, project_id)
        brief = store.read_json("plan/brief.json")
        original = store.read_json("plan/slide-plan.json")
        scope = self.agent.revision_scope(request, original)
        proposed = self.generator.generate(
            task=(
                "Revise the slide plan while preserving every unaffected slide exactly. "
                f"Allowed scope: {scope.type}; slide_ids={list(scope.slide_ids)}; element_ids={list(scope.element_ids)}."
            ),
            payload={"request": request, "slide_plan": original},
            contract_name="slide-plan",
            contract_version="1.0.0",
        )
        revised = self._enforce_revision_scope(original, proposed, scope)
        validate_or_raise(revised, "slide-plan", "1.0.0")
        revision_id = store.next_revision_id()
        store.write_json(f"revisions/{revision_id}-before.json", original)
        store.write_json(f"revisions/{revision_id}-candidate.json", revised)
        store.write_json("plan/slide-plan.json", revised)
        try:
            result = self._compile_and_render(store, brief, revised)
        except Exception:
            store.write_json("plan/slide-plan.json", original)
            raise
        if result.status != "complete":
            store.write_json("plan/slide-plan.json", original)
            return RunResult(
                project_id=project_id,
                status="revision_rejected",
                next_action="review_revision_qa",
                project_path=store.root,
                qa_report_path=result.qa_report_path,
            )
        changes = _changed_slides(original, revised)
        revision = {
            "schema_version": "1.0.0",
            "project_id": project_id,
            "revisions": [
                {
                    "revision_id": revision_id,
                    "requested_at": datetime.now(UTC).isoformat(),
                    "user_request": request,
                    "scope": {
                        "type": scope.type,
                        "slide_ids": list(scope.slide_ids),
                        "element_ids": list(scope.element_ids),
                    },
                    "changes": changes,
                    "outputs": {
                        "pptx_path": str(result.output_path or ""),
                        "preview_path": None,
                        "brief_path": str(store.root / "plan" / "brief.json"),
                    },
                }
            ],
        }
        validate_or_raise(revision, "revision-log", "1.0.0")
        store.write_json(f"revisions/{revision_id}.json", revision)
        return result

    def _compile_and_render(
        self,
        store: ProjectStore,
        brief: dict[str, Any],
        slide_plan: dict[str, Any],
    ) -> RunResult:
        qa_report = self.agent.content_qa(store.project_id, slide_plan)
        qa_path = store.write_json("qa/qa-report.json", qa_report)
        if qa_report["status"] == "fail":
            return RunResult(
                project_id=store.project_id,
                status="qa_failed",
                next_action="resolve_blocking_qa_issues",
                project_path=store.root,
                qa_report_path=qa_path,
            )

        planner = _load_symbol(
            self.project_root / "agent" / "skills" / "design-planner" / "planner.py",
            "ppt_agent_runtime_planner",
            "DesignPlanner",
        )
        design_plan = planner().plan(slide_plan, content_source_path="slide-plan.json")
        store.write_json("plan/design-plan.json", design_plan)
        render_plan = RenderPlanCompiler().compile(design_plan, slide_plan)
        store.write_json("plan/render-plan.json", render_plan)

        version = store.next_output_version()
        output_path = store.output_path(version)
        render_pptx = _load_symbol(
            self.project_root / "agent" / "skills" / "ppt-renderer" / "renderer.py",
            "ppt_agent_runtime_renderer",
            "render_pptx",
        )
        render_pptx(store.root / "plan" / "design-plan.json", output_path)
        qa_report["artifact"] = {
            "pptx_path": str(output_path),
            "slide_plan_path": str(store.root / "plan" / "slide-plan.json"),
            "preview_path": None,
        }
        qa_path = store.write_json("qa/qa-report.json", qa_report)
        store.write_json(
            "input/session.json",
            {"status": "complete", "next_action": "await_feedback", "output_version": version},
        )
        return RunResult(
            project_id=store.project_id,
            status="complete",
            next_action="await_feedback",
            project_path=store.root,
            output_path=output_path,
            qa_report_path=qa_path,
        )

    def _design_system(self, project_id: str, theme_path: Path) -> dict[str, Any]:
        theme = json.loads(theme_path.read_text(encoding="utf-8"))
        layouts = [layout["layout_id"] for layout in self.agent.templates.layouts()]
        fonts = theme.get("typography", {}).get("preferred_fonts", ["Microsoft YaHei"])
        system = {
            "schema_version": "1.0.0",
            "design_system_id": f"{project_id}.{theme['theme_id']}",
            "theme_id": theme["theme_id"],
            "slide_size": {"preset": "wide-16-9", "width": 13.333, "height": 7.5, "unit": "in"},
            "palette": deepcopy(theme["palette"]),
            "typography": {
                "title_font": fonts[0],
                "body_font": fonts[0],
                "min_body_size_pt": theme.get("typography", {}).get("min_body_size_pt", 16),
                "max_title_size_pt": theme.get("typography", {}).get("max_title_size_pt", 40),
            },
            "spacing": {"page_margin": 0.55, "block_gap": 0.18, "section_gap": 0.35},
            "layout_rules": {
                "density": theme.get("layout_rules", {}).get("density", "medium"),
                "grid": theme.get("layout_rules", {}).get("grid", "12-column"),
                "allowed_layout_ids": layouts,
                "avoid": theme.get("layout_rules", {}).get("avoid", []),
            },
        }
        validate_or_raise(system, "design-system", "1.0.0")
        return system

    @staticmethod
    def _normalize_slide_plan(
        slide_plan: dict[str, Any], brief: dict[str, Any], design_system: dict[str, Any]
    ) -> dict[str, Any]:
        normalized = deepcopy(slide_plan)
        normalized["schema_version"] = "1.0.0"
        normalized["deck_id"] = brief["project_id"]
        normalized["language"] = brief["language"]
        normalized["slide_size"] = deepcopy(design_system["slide_size"])
        normalized["design_system_id"] = design_system["design_system_id"]
        return normalized

    @staticmethod
    def _enforce_revision_scope(
        original: dict[str, Any], proposed: dict[str, Any], scope: RevisionScope
    ) -> dict[str, Any]:
        if scope.type == "deck":
            return proposed
        allowed_slides = set(scope.slide_ids)
        if scope.type == "elements":
            allowed_elements = set(scope.element_ids)
            for slide in original["slides"]:
                if any(
                    element.get("element_id", "").lower() in allowed_elements
                    for element in slide.get("editable_elements", [])
                ):
                    allowed_slides.add(slide["slide_id"])
        proposed_by_id = {slide["slide_id"]: slide for slide in proposed["slides"]}
        revised = deepcopy(original)
        revised["slides"] = [
            deepcopy(proposed_by_id.get(slide["slide_id"], slide))
            if slide["slide_id"] in allowed_slides
            else slide
            for slide in original["slides"]
        ]
        return revised


def _load_symbol(path: Path, module_name: str, symbol: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, symbol)


def _changed_slides(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    before_by_id = {slide["slide_id"]: slide for slide in before["slides"]}
    changes = []
    for slide in after["slides"]:
        previous = before_by_id.get(slide["slide_id"])
        if previous != slide:
            changes.append({"target": slide["slide_id"], "before": previous, "after": slide})
    return changes
