import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fixed_truth_ai_gm_mvp import Game, State


class CompanionBanterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        text = Path("author_scenario_lighthouse_v2150.md").read_text(encoding="utf-8")
        match = re.search(r"```scenario-json\s*(.*?)\s*```", text, re.S)
        if not match:
            raise AssertionError("scenario-json block not found")
        scenario = json.loads(match.group(1))
        scenario.pop("tests", None)
        cls.temp_dir = tempfile.TemporaryDirectory()
        Path(cls.temp_dir.name, "scenario.json").write_text(
            json.dumps(scenario, ensure_ascii=False), encoding="utf-8"
        )

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def make_game(self):
        return Game(self.temp_dir.name)

    def test_safe_packet_excludes_unrevealed_and_author_only_data(self):
        game = self.make_game()
        state = State("harbor")
        intent = {"raw": "潮汐表を見る", "action_type": "inspect", "target_id": "tide_log"}

        packet = game.packet(intent, [], state)
        serialized = json.dumps(packet, ensure_ascii=False)

        self.assertNotIn(game.disc["tide_log_cave_time"]["public_text"], serialized)
        self.assertNotIn("solution_paths", serialized)
        self.assertNotIn("required_discoverables", serialized)
        self.assertNotIn("does_not_know", serialized)
        self.assertNotIn("灯台入口の手すり", serialized)

        npc_packet = game.packet(
            {"raw": "漁師に聞く", "action_type": "ask", "target_id": "fisherman"}, [], state
        )
        self.assertNotIn(
            game.npcs["fisherman"]["banter_observation"],
            json.dumps(npc_packet, ensure_ascii=False),
        )

        revealed_packet = game.packet(
            intent, [{"type": "discoverable_revealed", "id": "tide_log_cave_time"}], state
        )
        self.assertIn(
            game.disc["tide_log_cave_time"]["public_text"],
            json.dumps(revealed_packet, ensure_ascii=False),
        )

    def test_prompt_separates_factual_gm_from_free_companion_hypotheses(self):
        game = self.make_game()
        state = State("cliff_path")
        captured = []

        def fake_post_json(url, body, timeout, tag):
            captured.append((url, body, timeout, tag))
            return {"choices": [{"message": {"content": "GM: ランタンが割れている。\nニコ: 空から落ちた、とかだったりして？\nリュート: ずいぶん高いところから来たな。"}}]}

        game.post_json = fake_post_json
        before = (state.location, set(state.discovered))
        with patch.dict(os.environ, {"LLM_PROVIDER": "llama_cpp"}):
            game.render_table_turn(
                ["GM: ランタンが割れている。"],
                {"raw": "ランタンを見る", "action_type": "inspect", "target_id": "broken_lantern"},
                {"status": "ok", "category": "no_reveal"},
                [],
                state,
            )

        self.assertEqual(len(captured), 1)
        prompt = captured[0][1]["messages"][0]["content"]
        user_packet = json.loads(captured[0][1]["messages"][1]["content"])
        self.assertIn("GMが述べた観察をそのまま要約・言い換えず", prompt)
        self.assertIn("根拠の弱い推測", prompt)
        self.assertIn("先に話した仲間への同意、反論、ツッコミ、便乗", prompt)
        self.assertIn("正解行動を指示する攻略役にならない", prompt)
        self.assertIn("GM本文は確定事実だけ", "".join(user_packet["instructions"]))
        self.assertEqual((state.location, state.discovered), before)

    def test_recent_banter_is_short_and_explicitly_non_factual(self):
        game = self.make_game()
        game.last_table_turn = {
            "output": "\n".join(
                [
                    "GM: 説明。",
                    "ニコ: 一つ目。",
                    "リュート: 二つ目。",
                    "ピピ: 三つ目。",
                    "ニコ: 四つ目。",
                    "リュート: 五つ目。",
                ]
            )
        }
        state = State("harbor")

        packet = game.packet({"raw": "周囲を見る", "action_type": "area_search", "target_id": None}, [], state)

        self.assertEqual(len(packet["recent_companion_lines"]), 4)
        self.assertNotIn("ニコ: 一つ目。", packet["recent_companion_lines"])
        self.assertTrue(any("世界設定や発見済み情報として扱わない" in x for x in packet["safety"]))

    def test_banter_generation_does_not_change_game_state(self):
        game = self.make_game()
        state = State("harbor")
        state.discovered.add("head_report")
        before = (state.location, set(state.discovered))

        with patch.dict(os.environ, {"LLM_PROVIDER": "none", "EMBEDDING_PROVIDER": "none"}):
            output = game.banter(
                {"raw": "港を見る", "action_type": "area_search", "target_id": None},
                {"status": "ok", "category": "area_search"},
                [],
                state,
            )

        self.assertEqual(output, "")
        self.assertEqual((state.location, state.discovered), before)


if __name__ == "__main__":
    unittest.main()
