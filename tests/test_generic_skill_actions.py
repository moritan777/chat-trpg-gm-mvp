import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
        start_index = lines.index("GM: 判定開始")
        roll_index = lines.index("GM: 2d6を振る")
        rank_index = lines.index("GM: 結果ランク: Success")
        self.assertLess(start_index, roll_index)
        self.assertLess(roll_index, rank_index)
        self.assertEqual("generic_skill_action", events[0]["type"])
        self.assertEqual(raw, events[0]["action_text"])
        self.assertEqual(expected_skill, events[0]["skill"])

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
        intent, lines, result, events = self.resolve_free_action("隠れる", dice_total=5)
        self.assertEqual("隠れる", intent["action_text"])
        self.assertEqual("隠れる", result["action_text"])
        self.assertEqual("partial_success", result["rank"])
        self.assertEqual("PartialSuccess", result["result_rank"])
        self.assertEqual("ok", result["status"])
        self.assertIn("GM: 結果ランク: PartialSuccess", lines)
        self.assertIn("GM: あと一歩でした。", lines)
        self.assertIn(
            {
                "type": "generic_skill_action",
                "action_text": "隠れる",
                "skill": "stealth",
                "roll": 6,
                "dice_roll": 5,
                "target": 8,
                "difficulty": 8,
                "rank": "partial_success",
                "result_rank": "PartialSuccess",
            },
            events,
        )

    def test_generic_skill_action_context_is_available_for_gm_packet(self):
        game = Game(self.temp_dir.name, skill_dice_total=5)
        state = State("harbor")
        intent = game.judge("崖を登る", state)
        _lines, result, events = game.resolve(intent, state)

        packet = game.packet(intent, events, state)

        self.assertEqual("崖を登る", packet["generic_skill_action"]["action_text"])
        self.assertEqual("athletics", packet["generic_skill_action"]["skill"])
        self.assertEqual("partial_success", packet["generic_skill_action"]["rank"])
        self.assertEqual("PartialSuccess", packet["generic_skill_action"]["result_rank"])
        self.assertEqual(6, packet["generic_skill_action"]["roll"])
        self.assertEqual(8, packet["generic_skill_action"]["target"])
        self.assertEqual("崖を登る", result["action_text"])

    def test_table_turn_prompt_receives_skill_result_consequence_context(self):
        game = Game(self.temp_dir.name, skill_dice_total=5)
        state = State("harbor")
        intent = game.judge("崖を登る", state)
        notes, result, events = game.resolve(intent, state)
        captured = []

        class FakeResponse:
            status = 200

            def read(self):
                return json.dumps({"choices": [{"message": {"content": "GM: 崖の中腹から港が見える。"}}]}).encode()

        class FakeConnection:
            def __init__(self, *args, **kwargs):
                pass

            def request(self, method, path, body=None, headers=None):
                captured.append(json.loads(body))

            def getresponse(self):
                return FakeResponse()

            def close(self):
                pass

        with patch.dict("os.environ", {"LLM_PROVIDER": "llama_cpp"}), patch(
            "http.client.HTTPConnection", FakeConnection
        ), patch("http.client.HTTPSConnection", FakeConnection):
            rendered_notes, _banter = game.render_table_turn(notes, intent, result, events, state)

        self.assertTrue(rendered_notes)
        self.assertTrue(captured)
        prompt = captured[0]["messages"][0]["content"]
        payload = json.loads(captured[0]["messages"][1]["content"])
        self.assertIn("技能判定結果が存在する場合", prompt)
        self.assertIn("世界の変化や見え方を描写", prompt)
        self.assertIn("HP、疲労、時間経過、ダメージ、戦闘、状態異常は変更しない", prompt)
        self.assertEqual("崖を登る", payload["skill_result_consequence"]["action_text"])
        self.assertEqual("athletics", payload["skill_result_consequence"]["skill"])
        self.assertEqual("partial_success", payload["skill_result_consequence"]["rank"])


if __name__ == "__main__":
    unittest.main()
