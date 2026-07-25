from __future__ import annotations

from pptx.enum.text import MSO_ANCHOR
from pptx.util import Inches

from .base import RenderContext


def render_cover(ctx: RenderContext, design_slide: dict) -> None:
    content = ctx.content_for(design_slide)
    slide = ctx.blank_slide()

    accent = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(0.22), Inches(7.5))
    accent.fill.solid()
    accent.fill.fore_color.rgb = ctx.color("accent_primary")
    accent.line.fill.background()

    ctx.add_text(
        slide,
        "COURSE REPORT",
        0.92,
        0.85,
        3.2,
        0.3,
        size=11,
        color="accent_primary",
        bold=True,
    )
    ctx.add_text(
        slide,
        content["title"],
        0.9,
        1.55,
        8.6,
        2.25,
        size=46 if len(content["title"]) <= 18 else 40,
        bold=True,
        font=ctx.title_font,
        valign=MSO_ANCHOR.MIDDLE,
    )
    ctx.add_text(
        slide,
        content["key_message"],
        0.94,
        4.12,
        7.8,
        0.86,
        size=19,
        color="text_secondary",
    )

    marker = slide.shapes.add_shape(1, Inches(10.55), Inches(1.3), Inches(1.9), Inches(4.85))
    marker.fill.solid()
    marker.fill.fore_color.rgb = ctx.color("surface")
    marker.line.fill.background()
    ctx.add_text(slide, "AI", 10.7, 2.15, 1.55, 1.0, size=54, color="accent_primary", bold=True)
    ctx.add_text(slide, "×", 11.1, 3.18, 0.7, 0.65, size=32, color="accent_secondary", bold=True)
    ctx.add_text(slide, "R&D", 10.7, 4.0, 1.55, 0.72, size=25, color="text_primary", bold=True)
    ctx.add_footer(slide)
