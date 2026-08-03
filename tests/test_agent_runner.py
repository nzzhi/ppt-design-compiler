import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from pptx import Presentation

from agent.runtime import AgentRunner, ContractGenerator, ProjectStore, ScriptedProvider


ROOT = Path(__file__).resolve().parents[1]


def brief():
    return {
        "schema_version": "1.0.0",
        "project_id": "runner-demo",
        "raw_request": "做一份三页市场简报",
        "topic": "市场简报",
        "use_case": "work_report",
        "audience": ["管理层"],
        "language": "zh-CN",
        "page_count": {"target": 3, "min": 3, "max": 3},
        "style": {"requested": None, "theme_hint": "business-report.v1"},
        "constraints": [],
        "materials": [{"material_id": "m-001", "type": "text", "path": None, "summary": "已核验内容"}],
        "clarifications": [],
    }


def outline():
    return {
        "schema_version": "1.0.0",
        "project_id": "runner-demo",
        "deck_title": "市场简报",
        "story_goal": "让管理层理解市场机会",
        "narrative_arc": "situation-analysis-action",
        "slides": [
            {"slide_id": f"slide-{number:03d}", "slide_number": number, "purpose": purpose, "working_title": title, "key_message": message, "required_evidence": [], "notes": ""}
            for number, purpose, title, message in (
                (1, "opening", "市场简报", "机会来自结构变化"),
                (2, "analysis", "关键判断", "场景比规模更重要"),
                (3, "closing", "行动建议", "先验证高频需求"),
            )
        ],
    }


def slide_plan():
    specs = [
        (1, "cover", "cover.title-subtitle.v1", "市场简报", "机会来自结构变化"),
        (2, "content", "content.title-body.v1", "关键判断", "场景比规模更重要"),
        (3, "closing", "closing.final-message.v1", "行动建议", "先验证高频需求"),
    ]
    slides = []
    for number, slide_type, layout, title, message in specs:
        block_id = f"block-{number:03d}-body"
        slides.append(
            {
                "slide_id": f"slide-{number:03d}",
                "slide_number": number,
                "slide_type": slide_type,
                "layout_id": layout,
                "question": f"第 {number} 页回答什么？",
                "title": title,
                "key_message": message,
                "content_blocks": [{"block_id": block_id, "role": "body", "content": [message], "priority": 1, "source_asset_ids": []}],
                "visual_intent": {"type": "text", "chart_type": None, "image_role": None, "emphasis": "high"},
                "assets": [],
                "editable_elements": [{"element_id": f"el-{number:03d}-body", "element_type": "text_box", "content_ref": block_id, "locked": False, "revision_scope": "element"}],
                "speaker_notes": "",
                "constraints": [],
                "revision_history": [],
            }
        )
    return {
        "schema_version": "1.0.0",
        "deck_id": "runner-demo",
        "language": "zh-CN",
        "slide_size": {"preset": "wide-16-9", "width": 13.333, "height": 7.5, "unit": "in"},
        "design_system_id": "runner-demo.business-report.v1",
        "global_constraints": [],
        "slides": slides,
    }


class ProviderAndStoreTests(unittest.TestCase):
    def test_contract_generator_retries_invalid_output(self):
        provider = ScriptedProvider([{}, outline()])
        document = ContractGenerator(provider, max_attempts=2).generate(
            task="outline",
            payload={},
            contract_name="outline",
            contract_version="1.0.0",
        )
        self.assertEqual(document["deck_title"], "市场简报")
        self.assertEqual(provider.calls, ["outline", "outline"])

    def test_store_rejects_unsafe_project_ids_and_versions_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                ProjectStore(temp_dir, "../unsafe")
            store = ProjectStore(temp_dir, "safe-project")
            store.write_json("plan/brief.json", {"ok": True})
            self.assertEqual(store.read_json("plan/brief.json"), {"ok": True})
            self.assertEqual(store.next_output_version(), 1)


class AgentRunnerTests(unittest.TestCase):
    def test_runner_generates_durable_project_and_editable_pptx(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = ScriptedProvider([outline(), slide_plan()])
            runner = AgentRunner(ROOT, provider, projects_root=temp_dir)
            result = runner.run_brief(brief())

            self.assertEqual(result.status, "complete")
            self.assertTrue(result.output_path.is_file())
            self.assertEqual(len(Presentation(result.output_path).slides), 3)
            project = Path(temp_dir) / "runner-demo"
            for relative in ("plan/brief.json", "plan/outline.json", "plan/design-system.json", "plan/slide-plan.json", "plan/design-plan.json", "plan/render-plan.json", "qa/qa-report.json"):
                self.assertTrue((project / relative).is_file(), relative)

    def test_start_waits_for_outline_confirmation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = ScriptedProvider([outline(), slide_plan()])
            runner = AgentRunner(ROOT, provider, projects_root=temp_dir)
            result = runner.start(
                project_id="runner-demo",
                raw_request="做一份三页市场简报",
                topic="市场简报",
                use_case="work_report",
                audience=["管理层"],
                page_count=3,
                theme_hint="business-report.v1",
                materials=[{"material_id": "m-001", "type": "text", "summary": "已核验内容"}],
            )
            self.assertEqual(result.status, "awaiting_outline_confirmation")
            self.assertFalse((Path(temp_dir) / "runner-demo" / "plan" / "slide-plan.json").exists())
            confirmed = runner.confirm_outline("runner-demo")
            self.assertEqual(confirmed.status, "complete")

    def test_revision_changes_only_target_slide_and_creates_new_version(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            initial = slide_plan()
            revised = deepcopy(initial)
            revised["slides"][1]["title"] = "更新后的关键判断"
            provider = ScriptedProvider([outline(), initial, revised])
            runner = AgentRunner(ROOT, provider, projects_root=temp_dir)
            first = runner.run_brief(brief())
            second = runner.revise("runner-demo", "只把第 2 页标题改得更明确")

            self.assertEqual(first.output_path.name, "presentation-v001.pptx")
            self.assertEqual(second.output_path.name, "presentation-v002.pptx")
            stored = json.loads((Path(temp_dir) / "runner-demo" / "plan" / "slide-plan.json").read_text(encoding="utf-8"))
            self.assertEqual(stored["slides"][0], initial["slides"][0])
            self.assertEqual(stored["slides"][1]["title"], "更新后的关键判断")
            self.assertTrue((Path(temp_dir) / "runner-demo" / "revisions" / "revision-001.json").is_file())
            self.assertEqual(ProjectStore(temp_dir, "runner-demo").next_revision_id(), "revision-002")


if __name__ == "__main__":
    unittest.main()
