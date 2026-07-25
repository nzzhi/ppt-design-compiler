import importlib.util
import json
import unittest
from pathlib import Path

from agent.core import get_contract


ROOT = Path(__file__).resolve().parents[1]
PLANNER_PATH = ROOT / "agent" / "skills" / "design-planner" / "planner.py"
SPEC = importlib.util.spec_from_file_location("ppt_agent_design_planner", PLANNER_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
DesignPlanner = MODULE.DesignPlanner


class DesignPlannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source_path = ROOT / "projects" / "ai-drug-discovery-course-report" / "plan" / "slide-plan.json"
        cls.source = json.loads(source_path.read_text(encoding="utf-8"))
        cls.plan = DesignPlanner().plan(cls.source)

    def test_design_plan_contract_is_registered(self):
        self.assertTrue(get_contract("design-plan", "2.0.0").path.is_file())

    def test_every_slide_has_required_design_decisions(self):
        required = {
            "slide_type",
            "layout",
            "visual_type",
            "information_density",
            "design_notes",
            "narrative",
            "hierarchy",
            "composition",
            "image_strategy",
        }
        for slide in self.plan["slides"]:
            with self.subTest(slide=slide["slide_id"]):
                self.assertTrue(required.issubset(slide))
                self.assertTrue(slide["layout"]["layout_id"])
                self.assertTrue(slide["design_notes"])

    def test_plan_contains_schema_required_fields(self):
        schema_path = get_contract("design-plan", "2.0.0").path
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertTrue(set(schema["required"]).issubset(self.plan))
        slide_required = set(schema["$defs"]["slide_design"]["required"])
        for slide in self.plan["slides"]:
            self.assertTrue(slide_required.issubset(slide))

    def test_layout_is_the_result_of_explicit_design_decisions(self):
        slide = self.plan["slides"][2]
        self.assertEqual(slide["hierarchy"]["dominant_element"], "primary-exhibit")
        self.assertEqual(slide["composition"]["silhouette"], "exhibit-dominant")
        self.assertIn("action-title", slide["hierarchy"]["reading_order"])
        self.assertTrue(slide["narrative"]["entry_logic"])
        self.assertTrue(slide["narrative"]["exit_logic"])

    def test_deck_direction_records_design_strategy(self):
        direction = self.plan["deck_direction"]
        for key in ("communication_job", "narrative_arc", "hierarchy_strategy", "image_strategy", "layout_strategy"):
            self.assertTrue(direction[key])

    def test_image_strategy_is_specific_even_when_no_image_is_needed(self):
        cover = self.plan["slides"][0]
        self.assertFalse(cover["image_strategy"]["use_image"])
        self.assertEqual(cover["image_strategy"]["role"], "none")
        self.assertEqual(cover["image_strategy"]["treatment"], "No decorative image required")

    def test_content_shape_drives_design(self):
        slides = {slide["slide_number"]: slide for slide in self.plan["slides"]}
        self.assertEqual(slides[4]["slide_type"], "process")
        self.assertEqual(slides[4]["visual_type"], "diagram")
        self.assertEqual(slides[6]["layout"]["family"], "comparison")

    def test_density_can_trigger_layout_action(self):
        closing = self.plan["slides"][-1]
        self.assertEqual(closing["slide_type"], "closing")
        self.assertEqual(closing["information_density"]["overflow_action"], "change-layout")

    def test_knowledge_ids_are_unique(self):
        knowledge = ROOT / "design-library" / "knowledge"
        page_rules = json.loads((knowledge / "page-type-rules.v1.json").read_text(encoding="utf-8"))
        layout_rules = json.loads((knowledge / "layout-selection-rules.v1.json").read_text(encoding="utf-8"))
        page_ids = [item["page_type"] for item in page_rules["page_types"]]
        layout_ids = [item["layout_id"] for item in layout_rules["layout_rules"]]
        self.assertEqual(len(page_ids), len(set(page_ids)))
        self.assertEqual(len(layout_ids), len(set(layout_ids)))


if __name__ == "__main__":
    unittest.main()
