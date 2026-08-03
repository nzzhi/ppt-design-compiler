from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from agent.core.validation import validate_or_raise


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY = PROJECT_ROOT / "design-library" / "layouts" / "layout-registry.v2.json"


class RenderPlanCompiler:
    """Resolve design decisions into stable frames and element bindings."""

    def __init__(self, registry_path: str | Path = DEFAULT_REGISTRY):
        self.registry_path = Path(registry_path)
        self.registry = _load_json(self.registry_path)
        validate_or_raise(self.registry, "layout-registry", "2.0.0")
        self.layouts = {layout["layout_id"]: layout for layout in self.registry["layouts"]}

    def compile(self, design_plan: dict[str, Any], content_plan: dict[str, Any]) -> dict[str, Any]:
        validate_or_raise(design_plan, "design-plan", "2.0.0")
        content_by_id = {slide["slide_id"]: slide for slide in content_plan["slides"]}
        slides = []
        for design_slide in design_plan["slides"]:
            content = content_by_id.get(design_slide["slide_id"], {})
            layout = self._select_layout(design_slide)
            density = design_slide["information_density"]
            fit_status = "warning" if density.get("overflow_action", "none") != "none" else "pass"
            fit_issues = [] if fit_status == "pass" else [density["overflow_action"]]
            slides.append(
                {
                    "slide_id": design_slide["slide_id"],
                    "layout_id": layout["layout_id"],
                    "layout_score": self._score(design_slide, layout),
                    "selection_reasons": [design_slide["layout"]["selection_reason"], "resolved by registry"],
                    "elements": self._bind_elements(design_slide, content, layout),
                    "fit_status": fit_status,
                    "fit_issues": fit_issues,
                }
            )
        render_plan = {
            "schema_version": "2.0.0",
            "deck_id": design_plan["deck_id"],
            "source_slide_plan_version": design_plan["source_slide_plan_version"],
            "design_system_id": design_plan["design_system_id"],
            "layout_registry_id": self.registry["registry_id"],
            "slides": slides,
        }
        validate_or_raise(render_plan, "render-plan", "2.0.0")
        return render_plan

    def _select_layout(self, design_slide: dict[str, Any]) -> dict[str, Any]:
        preferred_family = design_slide["layout"].get("family", "")
        candidates = [layout for layout in self.layouts.values() if layout["family"] == preferred_family]
        if not candidates:
            candidates = list(self.layouts.values())
        visual_type = design_slide.get("visual_type")
        exact = [layout for layout in candidates if visual_type in layout["compatible_visual_types"]]
        return deepcopy((exact or candidates)[0])

    @staticmethod
    def _score(design_slide: dict[str, Any], layout: dict[str, Any]) -> float:
        score = 100.0
        if design_slide.get("visual_type") in layout["compatible_visual_types"]:
            score += 10
        if design_slide["information_density"]["level"] == layout["density_budget"]["level"]:
            score += 5
        return score

    @staticmethod
    def _bind_elements(design_slide: dict[str, Any], content: dict[str, Any], layout: dict[str, Any]) -> list[dict[str, Any]]:
        refs = {
            "title": design_slide["slide_id"],
            "key-message": design_slide["slide_id"],
            "body": design_slide["content_refs"][0],
            "visual": design_slide["content_refs"][0],
        }
        elements = []
        for index, slot in enumerate(layout["slots"]):
            content_ref = refs.get(slot["role"])
            if slot["role"] == "visual" and design_slide.get("visual_type") == "typography":
                continue
            elements.append(
                {
                    "element_id": f"el-{design_slide['slide_id'][6:]}-{slot['slot_id'][5:]}",
                    "slot_id": slot["slot_id"],
                    "element_type": "text" if slot["role"] in {"title", "key-message", "body"} else "shape",
                    "content_ref": content_ref,
                    "frame": {**slot["frame"], "unit": "px"},
                    "style_ref": slot["style_ref"],
                    "z_order": index,
                }
            )
        return elements


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
