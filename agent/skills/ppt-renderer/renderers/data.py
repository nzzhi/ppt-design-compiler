from __future__ import annotations

from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches

from .base import RenderContext, content_items


def render_data(ctx: RenderContext, design_slide: dict) -> None:
    content = ctx.content_for(design_slide)
    slide = ctx.blank_slide()
    ctx.add_title(slide, content["title"], design_slide["slide_number"])
    ctx.add_key_message(slide, content["key_message"])
    visual_type = design_slide.get("visual_type", "chart")
    if visual_type == "metric":
        _render_metric(ctx, slide, content)
    elif visual_type == "table":
        _render_table(ctx, slide, content)
    else:
        _render_chart(ctx, slide, content)
    ctx.add_footer(slide)


def _render_metric(ctx, slide, content):
    items = content_items(content)
    value = items[0] if items else "-"
    label = items[1] if len(items) > 1 else content["key_message"]
    ctx.add_panel(slide, 0.95, 2.2, 5.1, 3.5, fill="surface")
    ctx.add_text(slide, value, 1.35, 2.8, 4.3, 1.2, size=54, color="accent_primary", bold=True, align=PP_ALIGN.CENTER)
    ctx.add_text(slide, label, 1.35, 4.25, 4.3, 0.7, size=20, color="text_primary", bold=True, align=PP_ALIGN.CENTER)
    ctx.add_text(slide, content["key_message"], 6.8, 2.75, 5.0, 1.6, size=24, color="text_primary", bold=True)


def _render_chart(ctx, slide, content):
    items = content_items(content)[:5]
    values = [max(18, 82 - index * 12) for index in range(max(len(items), 1))]
    base_y = 5.85
    for index, value in enumerate(values):
        x = 1.05 + index * 1.05
        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(base_y - value / 22), Inches(0.62), Inches(value / 22))
        bar.fill.solid(); bar.fill.fore_color.rgb = ctx.color("accent_primary" if index < len(values) - 1 else "accent_secondary"); bar.line.fill.background()
        label = items[index][:14] if index < len(items) else f"{index + 1}"
        ctx.add_text(slide, label, x - 0.25, 6.05, 1.1, 0.45, size=10, color="text_secondary", align=PP_ALIGN.CENTER)
    ctx.add_text(slide, "KEY FINDING", 7.15, 2.55, 2.4, 0.3, size=11, color="accent_secondary", bold=True)
    ctx.add_text(slide, content["key_message"], 7.15, 3.05, 4.75, 1.65, size=25, color="text_primary", bold=True)


def _render_table(ctx, slide, content):
    items = content_items(content)[:6]
    ctx.add_panel(slide, 0.9, 2.25, 7.2, 3.9, fill="surface")
    for index, item in enumerate(items):
        y = 2.6 + index * 0.53
        ctx.add_text(slide, f"{index + 1:02d}", 1.15, y, 0.55, 0.3, size=11, color="accent_primary", bold=True)
        ctx.add_text(slide, item, 1.9, y - 0.02, 5.85, 0.38, size=15, color="text_primary")
    ctx.add_text(slide, content["key_message"], 8.65, 3.0, 3.35, 1.85, size=23, color="text_primary", bold=True)
