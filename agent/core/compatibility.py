from __future__ import annotations

from copy import deepcopy
from typing import Any


_NARRATIVE_ROLE = {
    "cover": "opening",
    "section": "transition",
    "agenda": "orientation",
    "summary": "summary",
    "closing": "closing",
    "comparison": "comparison",
}

_CONTENT_TYPE = {
    "cover": "headline",
    "section": "headline",
    "agenda": "bullet-list",
    "summary": "bullet-list",
    "content": "bullet-list",
    "big-number": "metric",
    "comparison": "comparison",
    "timeline": "timeline",
    "process": "process",
    "chart": "chart",
    "image": "image",
    "quote": "quote",
    "closing": "headline",
}


def upgrade_slide_plan_v1(plan: dict[str, Any]) -> dict[str, Any]:
    """Create a semantic v2 plan without mutating the v1 source.

    The adapter preserves information but does not invent evidence, assets, or
    visual claims. Phase 2 can enrich the resulting semantic plan.
    """
    if plan.get("schema_version") != "1.0.0":
        raise ValueError("Expected slide-plan schema_version 1.0.0")

    slides = [_upgrade_slide(slide) for slide in plan.get("slides", [])]
    if not slides:
        raise ValueError("A slide plan must contain at least one slide")

    central_takeaway = slides[-1]["key_message"]
    return {
        "schema_version": "2.0.0",
        "deck_id": plan["deck_id"],
        "language": plan["language"],
        "communication_job": {
            "audience": ["unspecified audience"],
            "audience_outcome": central_takeaway,
            "central_takeaway": central_takeaway,
            "deck_mode": "structured-argument",
        },
        "design_system_id": plan["design_system_id"],
        "global_constraints": deepcopy(plan.get("global_constraints", [])),
        "slides": slides,
    }


def _upgrade_slide(slide: dict[str, Any]) -> dict[str, Any]:
    slide_type = slide.get("slide_type", "content")
    content_type = _CONTENT_TYPE.get(slide_type, "mixed")
    return {
        "slide_id": slide["slide_id"],
        "slide_number": slide["slide_number"],
        "narrative_role": _NARRATIVE_ROLE.get(slide_type, "explanation"),
        "content_type": content_type,
        "communication_goal": slide.get("question") or slide["key_message"],
        "action_title": slide["title"],
        "key_message": slide["key_message"],
        "content": _upgrade_content(slide.get("content_blocks", []), content_type),
        "evidence": [],
        "visual_brief": _upgrade_visual_brief(slide),
        "layout_preferences": {
            "preferred_families": [slide_type],
            "avoid_families": [],
            "preferred_layout_ids": [slide["layout_id"]] if slide.get("layout_id") else [],
        },
        "density_budget": {
            "level": "medium",
            "max_body_characters": _character_count(slide.get("content_blocks", [])),
            "max_content_items": max(_item_count(slide.get("content_blocks", [])), 1),
            "min_body_size_pt": 16,
        },
        "speaker_notes": slide.get("speaker_notes", ""),
        "constraints": deepcopy(slide.get("constraints", [])),
        "revision_history": deepcopy(slide.get("revision_history", [])),
    }


def _upgrade_content(blocks: list[dict[str, Any]], content_type: str) -> list[dict[str, Any]]:
    upgraded = []
    for block in blocks:
        raw = block.get("content", "")
        items = [str(item) for item in raw] if isinstance(raw, list) else [str(raw)]
        upgraded.append(
            {
                "block_id": block["block_id"],
                "type": "quote" if content_type == "quote" else "bullet-list",
                "priority": block.get("priority", 3),
                "source_ids": deepcopy(block.get("source_asset_ids", [])),
                "items": items,
            }
        )
    return upgraded or [{"block_id": "block-fallback", "type": "paragraph", "priority": 5, "source_ids": [], "items": [""]}]


def _upgrade_visual_brief(slide: dict[str, Any]) -> dict[str, Any]:
    visual_type = slide.get("visual_intent", {}).get("type", "text")
    medium = {
        "image": "photo",
        "chart": "chart",
        "process": "diagram",
        "timeline": "diagram",
        "comparison": "diagram",
        "mixed": "mixed",
    }.get(visual_type, "none")
    return {
        "purpose": slide.get("key_message", "Support the slide claim"),
        "preferred_medium": medium,
        "asset_required": medium in {"photo", "illustration", "chart"},
        "subject": None,
        "aspect_ratio": "auto",
        "focal_position": "auto",
        "style_notes": "",
        "fallback": "change-layout",
    }


def _character_count(blocks: list[dict[str, Any]]) -> int:
    return sum(len(str(item)) for block in blocks for item in _as_items(block.get("content", "")))


def _item_count(blocks: list[dict[str, Any]]) -> int:
    return sum(len(_as_items(block.get("content", ""))) for block in blocks)


def _as_items(value: Any) -> list[Any]:
    return value if isinstance(value, list) else [value]
