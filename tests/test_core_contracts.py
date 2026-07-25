import json
import unittest
from pathlib import Path

from agent.core import get_contract, list_contracts, upgrade_slide_plan_v1


ROOT = Path(__file__).resolve().parents[1]


class ContractTests(unittest.TestCase):
    def test_registered_contracts_are_valid_json_objects(self):
        for contract in list_contracts():
            with self.subTest(contract=f"{contract.name}@{contract.version}"):
                schema = json.loads(contract.path.read_text(encoding="utf-8"))
                self.assertEqual(schema["type"], "object")

    def test_v2_contracts_are_registered(self):
        self.assertTrue(get_contract("slide-plan", "2.0.0").path.is_file())
        self.assertTrue(get_contract("layout-registry", "2.0.0").path.is_file())
        self.assertTrue(get_contract("render-plan", "2.0.0").path.is_file())

    def test_existing_plan_upgrades_without_mutation(self):
        source_path = ROOT / "projects" / "ai-drug-discovery-course-report" / "plan" / "slide-plan.json"
        source = json.loads(source_path.read_text(encoding="utf-8"))
        before = json.dumps(source, ensure_ascii=False, sort_keys=True)

        upgraded = upgrade_slide_plan_v1(source)

        self.assertEqual(upgraded["schema_version"], "2.0.0")
        self.assertEqual(len(upgraded["slides"]), len(source["slides"]))
        self.assertEqual(upgraded["slides"][0]["narrative_role"], "opening")
        self.assertEqual(json.dumps(source, ensure_ascii=False, sort_keys=True), before)


if __name__ == "__main__":
    unittest.main()
