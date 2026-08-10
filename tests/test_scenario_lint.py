import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class ScenarioLintKnowledgeBoundaryTests(unittest.TestCase):
    def run_lint(self, scenario):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scenario.json"
            path.write_text(json.dumps(scenario, ensure_ascii=False), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(ROOT / "scenario_lint.py"), str(path)],
                capture_output=True,
                text=True,
                check=False,
            )

    def base_scenario(self):
        return {
            "opening_scene": "harbor",
            "locations": [{"id": "harbor", "npcs": ["head"], "visible_objects": [], "exits": []}],
            "objects": [],
            "npcs": [
                {
                    "id": "head",
                    "location": "harbor",
                    "knows": ["report"],
                    "does_not_know": [],
                    "topics": {"報告": ["report"]},
                }
            ],
            "discoverables": [
                {
                    "id": "report",
                    "source": {"type": "npc", "id": "head"},
                    "positive_examples": ["報告を聞く"],
                    "public_text": "報告を聞いた。",
                }
            ],
            "goals": [],
        }

    def test_valid_topic_knowledge_boundary_passes(self):
        result = self.run_lint(self.base_scenario())
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_topic_cannot_reference_does_not_know(self):
        scenario = self.base_scenario()
        scenario["npcs"][0]["does_not_know"] = ["report"]
        result = self.run_lint(scenario)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("listed in does_not_know", result.stdout)

    def test_topic_owner_must_match_npc_discoverable_source(self):
        scenario = self.base_scenario()
        scenario["npcs"].append(
            {
                "id": "other",
                "location": "harbor",
                "knows": ["report"],
                "does_not_know": [],
                "topics": {"報告": ["report"]},
            }
        )
        scenario["locations"][0]["npcs"].append("other")
        result = self.run_lint(scenario)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("source npc is head", result.stdout)


if __name__ == "__main__":
    unittest.main()
