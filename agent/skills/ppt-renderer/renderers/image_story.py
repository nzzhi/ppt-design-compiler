from __future__ import annotations

from pathlib import Path

from pptx.enum.text import PP_ALIGN
from pptx.util import Inches

from .base import RenderContext, content_items


def render_image_story(ctx: RenderContext, design_slide: dict) -> None:
    content = ctx.content_for(design_slide)
    slide = ctx.blank_slide()
    ctx.add_title(slide, content["title"], design_slide["slide_number"])
    ctx.add_key_message(slide, content["key_message"])
    frame_x, frame_y, frame_w, frame_h = 0.8, 2.15, 7.35, 4.25
    asset = _find_asset(content, design_slide)
    if asset:
        slide.shapes.add_picture(str(asset), Inches(frame_x), Inches(frame_y), width=Inches(frame_w), height=Inches(frame_h))
    else:
        ctx.add_panel(slide, frame_x, frame_y, frame_w, frame_h, fill="surface")
        ctx.add_text(slide, "VISUAL EVIDENCE", frame_x + 0.35, frame_y + 0.35, 2.3, 0.28, size=11, color="accent_primary", bold=True)
        ctx.add_text(slide, design_slide.get("image_strategy", {}).get("treatment", "Image asset required"), frame_x + 0.55, frame_y + 1.45, frame_w - 1.1, 0.9, size=18, color="text_secondary", align=PP_ALIGN.CENTER)
    ctx.add_text(slide, "主视觉", frame_x + 0.35, frame_y + frame_h - 0.55, 1.0, 0.25, size=10, color="background" if asset else "accent_secondary", bold=True)
    ctx.add_text(slide, content["key_message"], 8.65, 2.55, 3.55, 1.6, size=25, color="text_primary", bold=True)
    items = content_items(content)[:3]
    for index, item in enumerate(items):
        ctx.add_text(slide, item, 8.7, 4.45 + index * 0.55, 3.4, 0.42, size=14, color="text_secondary")
    ctx.add_footer(slide)


def _find_asset(content: dict, design_slide: dict) -> Path | None:
    candidates = []
    for asset in content.get("assets", []):
        if isinstance(asset, str):
            candidates.append(asset)
        elif isinstance(asset, dict):
            candidates.extend(asset.get(key) for key in ("path", "file", "source") if asset.get(key))
    for req in design_slide.get("asset_requirements", []):
        if req.get("path"):
            candidates.append(req["path"])
    base_dir = Path(content.get("_base_dir", "."))
    for candidate in candidates:
        path = Path(candidate)
        if not path.is_absolute():
            path = base_dir / path
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".gif"}:
            return path
    return None
