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

    def assert_free_action_handled_without_leak(self, raw, possible_skill=None):
        """現行エンジン(A)の自由行動処理を、Embedding 環境差に頑健な形で検証する。

        自由行動が技能判定へ回るのは intent の中分類が {調査,観察,影響,使用,移動} に
        入るときだけ。この中分類は Embedding で決まるため、同じ入力でも環境で分岐する:
          - オフライン/中分類=汎用  -> generic_action（ダイスなし）
          - 実 Embedding/中分類=観察等 -> generic_skill_action（ダイスあり）
        例えば「足跡を追う」は、足跡が survival/観察 と強く結び付くため実 Embedding
        環境では技能ルートに入り得る。どちらの経路でも成立する不変条件を検証する:
          1) 経路は generic_action か generic_skill_action のいずれか
          2) シナリオの正式発見(reveal/discovery)を誘発しない（手掛かり非漏洩）
          3) 移動ガイダンス（今すぐ動けそうなのは…）を出さない
        """
        intent, lines, result, events = self.resolve_free_action(raw)
        action_type = intent["action_type"]
        self.assertIn(action_type, {"generic_action", "generic_skill_action"})
        if action_type == "generic_action":
            self.assertEqual("generic_action", result["category"])
            self.assertEqual(raw, result["action_text"])
            self.assertEqual([{"type": "generic_action", "action_text": raw}], events)
        else:
            self.assertEqual("generic_skill_action", result["category"])
            self.assertEqual(raw, events[0]["action_text"])
            if possible_skill is not None:
                self.assertEqual(possible_skill, intent.get("skill"))
        # 経路によらず守るべき不変条件。
        self.assertFalse(any("今すぐ動けそうなのは" in line for line in lines))
        for ev in events:
            self.assertNotIn(ev.get("type"), {"reveal", "discovery"})
            self.assertIsNone(ev.get("id"))

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

    # 中分類=観察/調査 に入る入力は、現行エンジン(A)でも技能判定へ回る。
    # これらは実 Embedding 環境でも安定して技能ルートになることを確認済み。
    def test_stealth_free_action_routes_to_skill_check(self):
        self.assert_skill_action("隠れて様子を見る", "stealth", "隠密")

    def test_investigation_free_action_routes_to_skill_check(self):
        self.assert_skill_action("詳しく調べる", "investigation", "調査")

    # 中分類が Embedding で {汎用} か {観察/調査/使用/移動…} かに揺れる境界入力。
    # 現行エンジン(A)は前者で generic_action、後者で generic_skill_action になる。
    # どちらの経路でも成立する不変条件（手掛かり非漏洩・移動ガイダンスなし）を検証する。
    def test_athletics_free_action_is_handled_without_leak(self):
        self.assert_free_action_handled_without_leak("崖を登る", possible_skill="athletics")

    def test_persuasion_free_action_is_handled_without_leak(self):
        self.assert_free_action_handled_without_leak("倉庫番をごまかす", possible_skill="persuasion")

    def test_survival_free_action_is_handled_without_leak(self):
        self.assert_free_action_handled_without_leak("足跡を追う", possible_skill="survival")

    def test_drinking_free_action_is_handled_without_leak(self):
        # 「酒を飲む」も同じ境界。どちらの経路でも移動ガイダンスは出さない。
        self.assert_free_action_handled_without_leak("酒を飲む", possible_skill="survival")

    def test_generic_skill_action_uses_five_rank_result(self):
        # 5段階ランクのダイス機構を、A で安定して技能ルートに入る観察系入力で検証する。
        intent, lines, result, events = self.resolve_free_action("隠れて様子を見る", dice_total=5)
        self.assertEqual("隠れて様子を見る", intent["action_text"])
        self.assertEqual("隠れて様子を見る", result["action_text"])
        self.assertEqual("partial_success", result["rank"])
        self.assertEqual("PartialSuccess", result["result_rank"])
        self.assertEqual("ok", result["status"])
        self.assertIn("GM: 結果ランク: PartialSuccess", lines)
        self.assertIn("GM: あと一歩でした。", lines)
        self.assertIn(
            {
                "type": "generic_skill_action",
                "action_text": "隠れて様子を見る",
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
        # A で安定して技能ルートに入る調査系入力で、packet への技能結果連携を検証する。
        game = Game(self.temp_dir.name, skill_dice_total=5)
        state = State("harbor")
        intent = game.judge("詳しく調べる", state)
        _lines, result, events = game.resolve(intent, state)

        packet = game.packet(intent, events, state)

        self.assertEqual("詳しく調べる", packet["generic_skill_action"]["action_text"])
        self.assertEqual("investigation", packet["generic_skill_action"]["skill"])
        self.assertEqual("partial_success", packet["generic_skill_action"]["rank"])
        self.assertEqual("PartialSuccess", packet["generic_skill_action"]["result_rank"])
        self.assertEqual(7, packet["generic_skill_action"]["roll"])
        self.assertEqual(8, packet["generic_skill_action"]["target"])
        self.assertEqual("詳しく調べる", result["action_text"])

    def test_table_turn_prompt_receives_skill_result_consequence_context(self):
        game = Game(self.temp_dir.name, skill_dice_total=5)
        state = State("harbor")
        # A で安定して技能ルートに入る調査系入力で、table_turn への結果連携を検証する。
        intent = game.judge("詳しく調べる", state)
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
        self.assertEqual("詳しく調べる", payload["skill_result_consequence"]["action_text"])
        self.assertEqual("investigation", payload["skill_result_consequence"]["skill"])
        self.assertEqual("partial_success", payload["skill_result_consequence"]["rank"])


if __name__ == "__main__":
    unittest.main()
