import json
import unittest
from pathlib import Path

from agent.core import validate_document
from agent.skills.layout_engine import RenderPlanCompiler


ROOT = Path(__file__).resolve().parents[1]


class LayoutEngineTests(unittest.TestCase):
    def test_registry_and_design_plan_validate(self):
        registry = json.loads((ROOT / "design-library" / "layouts" / "layout-registry.v2.json").read_text(encoding="utf-8"))
        design_plan = json.loads((ROOT / "projects" / "ai-drug-discovery-course-report" / "plan" / "design-plan.json").read_text(encoding="utf-8"))
        self.assertEqual(validate_document(registry, "layout-registry", "2.0.0"), [])
        self.assertEqual(validate_document(design_plan, "design-plan", "2.0.0"), [])

    def test_compiler_emits_valid_render_plan_with_stable_bindings(self):
        plan_dir = ROOT / "projects" / "ai-drug-discovery-course-report" / "plan"
        design_plan = json.loads((plan_dir / "design-plan.json").read_text(encoding="utf-8"))
        content_plan = json.loads((plan_dir / "slide-plan.json").read_text(encoding="utf-8"))
        render_plan = RenderPlanCompiler().compile(design_plan, content_plan)
        self.assertEqual(len(render_plan["slides"]), len(design_plan["slides"]))
        self.assertEqual(validate_document(render_plan, "render-plan", "2.0.0"), [])
        self.assertTrue(render_plan["slides"][0]["elements"][0]["element_id"].startswith("el-001-"))


if __name__ == "__main__":
    unittest.main()
