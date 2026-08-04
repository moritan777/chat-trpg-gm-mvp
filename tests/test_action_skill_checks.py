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
        self.assertEqual("GM: 判定開始", lines[0])
        self.assertEqual("GM: 2d6を振る", lines[1])
        self.assertEqual("Success", result["result_rank"])
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
        self.assertEqual("GM: 最終値: 8", lines[5])
        self.assertEqual("GM: 結果ランク: Success", lines[6])

    def test_five_result_ranks_preserve_binary_success_condition(self):
        cases = (
            (10, "CriticalSuccess", "ok"),
            (7, "Success", "ok"),
            (6, "PartialSuccess", "fail"),
            (3, "Failure", "fail"),
            (0, "CriticalFailure", "fail"),
        )
        for dice_total, rank, status in cases:
            with self.subTest(rank=rank):
                _state, _intent, (lines, result, _events) = self.run_climb(dice_total)
                self.assertEqual(rank, result["result_rank"])
                self.assertEqual(status, result["status"])
                self.assertEqual(f"GM: 結果ランク: {rank}", lines[6])

    def test_gm_dice_presentation_has_the_required_order(self):
        _state, _intent, (lines, _result, _events) = self.run_climb(7)
        self.assertEqual(
            [
                "GM: 判定開始",
                "GM: 2d6を振る",
                "GM: 出目: 7",
                "GM: 技能補正: 1",
                "GM: 手掛かり補正: 0",
                "GM: 最終値: 8",
                "GM: 結果ランク: Success",
            ],
            lines[:7],
        )

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
        prompt = "GM: 嵐の影響で崖はぬかるみ、足場も不安定になっています。安全に登れるか、生存判定を行います。"
        self.assertIn(prompt, lines)
        self.assertLess(lines.index("GM: 判定開始"), lines.index(prompt))
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

    def test_explicit_footprints_inspection_beats_action_check_embedding(self):
        game = Game(self.temp_dir.name, debug_judge=True)
        game.score_examples = lambda _raw, _examples: (0.99, "embedding")
        state = State("cliff_path")
        state.discovered.add("broken_lantern_clue")
        output = StringIO()

        with redirect_stdout(output):
            intent = game.judge("足跡を見る", state)
            lines, _result, _events = game.resolve(intent, state)

        self.assertEqual("inspect", intent["action_type"])
        self.assertEqual("cliff_footprints", intent["target_id"])
        self.assertIn("cliff_tracks_to_shore", state.discovered)
        self.assertFalse(any("GM: 判定開始" in line for line in lines))
        self.assertIn("decision=skipped\nreason=explicit_object_target", output.getvalue())
        self.assertNotIn("id=climb_cliff\ndecision=selected", output.getvalue())

    def test_explicit_footprints_examine_beats_action_check_embedding(self):
        game = Game(self.temp_dir.name)
        game.score_examples = lambda _raw, _examples: (0.99, "embedding")
        intent = game.judge("足跡を調べる", State("cliff_path"))
        self.assertEqual(("inspect", "cliff_footprints"), (intent["action_type"], intent["target_id"]))

    def test_explicit_lantern_inspection_reveals_clue(self):
        game = Game(self.temp_dir.name)
        game.score_examples = lambda _raw, _examples: (0.99, "embedding")
        state = State("cliff_path")
        intent = game.judge("ランタンを見る", state)
        game.resolve(intent, state)
        self.assertEqual(("inspect", "broken_lantern"), (intent["action_type"], intent["target_id"]))
        self.assertIn("broken_lantern_clue", state.discovered)

    def test_explicit_exits_beat_action_check_embedding(self):
        for raw, destination in (("岩場へ行く", "rocky_shore"), ("灯台入口へ行く", "lighthouse_entrance")):
            with self.subTest(raw=raw):
                game = Game(self.temp_dir.name)
                game.score_examples = lambda _raw, _examples: (0.99, "embedding")
                intent = game.judge(raw, State("cliff_path"))
                self.assertEqual(("move", destination), (intent["action_type"], intent["target_id"]))

    def test_natural_climb_still_uses_embedding(self):
        game = Game(self.temp_dir.name)
        game.score_examples = lambda _raw, _examples: (0.90, "embedding")
        intent = game.judge("この崖をよじ登って上へ進む", State("cliff_path"))
        self.assertEqual(("action_skill_check", "climb_cliff"), (intent["action_type"], intent["target_id"]))

    def test_explicit_npc_question_skips_action_check(self):
        game = Game(self.temp_dir.name)
        game.score_examples = lambda _raw, _examples: (0.99, "embedding")
        intent = game.judge("少年に洞窟のことを聞く", State("rocky_shore"))
        self.assertEqual(("ask", "boy"), (intent["action_type"], intent["target_id"]))


if __name__ == "__main__":
    unittest.main()
