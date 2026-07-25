from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_KNOWLEDGE_ROOT = PROJECT_ROOT / "design-library" / "knowledge"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.core import upgrade_slide_plan_v1


class DesignPlanner:
    def __init__(self, knowledge_root: str | Path = DEFAULT_KNOWLEDGE_ROOT):
        root = Path(knowledge_root)
        self.page_rules = _index_by(
            _load_json(root / "page-type-rules.v1.json")["page_types"], "page_type"
        )
        self.layout_rules = _load_json(root / "layout-selection-rules.v1.json")["layout_rules"]
        self.layouts_by_id = _index_by(self.layout_rules, "layout_id")
        self.base_rules = _load_json(root / "base-design-rules.v1.json")
        self.ruleset_version = self.base_rules["ruleset_version"]

    def plan(
        self, slide_plan: dict[str, Any], content_source_path: str = "slide-plan.json"
    ) -> dict[str, Any]:
        semantic_plan = self._normalize_slide_plan(slide_plan)
        source_slides = semantic_plan["slides"]
        slides = [
            self._plan_slide(slide, source_slides[index - 1] if index else None, source_slides[index + 1] if index + 1 < len(source_slides) else None)
            for index, slide in enumerate(source_slides)
        ]
        self._apply_deck_rhythm(slides)
        return {
            "schema_version": "2.0.0",
            "deck_id": semantic_plan["deck_id"],
            "content_source": {
                "type": "slide-plan",
                "path": content_source_path,
                "schema_version": slide_plan["schema_version"],
            },
            "source_slide_plan_version": slide_plan["schema_version"],
            "design_system_id": semantic_plan["design_system_id"],
            "ruleset_version": self.ruleset_version,
            "deck_direction": self._deck_direction(semantic_plan, slides),
            "slides": slides,
        }

    def _normalize_slide_plan(self, slide_plan: dict[str, Any]) -> dict[str, Any]:
        version = slide_plan.get("schema_version")
        if version == "1.0.0":
            return upgrade_slide_plan_v1(slide_plan)
        if version == "2.0.0":
            return deepcopy(slide_plan)
        raise ValueError(f"Unsupported slide-plan version: {version}")

    def _plan_slide(
        self,
        slide: dict[str, Any],
        previous_slide: dict[str, Any] | None,
        next_slide: dict[str, Any] | None,
    ) -> dict[str, Any]:
        page_type = _page_type(slide)
        visual_type = _visual_type(slide, page_type)
        stats = _content_stats(slide["content"])
        page_rule = self.page_rules[page_type]
        density = _density_decision(stats, page_rule)
        layout = self._select_layout(slide, page_type, visual_type, stats)
        narrative = _narrative_decision(slide, page_type, previous_slide, next_slide, self.base_rules)
        hierarchy = _hierarchy_decision(slide, page_type, visual_type)
        composition = _composition_decision(slide, page_type, visual_type, density, self.base_rules)
        image_strategy = _image_strategy(slide, visual_type, composition)

        notes = list(page_rule["required_notes"])
        notes.extend(_visual_notes(visual_type, slide))
        if density["overflow_action"] != "none":
            notes.append(f"Resolve density with `{density['overflow_action']}` before rendering")

        return {
            "slide_id": slide["slide_id"],
            "slide_number": slide["slide_number"],
            "slide_type": page_type,
            "layout": layout,
            "visual_type": visual_type,
            "information_density": density,
            "narrative": narrative,
            "hierarchy": hierarchy,
            "composition": composition,
            "image_strategy": image_strategy,
            "design_notes": _unique(notes),
            "content_refs": [block["block_id"] for block in slide["content"]],
            "asset_requirements": _asset_requirements(slide, visual_type),
            "quality_constraints": _quality_constraints(page_type, visual_type),
        }

    def _select_layout(
        self,
        slide: dict[str, Any],
        page_type: str,
        visual_type: str,
        stats: dict[str, int],
    ) -> dict[str, Any]:
        preferred_ids = set(slide.get("layout_preferences", {}).get("preferred_layout_ids", []))
        candidates = []
        for rule in self.layout_rules:
            if page_type not in rule["page_types"] or visual_type not in rule["visual_types"]:
                continue
            score = 100
            reasons = [f"supports `{page_type}`", f"supports `{visual_type}`"]
            if rule["min_items"] <= stats["items"] <= rule["max_items"]:
                score += 20
                reasons.append("content item count fits")
            else:
                score -= abs(stats["items"] - rule["max_items"]) * 10
            if stats["characters"] <= rule["max_characters"]:
                score += 20
                reasons.append("text fits declared capacity")
            else:
                score -= min(stats["characters"] - rule["max_characters"], 100)
            if rule["layout_id"] in preferred_ids:
                score += 15
                reasons.append("preserves compatible v1 layout intent")
            candidates.append((score, rule, reasons))

        if not candidates:
            fallback = next(rule for rule in self.layout_rules if rule["layout_id"] == "content.title-body.v1")
            return {
                "layout_id": fallback["layout_id"],
                "family": fallback["family"],
                "selection_reason": "No exact rule matched; use the conservative text layout and flag for review.",
                "fallback_layout_ids": fallback["fallback_layout_ids"],
            }

        ranked = sorted(candidates, key=lambda item: (item[0], item[1]["layout_id"]), reverse=True)
        _, selected, reasons = ranked[0]
        return {
            "layout_id": selected["layout_id"],
            "family": selected["family"],
            "selection_reason": "; ".join(reasons),
            "fallback_layout_ids": deepcopy(selected["fallback_layout_ids"]),
            "alternatives": [item[1]["layout_id"] for item in ranked[1:3]],
        }

    def _apply_deck_rhythm(self, slides: list[dict[str, Any]]) -> None:
        max_repeat = self.base_rules["composition"]["max_repeated_layout_family"]
        for index in range(max_repeat, len(slides)):
            window = slides[index - max_repeat : index + 1]
            families = [slide["layout"]["family"] for slide in window]
            if len(set(families)) == 1:
                alternatives = slides[index]["layout"].get("alternatives", [])
                if alternatives:
                    alternate = self.layouts_by_id[alternatives[0]]
                    slides[index]["layout"]["layout_id"] = alternate["layout_id"]
                    slides[index]["layout"]["family"] = alternate["family"]
                    slides[index]["layout"]["selection_reason"] += "; selected alternate to vary the deck silhouette"
                    slides[index]["composition"]["variation_reason"] = "Break a repeated layout run while preserving the communication job"
                else:
                    slides[index]["design_notes"].append(
                        "Deck rhythm warning: change silhouette because this layout family repeats too often"
                    )
                    slides[index]["quality_constraints"].append("layout-family-repetition-must-be-resolved")

    def _deck_direction(
        self, semantic_plan: dict[str, Any], slides: list[dict[str, Any]]
    ) -> dict[str, str]:
        mode = semantic_plan["communication_job"]["deck_mode"]
        visual_count = sum(slide["visual_type"] != "typography" for slide in slides)
        arc = _narrative_arc(semantic_plan["slides"])
        return {
            "communication_mode": mode,
            "communication_job": _communication_job(semantic_plan),
            "narrative_arc": arc,
            "visual_strategy": f"Use evidence-led visuals on {visual_count} of {len(slides)} slides; keep visuals subordinate to the slide claim.",
            "hierarchy_strategy": "Create one dominant read per slide, then reveal the primary exhibit and supporting context in a deliberate order.",
            "image_strategy": "Use images as hero, evidence, context, or comparison; define crop and focal placement before layout selection, and avoid decorative thumbnail grids.",
            "layout_strategy": "Choose a composition by communication job, content relationship, and capacity; vary silhouette at narrative beats rather than for decoration.",
            "density_strategy": "Prefer low-to-medium density; shorten, change layout, or split before reducing typography below budget.",
            "rhythm_strategy": "Alternate text-led, visual-led, and transition silhouettes; do not repeat one layout family more than twice.",
        }


def _communication_job(plan: dict[str, Any]) -> str:
    job = plan["communication_job"]
    audience = ", ".join(job.get("audience", []))
    return f"By the end, {audience} should {job['audience_outcome']} because {job['central_takeaway']}"


def _narrative_arc(slides: list[dict[str, Any]]) -> list[str]:
    arc = []
    for slide in slides:
        role = slide["narrative_role"]
        if not arc or arc[-1] != role:
            arc.append(role)
    return arc


def _narrative_decision(
    slide: dict[str, Any],
    page_type: str,
    previous_slide: dict[str, Any] | None,
    next_slide: dict[str, Any] | None,
    rules: dict[str, Any],
) -> dict[str, str]:
    role = slide["narrative_role"]
    pacing = rules["narrative"]["pacing_by_role"].get(role, rules["narrative"]["pacing_by_role"]["default"])
    entry = "Open the deck and establish the central tension" if previous_slide is None else f"Build from: {previous_slide['key_message']}"
    exit_line = "Resolve the deck's opening promise" if next_slide is None else f"Create the need for: {next_slide['communication_goal']}"
    return {
        "communication_job": slide["communication_goal"],
        "primary_claim": slide["key_message"],
        "entry_logic": entry,
        "exit_logic": exit_line,
        "pacing": pacing,
    }


def _hierarchy_decision(slide: dict[str, Any], page_type: str, visual_type: str) -> dict[str, Any]:
    if page_type in {"cover", "section", "closing"}:
        dominant = "primary-claim"
        order = ["primary-claim", "supporting-line"]
    elif visual_type in {"chart", "metric", "photo", "illustration", "diagram", "mixed", "table"}:
        dominant = "primary-exhibit"
        order = ["action-title", "primary-exhibit", "supporting-context"]
    else:
        dominant = "action-title"
        order = ["action-title", "key-message", "supporting-content"]
    priorities = sorted({block.get("priority", 3) for block in slide["content"]})
    return {
        "dominant_element": dominant,
        "reading_order": order,
        "emphasis_levels": min(3, max(2, len(priorities) + 1)),
        "deemphasis": "Sources, captions, qualifiers, and repeated context",
    }


def _composition_decision(
    slide: dict[str, Any],
    page_type: str,
    visual_type: str,
    density: dict[str, Any],
    rules: dict[str, Any],
) -> dict[str, str]:
    silhouette = {
        "cover": "single-focal-field", "section": "single-focal-field", "closing": "single-focal-field",
        "comparison": "matched-split", "process": "directional-sequence", "timeline": "directional-sequence",
        "data-insight": "exhibit-dominant", "agenda": "staged-index", "summary": "synthesis-stack",
    }.get(page_type, "exhibit-dominant" if visual_type != "typography" else "editorial-stack")
    balance = "asymmetric" if silhouette in {"exhibit-dominant", "editorial-stack"} else "centered" if silhouette == "single-focal-field" else "structured"
    return {
        "silhouette": silhouette,
        "balance": balance,
        "reading_pattern": "center-out" if silhouette == "single-focal-field" else "left-to-right" if silhouette in {"matched-split", "directional-sequence"} else "z-pattern",
        "whitespace": rules["composition"]["whitespace_by_density"][density["level"]],
        "grouping": "Group by meaning and relationship; avoid equal card treatment for unrelated content",
        "contrast": "Use scale first, then weight or color; reserve the accent for the decisive point",
        "variation_reason": "Chosen to match this slide's communication job and content relationships",
    }


def _image_strategy(slide: dict[str, Any], visual_type: str, composition: dict[str, str]) -> dict[str, Any]:
    brief = slide["visual_brief"]
    uses_image = visual_type in {"photo", "illustration", "mixed"}
    role = "hero" if uses_image and composition["silhouette"] == "single-focal-field" else "evidence" if uses_image else "none"
    return {
        "use_image": uses_image,
        "role": role,
        "subject": brief.get("subject"),
        "aspect_ratio": brief.get("aspect_ratio", "auto"),
        "focal_position": brief.get("focal_position", "auto"),
        "crop_intent": "Preserve the focal subject and leave negative space for the title" if uses_image else "none",
        "treatment": brief.get("style_notes") or ("Use one strong image, not a collage" if uses_image else "No decorative image required"),
        "fallback": brief.get("fallback", "change-layout"),
    }


def _page_type(slide: dict[str, Any]) -> str:
    role = slide["narrative_role"]
    content_type = slide["content_type"]
    if role == "opening":
        return "cover"
    if role == "orientation":
        return "agenda"
    if role == "transition":
        return "section"
    if role == "comparison" or content_type == "comparison":
        return "comparison"
    if content_type == "process":
        return "process"
    if content_type == "timeline":
        return "timeline"
    if content_type in {"chart", "metric", "table"}:
        return "data-insight"
    if role in {"summary", "recommendation"}:
        return "summary"
    if role == "closing":
        return "closing"
    return "claim-evidence"


def _visual_type(slide: dict[str, Any], page_type: str) -> str:
    content_type = slide["content_type"]
    medium = slide["visual_brief"]["preferred_medium"]
    if content_type == "metric":
        return "metric"
    if content_type == "chart" or medium == "chart":
        return "chart"
    if content_type == "table" or medium == "table":
        return "table"
    if content_type == "quote":
        return "quote"
    if medium in {"photo", "illustration", "diagram", "mixed"}:
        return medium
    if page_type in {"process", "timeline", "comparison"}:
        return "diagram"
    return "typography"


def _content_stats(blocks: list[dict[str, Any]]) -> dict[str, int]:
    items = 0
    characters = 0
    for block in blocks:
        values = _block_values(block)
        items += len(values)
        characters += sum(len(str(value)) for value in values)
    return {"items": items, "characters": characters}


def _block_values(block: dict[str, Any]) -> list[Any]:
    for key in ("items", "steps", "rows"):
        if key in block:
            return block[key]
    if block.get("type") == "metric":
        return [block.get("value", ""), block.get("label", "")]
    if block.get("type") == "chart":
        return [block.get("insight", "")]
    if block.get("type") == "image":
        return [block.get("caption", "")]
    return [block]


def _density_decision(stats: dict[str, int], rule: dict[str, Any]) -> dict[str, Any]:
    item_ratio = stats["items"] / max(rule["max_items"], 1)
    char_ratio = stats["characters"] / max(rule["max_characters"], 1)
    ratio = max(item_ratio, char_ratio)
    if ratio <= 0.45:
        level = "sparse"
    elif ratio <= 0.7:
        level = "low"
    elif ratio <= 1:
        level = "medium"
    else:
        level = "high"
    overflow_action = "none"
    if ratio > 1.5:
        overflow_action = "split-slide"
    elif ratio > 1.2:
        overflow_action = "change-layout"
    elif ratio > 1:
        overflow_action = "shorten"
    return {
        "level": level,
        "content_items": stats["items"],
        "estimated_characters": stats["characters"],
        "max_content_items": rule["max_items"],
        "max_characters": rule["max_characters"],
        "overflow_action": overflow_action,
    }


def _visual_notes(visual_type: str, slide: dict[str, Any]) -> list[str]:
    notes = {
        "typography": ["Use scale, weight, and whitespace to create hierarchy; do not default to a bullet document"],
        "photo": ["Reserve a stable image frame and crop around the declared focal subject"],
        "illustration": ["Use one coherent illustration style across the deck"],
        "diagram": ["Use a simple directional structure; keep labels concise"],
        "chart": ["Give the chart the dominant evidence region and annotate the stated insight"],
        "table": ["Use alignment and selective emphasis instead of shrinking the table"],
        "metric": ["Make the metric the dominant read and keep context secondary"],
        "quote": ["Let the quotation dominate; keep attribution visibly subordinate"],
        "mixed": ["Choose one dominant visual and one supporting text region"],
    }
    result = list(notes[visual_type])
    purpose = slide.get("visual_brief", {}).get("purpose")
    if purpose:
        result.append(f"Visual purpose: {purpose}")
    return result


def _asset_requirements(slide: dict[str, Any], visual_type: str) -> list[dict[str, Any]]:
    if visual_type not in {"photo", "illustration", "chart", "table"}:
        return []
    brief = slide["visual_brief"]
    asset_type = {"chart": "chart-data", "table": "table-data"}.get(visual_type, visual_type)
    return [
        {
            "asset_role": "primary-visual",
            "asset_type": asset_type,
            "required": bool(brief.get("asset_required", True)),
            "aspect_ratio": brief.get("aspect_ratio", "auto"),
            "brief": brief.get("subject") or brief.get("purpose") or "Support the primary slide claim",
        }
    ]


def _quality_constraints(page_type: str, visual_type: str) -> list[str]:
    constraints = ["title-must-not-overflow", "body-font-at-least-16pt", "no-unintended-overlap"]
    if page_type not in {"cover", "section"}:
        constraints.append("action-title-must-state-takeaway")
    if visual_type == "chart":
        constraints.extend(["chart-must-have-insight", "chart-data-source-required"])
    if visual_type in {"photo", "illustration"}:
        constraints.append("visual-must-support-claim")
    return constraints


def _index_by(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {item[key]: item for item in items}


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a design-plan from a slide-plan.")
    parser.add_argument("slide_plan", help="Input slide-plan v1 or v2 JSON")
    parser.add_argument("output", help="Output design-plan JSON")
    parser.add_argument("--knowledge-root", default=str(DEFAULT_KNOWLEDGE_ROOT))
    args = parser.parse_args()

    source = _load_json(Path(args.slide_plan))
    design_plan = DesignPlanner(args.knowledge_root).plan(source)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(design_plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {output}")


if __name__ == "__main__":
    main()
