from __future__ import annotations

from .base import RenderContext, content_items


def render_conclusion(ctx: RenderContext, design_slide: dict) -> None:
    content = ctx.content_for(design_slide)
    slide = ctx.blank_slide()
    ctx.add_text(slide, "CONCLUSION", 0.82, 0.62, 2.2, 0.3, size=11, color="accent_primary", bold=True)
    ctx.add_text(slide, content["title"], 0.8, 1.25, 11.6, 0.9, size=32, color="text_primary", bold=True, font=ctx.title_font)
    ctx.add_text(slide, content["key_message"], 0.82, 2.45, 10.9, 1.2, size=25, color="accent_primary", bold=True)
    items = content_items(content)
    for index, item in enumerate(items[:4]):
        y = 4.25 + index * 0.58
        ctx.add_text(slide, f"{index + 1:02d}", 0.86, y, 0.5, 0.34, size=12, color="accent_secondary", bold=True)
        ctx.add_text(slide, item, 1.62, y - 0.02, 9.9, 0.42, size=16, color="text_primary")
    ctx.add_footer(slide, "FINAL MESSAGE")
