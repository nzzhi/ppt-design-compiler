import unittest
from pathlib import Path

from agent.runtime import PresentationAgent


ROOT = Path(__file__).resolve().parents[1]


class AgentRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.agent = PresentationAgent(ROOT)

    def test_catalog_discovers_templates_and_selects_theme_by_use_case(self):
        themes = self.agent.templates.themes()
        self.assertGreaterEqual(len(themes), 3)
        self.assertEqual(self.agent.templates.select_theme("roadshow").theme_id, "tech-roadshow.v1")
        self.assertEqual(self.agent.templates.select_theme("work_report", "business-report.v1").theme_id, "business-report.v1")
        self.assertTrue(self.agent.templates.layouts())

    def test_intake_requires_missing_audience_and_materials(self):
        result = self.agent.intake(
            project_id="demo",
            raw_request="做一份新能源汽车市场分析",
            topic="新能源汽车市场分析",
            use_case="work_report",
        )
        self.assertEqual(result.status, "needs_clarification")
        self.assertEqual(result.selected_theme_id, "business-report.v1")
        self.assertTrue(result.brief["clarifications"])

    def test_intake_is_ready_when_minimum_context_is_present(self):
        result = self.agent.intake(
            project_id="demo",
            raw_request="向管理层汇报",
            topic="新能源汽车市场分析",
            use_case="work_report",
            audience=["管理层"],
            materials=[{"material_id": "m-001", "type": "data", "summary": "年度销量数据"}],
        )
        self.assertEqual(result.status, "ready_for_outline")
        self.assertEqual(result.next_action, "generate_outline_preview")

    def test_revision_scope_prefers_explicit_elements_then_slides(self):
        self.assertEqual(self.agent.revision_scope("把 el-003-title 改成蓝色").type, "elements")
        scope = self.agent.revision_scope("把第 4 页和 slide-007 改成图表")
        self.assertEqual(scope.type, "slides")
        self.assertEqual(scope.slide_ids, ("slide-004", "slide-007"))
        self.assertEqual(self.agent.revision_scope("整体换成商务风").type, "deck")

    def test_content_qa_flags_missing_chart_data(self):
        report = self.agent.content_qa(
            "demo",
            {"slides": [{"slide_id": "slide-001", "slide_type": "chart", "title": "图表结论", "key_message": "图表需要数据", "content_blocks": []}]},
        )
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["summary"]["blocking_issues"], 1)


if __name__ == "__main__":
    unittest.main()
