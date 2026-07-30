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

    def test_revealed_object_uses_public_text_as_single_companion_stage(self):
        game = self.make_game()
        state = State("light_room")
        intent = {"raw": "レンズを見る", "action_type": "inspect", "target_id": "lighthouse_lens"}
        event = [{"type": "discoverable_revealed", "id": "lens_misaligned"}]

        packet = game.packet(intent, event, state)
        observations = packet["current_observations"]

        self.assertEqual(observations, [game.disc["lens_misaligned"]["public_text"]])
        self.assertNotIn(game.objects["lighthouse_lens"]["surface_text"], observations)
        self.assertNotIn(game.objects["lighthouse_lens"]["banter_observation"], observations)

    def test_unrevealed_object_prefers_safe_surface_banter_observation(self):
        game = self.make_game()
        state = State("light_room")
        intent = {"raw": "レンズを見る", "action_type": "inspect", "target_id": "lighthouse_lens"}

        observations = game.packet(intent, [], state)["current_observations"]

        self.assertEqual(
            observations,
            [game.objects["lighthouse_lens"]["surface_banter_observation"]],
        )
        self.assertNotIn(game.objects["lighthouse_lens"]["surface_text"], observations)
        self.assertNotIn(game.objects["lighthouse_lens"]["banter_observation"], observations)

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
        self.assertIn("手掛かりを分析しなくてもよい", prompt)
        self.assertIn("現在の観察へ直接触れない連想", prompt)
        self.assertIn("証拠分析を続けず少し付き合ってよい", prompt)
        self.assertIn("正解行動を指示する攻略役にならない", prompt)
        self.assertIn("GM本文は確定事実だけ", "".join(user_packet["instructions"]))
        self.assertEqual((state.location, state.discovered), before)

    def test_prompt_prioritizes_current_scene_and_prevents_repetition(self):
        prompt = self.make_game().companion_banter_prompt()

        self.assertIn("優先順は、現在のGM事実、今回の開示、現在の場所・対象・行動、同一ターンの先行発言、過去会話", prompt)
        self.assertIn("そのまま再出力せず", prompt)
        self.assertIn("同じ内容の言い換えも避け", prompt)
        self.assertIn("現在の場面に合う新しい反応や発展", prompt)
        self.assertIn("自然につながらないなら使用せず", prompt)

    def test_prompt_encourages_dialogue_without_fixed_consensus(self):
        prompt = self.make_game().companion_banter_prompt()

        self.assertIn("人物関係と卓の空気を作る発言も正規の仲間会話", prompt)
        self.assertIn("事件解決に役立たなくてよい", prompt)
        self.assertIn("全員が調査対象へ意見を言う必要はない", prompt)
        self.assertIn("誰がどの会話役をしてもよい", prompt)
        self.assertIn("0〜3人が自然なときだけ", prompt)

    def test_prompt_broadens_each_companion_beyond_evidence_roles(self):
        prompt = self.make_game().companion_banter_prompt()

        self.assertIn("事件の解説役ではない", prompt)
        self.assertIn("何も言わないことがある", prompt)
        self.assertIn("発言は事件の仮説でなくてよく", prompt)
        self.assertIn("場違いな連想", prompt)
        self.assertIn("怖がるだけでなく", prompt)
        self.assertIn("事件分析をまとめる役ではない", prompt)

    def test_recent_banter_is_single_turn_labeled_and_separate_from_current_event(self):
        game = self.make_game()
        state = State("cliff_path")
        old_intent = {"raw": "ランタンを見る", "action_type": "inspect", "target_id": "broken_lantern"}
        game.remember_companion_turn(
            [
                "ニコ: 一つ目。",
                "リュート: 二つ目。",
                "ピピ: 三つ目。",
                "ニコ: 四つ目。",
                "リュート: 五つ目。",
            ],
            old_intent,
            state,
        )
        # A stale fallback cache must not be merged back into the latest turn.
        game.last_banter = {"output": "ニコ: 古い別ターン。"}

        current_intent = {"raw": "足跡を見る", "action_type": "inspect", "target_id": "cliff_footprints"}
        packet = game.packet(current_intent, [], state)
        history = packet["recent_companion_lines"]

        self.assertEqual(set(packet), {"current_event", "current_observations", "recent_companion_lines", "safety"})
        self.assertEqual(packet["current_event"]["target_id"], "cliff_footprints")
        self.assertEqual(history["label"], "reference_only_past_turn")
        self.assertEqual(history["previous_scene"]["target"], "broken_lantern")
        # A new inspect target retains the previous scene metadata for
        # diagnostics, but does not expose its wording to the model.
        self.assertEqual(history["lines"], [])
        self.assertNotIn("ニコ: 一つ目。", history["lines"])
        self.assertNotIn("ニコ: 古い別ターン。", history["lines"])
        self.assertNotIn("リュート: 二つ目。", packet["current_observations"])
        self.assertIn("コピーや言い換え再出力は禁止", history["usage"])
        self.assertTrue(any("世界設定や発見済み情報として扱わない" in x for x in packet["safety"]))

        game.remember_companion_turn([], current_intent, state)
        self.assertEqual(game.recent_companion_lines(), [])

    def test_table_renderer_reads_history_then_saves_current_response_once(self):
        game = self.make_game()
        state = State("light_room")
        old_intent = {"raw": "レンズを見る", "action_type": "inspect", "target_id": "lighthouse_lens"}
        game.remember_companion_turn(["ニコ: 古いレンズの台詞。"], old_intent, state)
        captured = []

        def fake_post_json(url, body, timeout, tag):
            captured.append(json.loads(body["messages"][1]["content"]))
            self.assertEqual(game.last_companion_turn["context"]["target"], "lighthouse_lens")
            return {"choices": [{"message": {"content": "GM: 弁を調べた。\nリュート: 少し休もうぜ。"}}]}

        game.post_json = fake_post_json
        with patch.dict(os.environ, {"LLM_PROVIDER": "llama_cpp"}):
            game.render_table_turn(
                ["GM: 弁を調べた。"],
                {"raw": "供給弁を見る", "action_type": "inspect", "target_id": "oil_valve"},
                {"status": "ok", "category": "no_reveal"}, [], state,
            )

        self.assertEqual(len(captured), 1)
        safe = captured[0]["safe_banter_packet"]
        self.assertEqual(safe["current_event"]["target_id"], "oil_valve")
        self.assertEqual(safe["recent_companion_lines"]["previous_scene"]["target"], "lighthouse_lens")
        self.assertEqual(safe["recent_companion_lines"]["lines"], [])
        self.assertNotIn("古いレンズの台詞", json.dumps(safe["current_observations"], ensure_ascii=False))
        self.assertEqual(game.last_companion_turn["context"]["target"], "oil_valve")
        self.assertEqual(game.recent_companion_lines(), ["リュート: 少し休もうぜ。"])

    def test_companion_observation_reduction_keeps_canonical_gm_discovery(self):
        game = self.make_game()
        state = State("light_room")
        public_text = game.disc["lens_misaligned"]["public_text"]
        captured = []

        def fake_post_json(url, body, timeout, tag):
            captured.append(json.loads(body["messages"][1]["content"]))
            return {"choices": [{"message": {"content": "GM: " + public_text}}]}

        game.post_json = fake_post_json
        with patch.dict(os.environ, {"LLM_PROVIDER": "llama_cpp"}):
            game.render_table_turn(
                ["GM: レンズを詳しく確認した。", "発見: " + public_text],
                {"raw": "レンズを見る", "action_type": "inspect", "target_id": "lighthouse_lens"},
                {"status": "ok", "category": "discoverable"},
                [{"type": "discoverable_revealed", "id": "lens_misaligned"}], state,
            )

        sent = captured[0]
        self.assertEqual(sent["canonical_gm_text"], "GM: レンズを詳しく確認した。")
        self.assertEqual(sent["discovery_log_lines_for_context"], ["発見: " + public_text])
        self.assertEqual(sent["safe_banter_packet"]["current_observations"], [public_text])

    def test_invalid_unified_response_clears_history_without_second_llm_call(self):
        game = self.make_game()
        state = State("light_room")
        game.remember_companion_turn(
            ["ニコ: 前回の台詞。"],
            {"action_type": "inspect", "target_id": "lighthouse_lens"}, state,
        )
        calls = []

        def fake_post_json(url, body, timeout, tag):
            calls.append(tag)
            return {"choices": [{"message": {"content": ""}}]}

        game.post_json = fake_post_json
        with patch.dict(os.environ, {"LLM_PROVIDER": "llama_cpp"}):
            notes, banter = game.render_table_turn(
                ["GM: 弁を調べた。"],
                {"raw": "供給弁を見る", "action_type": "inspect", "target_id": "oil_valve"},
                {"status": "ok", "category": "no_reveal"}, [], state,
            )

        self.assertEqual(calls, ["TABLE_TURN"])
        self.assertEqual(notes, ["GM: 弁を調べた。"])
        self.assertEqual(banter, "")
        self.assertEqual(game.last_companion_turn, {})

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
