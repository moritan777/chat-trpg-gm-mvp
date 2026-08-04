import json
import tempfile
import unittest
from pathlib import Path

from fixed_truth_ai_gm_mvp import Game, State


class GenericSkillActionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        scenario = {
            "opening_scene": "harbor",
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
                {"id": "harbor", "name": "港", "intro": "潮風の強い港だ。", "exits": []}
            ],
            "objects": [],
            "npcs": [],
            "discoverables": [],
            "action_checks": [],
        }
        Path(self.temp_dir.name, "scenario.json").write_text(
            json.dumps(scenario, ensure_ascii=False), encoding="utf-8"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def resolve_free_action(self, raw, dice_total=7):
        game = Game(self.temp_dir.name, skill_dice_total=dice_total)
        state = State("harbor")
        intent = game.judge(raw, state)
        lines, result, events = game.resolve(intent, state)
        return intent, lines, result, events

    def assert_skill_action(self, raw, expected_skill, expected_label):
        intent, lines, result, events = self.resolve_free_action(raw)
        self.assertEqual("generic_skill_action", intent["action_type"])
        self.assertEqual(expected_skill, intent["skill"])
        self.assertEqual("generic_skill_action", result["category"])
        self.assertEqual(expected_skill, result["skill"])
        self.assertEqual("Success", result["result_rank"])
        self.assertIn(f"【{expected_label}判定】", lines)
        self.assertIn(f"2d6 + {expected_skill}", lines)
        self.assertEqual("GM: 判定開始", lines[4])
        self.assertEqual("GM: 2d6を振る", lines[5])
        self.assertEqual("GM: 結果ランク: Success", lines[10])
        self.assertEqual([], events)

    def test_athletics_free_action_routes_to_skill_check(self):
        self.assert_skill_action("崖を登る", "athletics", "運動")

    def test_stealth_free_action_routes_to_skill_check(self):
        self.assert_skill_action("隠れて様子を見る", "stealth", "隠密")

    def test_persuasion_free_action_routes_to_skill_check(self):
        self.assert_skill_action("倉庫番をごまかす", "persuasion", "説得")

    def test_survival_free_action_routes_to_skill_check(self):
        self.assert_skill_action("足跡を追う", "survival", "生存")

    def test_investigation_free_action_routes_to_skill_check(self):
        self.assert_skill_action("詳しく調べる", "investigation", "調査")

    def test_drinking_free_action_uses_skill_check_instead_of_move_guidance(self):
        intent, lines, result, _events = self.resolve_free_action("酒を飲む")
        self.assertEqual("generic_skill_action", intent["action_type"])
        self.assertEqual("survival", result["skill"])
        self.assertEqual("generic_skill_action", result["category"])
        self.assertTrue(any("判定" in line for line in lines))
        self.assertFalse(any("今すぐ動けそうなのは" in line for line in lines))

    def test_generic_skill_action_uses_five_rank_result(self):
        _intent, lines, result, _events = self.resolve_free_action("隠れる", dice_total=5)
        self.assertEqual("PartialSuccess", result["result_rank"])
        self.assertEqual("ok", result["status"])
        self.assertIn("GM: 結果ランク: PartialSuccess", lines)
        self.assertIn("GM: あと一歩でした。", lines)


if __name__ == "__main__":
    unittest.main()
