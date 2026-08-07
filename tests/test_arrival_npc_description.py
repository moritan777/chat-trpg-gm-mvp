import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fixed_truth_ai_gm_mvp import Game, State


class ArrivalNpcDescriptionTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        scenario = {
            "locations": [
                {"id": "rocks", "name": "岩場", "npcs": ["noah"], "intro": "海蝕洞が見える。"},
                {"id": "tavern", "name": "酒場", "npcs": ["baro"], "intro": "漁師の酒場。"},
                {"id": "lighthouse", "name": "灯台入口", "npcs": ["rena"], "intro": "灯台入口。"},
            ],
            "npcs": [
                {"id": "noah", "name": "少年ノア"},
                {"id": "baro", "name": "漁師バロ"},
                {"id": "rena", "name": "助手レナ"},
            ],
        }
        Path(self.tempdir.name, "scenario.json").write_text(
            json.dumps(scenario, ensure_ascii=False), encoding="utf-8"
        )
        self.game = Game(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_successful_arrival_mentions_each_locations_available_npc(self):
        cases = [
            ("rocks", "海蝕洞が見える。", "少年ノア"),
            ("tavern", "漁師の酒場。", "漁師バロ"),
            ("lighthouse", "灯台入口。", "助手レナ"),
        ]

        with patch.dict(os.environ, {"LLM_PROVIDER": "none", "TABLE_TURN_RENDER": "1"}):
            for location_id, intro, npc_name in cases:
                with self.subTest(location=location_id):
                    state = State(location_id)
                    notes, _ = self.game.render_table_turn(
                        ["GM: " + intro],
                        {"raw": self.game.locs[location_id]["name"] + "へ行く", "action_type": "move"},
                        {"status": "ok", "category": "move"},
                        [],
                        state,
                    )
                    rendered = "\n".join(notes)
                    self.assertIn(intro, rendered)
                    self.assertIn(npc_name, rendered)
                    self.assertNotIn("会話可能NPC", rendered)

    def test_non_arrival_turn_does_not_add_npc_description(self):
        state = State("rocks")
        with patch.dict(os.environ, {"LLM_PROVIDER": "none", "TABLE_TURN_RENDER": "1"}):
            notes, _ = self.game.render_table_turn(
                ["GM: 足元を調べます。"],
                {"raw": "足元を見る", "action_type": "inspect"},
                {"status": "ok", "category": "surface_inspect"},
                [],
                state,
            )
        self.assertNotIn("少年ノア", "\n".join(notes))



    def test_arrival_without_npc_does_not_add_npc_line(self):
        self.game.locs["empty"] = {"id": "empty", "name": "空き地", "intro": "誰もいない空き地。", "npcs": []}
        state = State("empty")
        with patch.dict(os.environ, {"LLM_PROVIDER": "none", "TABLE_TURN_RENDER": "1"}):
            notes, _ = self.game.render_table_turn(
                ["GM: 誰もいない空き地。"],
                {"raw": "空き地へ行く", "action_type": "move"},
                {"status": "ok", "category": "move"},
                [],
                state,
            )
        rendered = "\n".join(notes)
        self.assertIn("誰もいない空き地。", rendered)
        self.assertNotIn("辺りには", rendered)

if __name__ == "__main__":
    unittest.main()
