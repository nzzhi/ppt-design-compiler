from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
import re

from .catalog import Capability, SkillRegistry, TemplateCatalog


_SLIDE_REFERENCE = re.compile(r"(?:slide[-\s]?(\d{1,3})|第\s*(\d{1,3})\s*页)", re.IGNORECASE)
_ELEMENT_REFERENCE = re.compile(r"\bel-[a-z0-9-]+\b", re.IGNORECASE)


@dataclass(frozen=True)
class RevisionScope:
    type: str
    slide_ids: tuple[str, ...]
    element_ids: tuple[str, ...]


@dataclass(frozen=True)
class IntakeResult:
    brief: dict[str, Any]
    selected_theme_id: str
    status: str
    next_action: str


class PresentationAgent:
    """Deterministic orchestration around the existing planner and renderer."""

    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root)
        self.templates = TemplateCatalog(self.project_root)
        self.skills = SkillRegistry()
        self.skills.register(
            Capability(
                name="ppt-design-pipeline",
                description="Build design plans, render editable PPTX files, and validate output.",
                operations=("plan", "render", "validate"),
            )
        )

    def intake(
        self,
        *,
        project_id: str,
        raw_request: str,
        topic: str,
        use_case: str,
        audience: list[str] | None = None,
        language: str = "zh-CN",
        page_count: int = 10,
        requested_style: str | None = None,
        theme_hint: str = "auto",
        materials: list[dict[str, Any]] | None = None,
        constraints: list[dict[str, Any]] | None = None,
    ) -> IntakeResult:
        audience = audience or []
        clarifications = self._clarifications(audience, use_case, materials or [])
        theme = self.templates.select_theme(use_case, theme_hint)
        brief = {
            "schema_version": "1.0.0",
            "project_id": project_id,
            "raw_request": raw_request,
            "topic": topic,
            "use_case": use_case,
            "audience": audience or ["待确认"],
            "language": language,
            "page_count": {"target": page_count, "min": max(1, page_count - 2), "max": page_count + 2},
            "style": {"requested": requested_style, "theme_hint": theme.theme_id},
            "constraints": constraints or [],
            "materials": materials or [],
            "clarifications": clarifications,
        }
        needs_input = any(item["status"] == "needed" for item in clarifications)
        return IntakeResult(
            brief=brief,
            selected_theme_id=theme.theme_id,
            status="needs_clarification" if needs_input else "ready_for_outline",
            next_action="confirm_brief" if needs_input else "generate_outline_preview",
        )

    @staticmethod
    def revision_scope(request: str, slide_plan: dict[str, Any] | None = None) -> RevisionScope:
        element_ids = tuple(dict.fromkeys(match.group(0).lower() for match in _ELEMENT_REFERENCE.finditer(request)))
        if element_ids:
            return RevisionScope("elements", (), element_ids)

        referenced_numbers = []
        for match in _SLIDE_REFERENCE.finditer(request):
            number = next(value for value in match.groups() if value is not None)
            referenced_numbers.append(int(number))
        if referenced_numbers:
            available = {
                slide.get("slide_number"): slide.get("slide_id")
                for slide in (slide_plan or {}).get("slides", [])
            }
            slide_ids = tuple(
                available.get(number, f"slide-{number:03d}")
                for number in dict.fromkeys(referenced_numbers)
            )
            return RevisionScope("slides", slide_ids, ())
        return RevisionScope("deck", (), ())

    @staticmethod
    def content_qa(project_id: str, slide_plan: dict[str, Any]) -> dict[str, Any]:
        issues = []
        for slide in slide_plan.get("slides", []):
            slide_id = slide.get("slide_id")
            title = slide.get("title") or slide.get("action_title", "")
            key_message = slide.get("key_message", "")
            if not key_message:
                issues.append(_issue(len(issues) + 1, "blocker", "content", slide_id, "页面缺少核心观点。", "补充一句可验证的 key_message。", True))
            if len(title) > 42:
                issues.append(_issue(len(issues) + 1, "warning", "density", slide_id, "标题可能超过单行版式容量。", "将标题缩短为结论式短句，或使用双行标题布局。", True))
            blocks = slide.get("content_blocks", slide.get("content", []))
            character_count = sum(_block_characters(block) for block in blocks)
            if character_count > 360:
                issues.append(_issue(len(issues) + 1, "warning", "density", slide_id, "正文内容密度偏高。", "拆分页面、缩短文案或替换为图表/图片。", True))
            if slide.get("slide_type") == "chart" and not _has_chart_data(blocks):
                issues.append(_issue(len(issues) + 1, "blocker", "content", slide_id, "图表页没有可验证的图表数据。", "补充 categories 与 values，并记录数据来源。", False))

        blockers = sum(issue["severity"] == "blocker" for issue in issues)
        warnings = sum(issue["severity"] == "warning" for issue in issues)
        return {
            "schema_version": "1.0.0",
            "project_id": project_id,
            "artifact": {"pptx_path": "pending", "slide_plan_path": "pending", "preview_path": None},
            "status": "fail" if blockers else "pass_with_warnings" if warnings else "pass",
            "checked_at": datetime.now(UTC).isoformat(),
            "summary": {"slides_checked": len(slide_plan.get("slides", [])), "blocking_issues": blockers, "warnings": warnings},
            "issues": issues,
        }

    @staticmethod
    def _clarifications(audience: list[str], use_case: str, materials: list[dict[str, Any]]) -> list[dict[str, Any]]:
        questions = []
        if not audience:
            questions.append({"question": "这份 PPT 面向谁？他们需要做出什么判断或行动？", "answer": None, "status": "needed"})
        if use_case == "other":
            questions.append({"question": "这份 PPT 的使用场景是什么，例如客户汇报、内部复盘或课程展示？", "answer": None, "status": "needed"})
        if not materials:
            questions.append({"question": "是否有必须使用的数据、图片、品牌模板或既有材料？", "answer": None, "status": "needed"})
        return questions


def _issue(number: int, severity: str, category: str, slide_id: str | None, description: str, repair_action: str, auto_fixable: bool) -> dict[str, Any]:
    return {"issue_id": f"qa-{number:03d}", "severity": severity, "category": category, "slide_id": slide_id, "element_id": None, "description": description, "repair_action": repair_action, "auto_fixable": auto_fixable}


def _block_characters(block: dict[str, Any]) -> int:
    values = block.get("content", block.get("items", block.get("steps", block.get("rows", ""))))
    if isinstance(values, dict):
        return sum(len(str(value)) for value in values.values())
    if isinstance(values, list):
        return sum(len(str(value)) for value in values)
    return len(str(values))


def _has_chart_data(blocks: list[dict[str, Any]]) -> bool:
    for block in blocks:
        if block.get("type") != "chart":
            continue
        data = block.get("data", {})
        categories = data.get("categories") or data.get("labels") or []
        values = data.get("values") or []
        series = data.get("series") or []
        if not values and series and isinstance(series[0], dict):
            values = series[0].get("values", [])
        if categories and values and len(categories) == len(values):
            return True
    return False
