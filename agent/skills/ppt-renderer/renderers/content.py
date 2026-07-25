from __future__ import annotations

from pptx.enum.text import PP_ALIGN
from pptx.util import Inches

from .base import RenderContext, content_items


def render_content(ctx: RenderContext, design_slide: dict) -> None:
    content = ctx.content_for(design_slide)
    slide = ctx.blank_slide()
    ctx.add_title(slide, content["title"], design_slide["slide_number"])
    ctx.add_key_message(slide, content["key_message"])
    items = content_items(content)

    if design_slide["slide_type"] == "agenda":
        _render_agenda(ctx, slide, items)
    elif design_slide["layout"]["family"] == "claim-evidence" and design_slide["visual_type"] != "typography":
        _render_visual_claim(ctx, slide, items, design_slide["visual_type"], content)
    else:
        _render_typographic_claim(ctx, slide, items)
    ctx.add_footer(slide)


def _render_agenda(ctx: RenderContext, slide, items: list[str]) -> None:
    for index, item in enumerate(items[:6]):
        y = 2.18 + index * 0.72
        ctx.add_text(slide, f"{index + 1:02d}", 0.85, y, 0.55, 0.42, size=18, color="accent_primary", bold=True)
        ctx.add_text(slide, item, 1.55, y - 0.01, 9.9, 0.5, size=20, color="text_primary")
        rule = slide.shapes.add_shape(1, Inches(1.55), Inches(y + 0.5), Inches(9.9), Inches(0.01))
        rule.fill.solid()
        rule.fill.fore_color.rgb = ctx.color("divider")
        rule.line.fill.background()


def _render_visual_claim(
    ctx: RenderContext, slide, items: list[str], visual_type: str, content: dict
) -> None:
    visual_bg = slide.shapes.add_shape(1, Inches(0.75), Inches(2.15), Inches(7.2), Inches(4.45))
    visual_bg.fill.solid()
    visual_bg.fill.fore_color.rgb = ctx.color("surface")
    visual_bg.line.fill.background()
    ctx.add_text(slide, visual_type.upper(), 1.05, 2.48, 1.8, 0.25, size=9, color="accent_primary", bold=True)

    for index, item in enumerate(items[:4]):
        y = 2.92 + index * 0.78
        ctx.add_text(slide, f"{index + 1}", 1.08, y, 0.48, 0.48, size=20, color="accent_primary", bold=True, align=PP_ALIGN.CENTER)
        ctx.add_text(slide, item, 1.72, y, 5.75, 0.58, size=16, color="text_primary")

    ctx.add_text(slide, "本页回答", 8.45, 2.34, 2.0, 0.35, size=13, color="accent_secondary", bold=True)
    ctx.add_text(slide, content["key_message"], 8.45, 2.88, 3.75, 1.75, size=22, color="text_primary", bold=True)
    ctx.add_text(slide, content.get("question", ""), 8.45, 5.05, 3.45, 0.85, size=14, color="text_secondary")


def _render_typographic_claim(ctx: RenderContext, slide, items: list[str]) -> None:
    ctx.add_text(slide, "要点", 0.9, 2.25, 1.0, 0.35, size=12, color="accent_secondary", bold=True)
    for index, item in enumerate(items[:5]):
        y = 2.78 + index * 0.72
        ctx.add_text(slide, f"{index + 1}", 0.9, y, 0.42, 0.42, size=18, color="accent_primary", bold=True)
        ctx.add_text(slide, item, 1.55, y - 0.02, 10.45, 0.54, size=19, color="text_primary")
