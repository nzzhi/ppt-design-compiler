from __future__ import annotations

from pptx.util import Inches

from .base import RenderContext, split_comparison


def render_comparison(ctx: RenderContext, design_slide: dict) -> None:
    content = ctx.content_for(design_slide)
    slide = ctx.blank_slide()
    ctx.add_title(slide, content["title"], design_slide["slide_number"])
    ctx.add_key_message(slide, content["key_message"])
    left, right = split_comparison(content)

    divider = slide.shapes.add_shape(1, Inches(6.65), Inches(2.2), Inches(0.025), Inches(4.2))
    divider.fill.solid()
    divider.fill.fore_color.rgb = ctx.color("divider")
    divider.line.fill.background()
    _render_side(ctx, slide, left, 0.82, "accent_primary", "A")
    _render_side(ctx, slide, right, 6.98, "accent_secondary", "B")
    ctx.add_footer(slide)


def _render_side(ctx: RenderContext, slide, items: list[str], x: float, accent: str, marker: str) -> None:
    title = items[0] if items else "待补充"
    ctx.add_text(slide, marker, x, 2.28, 0.42, 0.35, size=11, color=accent, bold=True)
    ctx.add_text(slide, title, x, 2.72, 5.1, 0.62, size=25, color=accent, bold=True)
    for index, item in enumerate(items[1:5]):
        y = 3.62 + index * 0.75
        ctx.add_text(slide, "—", x, y, 0.35, 0.35, size=16, color=accent, bold=True)
        ctx.add_text(slide, item, x + 0.48, y - 0.02, 4.65, 0.58, size=17, color="text_primary")
