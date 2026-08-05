import json
import tempfile
import unittest
from pathlib import Path

from fixed_truth_ai_gm_mvp import Game, State


class ScenarioIntentLayerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        scenario = {
            "opening_scene": "tavern",
            "player": {"skills": {"investigation": 2, "survival": 1, "persuasion": 1}},
            "locations": [
                {
                    "id": "tavern",
                    "name": "酒場",
                    "intro": "古い酒場だ。掲示板と樽が見える。",
                    "visible_objects": ["board", "barrel"],
                    "npcs": ["village_head", "lena"],
                    "exits": ["harbor"],
                },
                {"id": "harbor", "name": "港", "intro": "港だ。", "exits": ["tavern"]},
            ],
            "objects": [
                {"id": "board", "name": "掲示板", "aliases": ["貼り紙"]},
                {"id": "barrel", "name": "樽"},
            ],
            "npcs": [
                {"id": "village_head", "name": "村長"},
                {"id": "lena", "name": "レナ"},
            ],
            "discoverables": [],
            "action_checks": [],
        }
        Path(self.temp_dir.name, "scenario.json").write_text(
            json.dumps(scenario, ensure_ascii=False), encoding="utf-8"
        )
        self.game = Game(self.temp_dir.name, dice_seed=1)
        self.state = State("tavern")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_available_targets_are_grouped_by_current_location(self):
        self.assertEqual(
            self.game.get_available_targets(self.state),
            {"npcs": ["village_head", "lena"], "objects": ["board", "barrel"], "locations": ["harbor"]},
        )

    def test_named_object_investigation_resolves_target_and_intent(self):
        intent = self.game.judge("掲示板を調べる", self.state)
        self.assertEqual(("inspect", "board"), (intent["action_type"], intent["target_id"]))
        self.assertEqual({"major": "行動", "minor": "調査", "confidence": 0.88, "alternates": []}, intent["intent"])

    def test_targetless_probe_prompts_candidates(self):
        intent = self.game.judge("調べる", self.state)
        lines, result, events = self.game.resolve(intent, self.state)
        self.assertEqual("target_prompt", intent["action_type"])
        self.assertEqual("target_prompt", result["category"])
        self.assertEqual([], events)
        self.assertEqual("GM: どれを調べますか？", lines[0])
        self.assertIn("・掲示板", lines)
        self.assertIn("・樽", lines)
        self.assertIn("・村長", lines)

    def test_chat_about_favorite_food_is_conversation_not_survival(self):
        intent = self.game.judge("好きな食べ物の話をする", self.state)
        self.assertEqual("会話", intent["intent"]["major"])
        self.assertEqual("雑談", intent["intent"]["minor"])
        self.assertNotEqual("generic_skill_action", intent["action_type"])
        self.assertNotEqual("survival", intent.get("skill"))

    def test_question_routes_to_conversation_question(self):
        intent = self.game.judge("村長に聞く", self.state)
        self.assertEqual(("ask", "village_head"), (intent["action_type"], intent["target_id"]))
        self.assertEqual(("会話", "質問"), (intent["intent"]["major"], intent["intent"]["minor"]))

    def test_influence_routes_to_action_influence(self):
        intent = self.game.judge("レナを安心させる", self.state)
        self.assertEqual(("ask", "lena"), (intent["action_type"], intent["target_id"]))
        self.assertEqual(("行動", "影響"), (intent["intent"]["major"], intent["intent"]["minor"]))

    def test_generic_action_route_handles_rest(self):
        intent = self.game.judge("休憩する", self.state)
        lines, result, events = self.game.resolve(intent, self.state)
        self.assertEqual("generic_action", intent["action_type"])
        self.assertEqual("generic_action", result["category"])
        self.assertEqual("休憩する", events[0]["action_text"])
        self.assertIn("少し時間を進めます", lines[0])

    def test_ambiguous_watch_uses_internal_dice(self):
        intent = self.game.judge("見張りの様子を見る", self.state)
        self.assertEqual("行動", intent["intent"]["major"])
        self.assertIn(intent["intent"]["minor"], {"観察", "調査"})
        self.assertLess(intent["intent"]["confidence"], 0.8)
