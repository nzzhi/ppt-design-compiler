from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

from pptx import Presentation
from pptx.util import Inches


SKILL_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = SKILL_ROOT.parents[2]
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from renderers import (
    render_comparison,
    render_conclusion,
    render_content,
    render_cover,
    render_process,
    render_timeline,
    render_data,
    render_image_story,
)
from renderers.base import RenderContext


Renderer = Callable[[RenderContext, dict[str, Any]], None]

RENDERERS: dict[str, Renderer] = {
    "cover": render_cover,
    "comparison": render_comparison,
    "process": render_process,
    "timeline": render_timeline,
    "data-insight": render_data,
    "summary": render_conclusion,
    "closing": render_conclusion,
    "conclusion": render_conclusion,
}


def _renderer_for(design_slide: dict[str, Any]) -> Renderer:
    page_type = design_slide["slide_type"]
    if page_type == "claim-evidence" and design_slide.get("visual_type") in {"photo", "illustration", "mixed"}:
        return render_image_story
    if page_type == "claim-evidence" and design_slide.get("visual_type") in {"chart", "table", "metric"}:
        return render_data
    if page_type == "data-insight":
        return render_data
    return RENDERERS.get(page_type, render_content)


def render_pptx(design_plan_path: str | Path, output_path: str | Path) -> Path:
    design_plan_path = Path(design_plan_path).resolve()
    output_path = Path(output_path).resolve()
    design_plan = _load_json(design_plan_path)
    if design_plan.get("schema_version") != "2.0.0":
        raise ValueError("Renderer requires design-plan schema_version 2.0.0")

    content_source = design_plan["content_source"]
    content_plan_path = (design_plan_path.parent / content_source["path"]).resolve()
    content_plan = _load_json(content_plan_path)
    design_system_path = design_plan_path.parent / "design-system.json"
    design_system = _load_json(design_system_path) if design_system_path.is_file() else {}

    presentation = Presentation()
    slide_size = content_plan.get("slide_size", {})
    presentation.slide_width = Inches(float(slide_size.get("width", 13.333)))
    presentation.slide_height = Inches(float(slide_size.get("height", 7.5)))
    context = RenderContext(presentation, design_plan, content_plan, design_system)

    for design_slide in design_plan["slides"]:
        renderer = _renderer_for(design_slide)
        renderer(context, design_slide)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    presentation.save(output_path)
    return output_path


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a PPTX from design-plan.json.")
    parser.add_argument("design_plan", help="Path to design-plan.json")
    parser.add_argument("output", help="Path to output .pptx")
    args = parser.parse_args()
    output_path = render_pptx(args.design_plan, args.output)
    print(f"Generated {output_path}")


if __name__ == "__main__":
    main()
