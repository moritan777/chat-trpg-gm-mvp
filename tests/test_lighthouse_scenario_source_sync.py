"""Audit the authored lighthouse scenario against the Web runtime artifact."""

import json
import unittest
from pathlib import Path

from md_to_scenario import load_scenario_markdown


ROOT = Path(__file__).resolve().parent.parent
AUTHOR_SOURCE = ROOT / "author_scenario_lighthouse_v2150.md"
WEB_SCENARIO = ROOT / "web" / "public" / "scenarios" / "lighthouse" / "scenario.json"
WEB_SCENARIO_DIR = WEB_SCENARIO.parent


class LighthouseScenarioSourceSyncTests(unittest.TestCase):
    def test_authored_scenario_block_matches_web_json_semantically_and_byte_for_byte(self):
        authored, tests = load_scenario_markdown(AUTHOR_SOURCE)
        web = json.loads(WEB_SCENARIO.read_text(encoding="utf-8"))

        self.assertTrue(tests, "author source should retain its generation-only test cases")
        self.assertEqual(authored, web)
        self.assertEqual(
            json.dumps(authored, ensure_ascii=False, indent=2),
            WEB_SCENARIO.read_text(encoding="utf-8"),
        )

        expectations = {}
        for name, spec in tests.items():
            self.assertEqual(
                "\n".join(spec.get("commands", [])) + "\n",
                (WEB_SCENARIO_DIR / f"sample_inputs_{name}.txt").read_text(encoding="utf-8"),
            )
            expectations[name] = {
                key: spec[key]
                for key in ("expect", "expect_not", "dice_total", "skill_dice_total")
                if key in spec
            }
        self.assertEqual(
            expectations,
            json.loads((WEB_SCENARIO_DIR / "test_expectations.json").read_text(encoding="utf-8")),
        )

    def test_v2161_assistant_key_foreshadowing_is_in_runtime_scenario(self):
        authored, _tests = load_scenario_markdown(AUTHOR_SOURCE)
        locations = {item["id"]: item for item in authored["locations"]}
        npcs = {item["id"]: item for item in authored["npcs"]}

        self.assertEqual("v2161_assistant_key_foreshadowing", authored["scenario_revision"])
        self.assertEqual("v2.16.1", authored["meta"]["authoring_revision"])
        self.assertEqual(
            "v2.16.1",
            authored["meta"]["engine_requirements"]["assistant_key_foreshadowing"],
        )
        self.assertIn("錠前に壊された形跡はなく", locations["lighthouse_entrance"]["intro"])
        self.assertIn("鍵束", locations["lighthouse_entrance"]["surface_banter_observation"])
        self.assertIn("鍵束", npcs["assistant"]["banter_observation"])
        self.assertIn("鍵束", npcs["assistant"]["surface_banter_observation"])


if __name__ == "__main__":
    unittest.main()
