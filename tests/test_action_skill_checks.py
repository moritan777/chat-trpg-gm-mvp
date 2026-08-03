import json
import re
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from fixed_truth_ai_gm_mvp import Game, State


class ActionSkillCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        scenario = {
            "opening_scene": "lower_cliff",
            "player": {
                "skills": {
                    "investigation": 2,
                    "survival": 1,
                    "persuasion": 1,
                    "athletics": 1,
                    "stealth": 1,
                }
            },
            "locations": [
                {"id": "lower_cliff", "name": "崖下", "intro": "切り立った崖だ。", "exits": []},
                {"id": "upper_cliff", "name": "崖上", "intro": "崖の上だ。", "exits": []},
            ],
            "action_checks": [
                {
                    "id": "climb_rocks",
                    "required_location": "lower_cliff",
                    "positive_examples": ["崖を登る", "岩を登る", "よじ登る"],
                    "skill_check": {"skill": "survival", "dice": "2d6", "difficulty": 8},
                    "success_text": "足場を選び、崖の上へ登り切りました。",
                    "failure_text": "足場をつかめず、崖下に留まります。",
                    "success_effect": {"move_to": "upper_cliff"},
                    "failure_effect": {"delay": True},
                }
            ],
        }
        Path(self.temp_dir.name, "scenario.json").write_text(
            json.dumps(scenario, ensure_ascii=False), encoding="utf-8"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_climb(self, dice_total):
        game = Game(self.temp_dir.name, skill_dice_total=dice_total)
        state = State("lower_cliff")
        intent = game.judge("崖を登る", state)
        return state, intent, game.resolve(intent, state)

    def test_success_moves_to_upper_cliff(self):
        state, intent, (lines, result, events) = self.run_climb(7)
        self.assertEqual("action_skill_check", intent["action_type"])
        self.assertEqual("ok", result["status"])
        self.assertEqual("upper_cliff", state.location)
        self.assertIn("成功", lines)
        self.assertIn({"type": "location_changed", "id": "upper_cliff"}, events)

    def test_failure_does_not_move_and_records_delay(self):
        state, _intent, (lines, result, events) = self.run_climb(6)
        self.assertEqual("fail", result["status"])
        self.assertEqual("lower_cliff", state.location)
        self.assertIn("失敗", lines)
        self.assertIn({"type": "action_delayed"}, events)

    def test_total_equal_to_difficulty_succeeds(self):
        state, _intent, (lines, result, _events) = self.run_climb(7)
        self.assertEqual("ok", result["status"])
        self.assertEqual("upper_cliff", state.location)
        self.assertEqual(["結果:", "8", "難易度:", "8"], lines[2:6])

    def test_check_is_only_available_at_required_location(self):
        game = Game(self.temp_dir.name, skill_dice_total=7)
        intent = game.judge("崖を登る", State("upper_cliff"))
        self.assertNotEqual("action_skill_check", intent["action_type"])

    def test_standard_skills_are_present_when_scenario_omits_them(self):
        scenario_path = Path(self.temp_dir.name, "scenario.json")
        scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
        scenario["player"] = {"skills": {"investigation": 3}}
        scenario_path.write_text(json.dumps(scenario, ensure_ascii=False), encoding="utf-8")

        skills = Game(self.temp_dir.name).player["skills"]

        self.assertEqual(3, skills["investigation"])
        self.assertEqual(0, skills["survival"])
        self.assertEqual(0, skills["persuasion"])
        self.assertEqual(0, skills["athletics"])
        self.assertEqual(0, skills["stealth"])

    def test_normalized_exact_example_is_selected_before_action_intent(self):
        game = Game(self.temp_dir.name, debug_judge=True)
        output = StringIO()
        with redirect_stdout(output):
            intent = game.judge("　崖を登る。 ", State("lower_cliff"))

        self.assertEqual("action_skill_check", intent["action_type"])
        self.assertNotIn("[ActionIntent]", output.getvalue())
        self.assertIn("[ActionCheckRoute]\ninput=　崖を登る。 \nid=climb_rocks\ndecision=selected", output.getvalue())

    def test_non_exact_action_can_use_embedding_similarity(self):
        game = Game(self.temp_dir.name)
        game.score_examples = lambda _raw, _examples: (0.90, "embedding")

        intent = game.judge("岩壁を登って上へ行く", State("lower_cliff"))

        self.assertEqual("action_skill_check", intent["action_type"])
        self.assertEqual("climb_rocks", intent["target_id"])


class LighthouseActionSkillCheckIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Path("author_scenario_lighthouse_v2150.md").read_text(encoding="utf-8")
        scenario = json.loads(re.search(r"```scenario-json\s*(.*?)\s*```", source, re.S).group(1))
        scenario.pop("tests", None)
        cls.temp_dir = tempfile.TemporaryDirectory()
        Path(cls.temp_dir.name, "scenario.json").write_text(
            json.dumps(scenario, ensure_ascii=False), encoding="utf-8"
        )

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_authored_climb_routes_and_succeeds_on_equal_difficulty(self):
        game = Game(self.temp_dir.name, skill_dice_total=7)
        state = State("cliff_path")

        intent = game.judge("崖を登る", state)
        lines, result, events = game.resolve(intent, state)

        self.assertEqual("action_skill_check", intent["action_type"])
        self.assertEqual("climb_cliff", intent["target_id"])
        self.assertEqual("ok", result["status"])
        self.assertEqual("lighthouse_entrance", state.location)
        self.assertIn("GM: 安全な足場を見つけ、灯台入口まで登り切りました。", lines)
        self.assertIn({"type": "location_changed", "id": "lighthouse_entrance"}, events)

    def test_authored_climb_variant_fails_and_delays(self):
        game = Game(self.temp_dir.name, skill_dice_total=3)
        state = State("cliff_path")

        intent = game.judge("よじ登る", state)
        lines, result, events = game.resolve(intent, state)

        self.assertEqual("climb_cliff", intent["target_id"])
        self.assertEqual("fail", result["status"])
        self.assertEqual("cliff_path", state.location)
        self.assertIn("GM: 足場が崩れ、岬の道で立ち止まります。", lines)
        self.assertIn({"type": "action_delayed"}, events)

    def test_authored_climb_is_ineligible_at_harbor(self):
        game = Game(self.temp_dir.name)
        intent = game.judge("崖を登る", State("harbor"))
        self.assertNotEqual("action_skill_check", intent["action_type"])

    def test_unrelated_actions_keep_existing_routes(self):
        game = Game(self.temp_dir.name)
        state = State("cliff_path")
        self.assertEqual("inspect", game.judge("足跡を調べる", state)["action_type"])
        self.assertEqual("move", game.judge("灯台入口へ行く", state)["action_type"])
        self.assertNotEqual("action_skill_check", game.judge("ニコに聞く", state)["action_type"])


if __name__ == "__main__":
    unittest.main()
