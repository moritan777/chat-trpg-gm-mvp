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
        self.assertNotIn(
            game.disc["tide_log_cave_time"]["public_text"],
            json.dumps(revealed_packet, ensure_ascii=False),
        )

    def test_revealed_object_still_uses_surface_companion_stage(self):
        game = self.make_game()
        state = State("light_room")
        intent = {"raw": "レンズを見る", "action_type": "inspect", "target_id": "lighthouse_lens"}
        event = [{"type": "discoverable_revealed", "id": "lens_misaligned"}]

        packet = game.packet(intent, event, state)
        observations = packet["current_observations"]

        self.assertEqual(
            observations,
            [game.objects["lighthouse_lens"]["surface_banter_observation"]],
        )
        self.assertNotIn(game.disc["lens_misaligned"]["public_text"], observations)
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

    def test_object_surface_text_fallback_and_empty_surface(self):
        game = self.make_game()
        state = State("light_room")
        obj = game.objects["lighthouse_lens"]
        obj.pop("surface_banter_observation", None)

        observations = game.packet(
            {"raw": "レンズを見る", "action_type": "inspect", "target_id": "lighthouse_lens"},
            [{"type": "discoverable_revealed", "id": "lens_misaligned"}], state,
        )["current_observations"]
        self.assertEqual(observations, [obj["surface_text"]])

        obj.pop("surface_text", None)
        observations = game.packet(
            {"raw": "レンズを見る", "action_type": "inspect", "target_id": "lighthouse_lens"},
            [{"type": "discoverable_revealed", "id": "lens_misaligned"}], state,
        )["current_observations"]
        self.assertEqual(observations, [])

    def test_revealed_npc_does_not_promote_public_or_internal_text(self):
        game = self.make_game()
        state = State("harbor")
        packet = game.packet(
            {"raw": "漁師に聞く", "action_type": "ask", "target_id": "fisherman"},
            [{"type": "discoverable_revealed", "id": "fisherman_blue_light"}], state,
        )

        self.assertEqual(packet["current_observations"], [])
        serialized = json.dumps(packet, ensure_ascii=False)
        self.assertNotIn(game.disc["fisherman_blue_light"]["public_text"], serialized)
        self.assertNotIn(game.npcs["fisherman"]["banter_observation"], serialized)

    def test_location_uses_safe_surface_observation(self):
        game = self.make_game()
        state = State("cliff_path")
        packet = game.packet(
            {"raw": "岬へ行く", "action_type": "move", "target_id": "cliff_path"}, [], state,
        )

        self.assertEqual(
            packet["current_observations"],
            [game.locs["cliff_path"]["surface_banter_observation"]],
        )
        self.assertNotIn(game.locs["cliff_path"]["banter_observation"], packet["current_observations"])

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
        self.assertIn("GMの発見結果を説明し直したり", prompt)
        self.assertIn("毎回原因や次の行動を推理したりする必要はない", prompt)
        self.assertIn("先行仲間への反応を優先候補にできる", prompt)
        instructions = "".join(user_packet["instructions"])
        self.assertIn("仲間発言は0〜3行", instructions)
        self.assertIn("同じ人物が短く再応答してよい", instructions)
        self.assertIn("全員を一度ずつ出す必要はない", instructions)
        self.assertIn("GM本文は確定事実だけ", "".join(user_packet["instructions"]))
        self.assertEqual((state.location, state.discovered), before)

    def test_system_prompt_prioritizes_observation_without_weakening_discovery(self):
        game = self.make_game()
        state = State("light_room")
        captured = []

        def fake_post_json(url, body, timeout, tag):
            captured.append(body)
            return {"choices": [{"message": {"content": "GM: レンズを確認した。"}}]}

        game.post_json = fake_post_json
        with patch.dict(os.environ, {"LLM_PROVIDER": "llama_cpp"}):
            game.render_table_turn(
                ["GM: レンズを確認した。", "発見: " + game.disc["lens_misaligned"]["public_text"]],
                {"raw": "レンズを見る", "action_type": "inspect", "target_id": "lighthouse_lens"},
                {"status": "ok", "category": "discoverable"},
                [{"type": "discoverable_revealed", "id": "lens_misaligned"}], state,
            )

        prompt = captured[0]["messages"][0]["content"]
        self.assertIn("観察事実を述べる", prompt)
        self.assertIn("正式発見はエンジンが後続のGM行として原文表示", prompt)
        self.assertIn("LLMのGM本文では詳しく反復しない", prompt)
        self.assertIn("canonical_gm_textに沿って", prompt)
        self.assertIn("犯人、動機、意図、背景事情、証拠隠滅、次の正解行動を追加しない", prompt)
        self.assertIn("硬い報告書や検査報告の口調にはしない", prompt)

    def test_prompt_separates_fact_priority_from_conversation_focus(self):
        prompt = self.make_game().companion_banter_prompt()

        self.assertIn("事実としては現在のGM事実、今回の正式な開示", prompt)
        self.assertIn("何について話すかはGMの最後の一文に従属しない", prompt)
        self.assertIn("仲間の冗談、仮説、勘違い、過去会話は事実の根拠ではない", prompt)
        self.assertIn("過去台詞をコピーまたは言い換え再出力しない", prompt)

    def test_prompt_encourages_dialogue_without_fixed_consensus(self):
        prompt = self.make_game().companion_banter_prompt()

        self.assertIn("事件解決だけでなく人物関係と卓の空気も作る", prompt)
        self.assertIn("GMへの別コメントより先行仲間への反応を優先候補", prompt)
        self.assertIn("同じ発見へ全員が別コメントを出す必要もない", prompt)
        self.assertIn("仲間同士の話題からGMへ戻る必要", prompt)
        self.assertIn("短い応答でまとまればそこで終える", prompt)
        self.assertIn("掛け合いは必須ではない", prompt)
        self.assertIn("仲間発言は0〜3行", prompt)
        self.assertIn("同じ人物が短い再応答で再び話してよい", prompt)
        self.assertIn("全員を一度ずつ出す必要はなく", prompt)
        self.assertNotIn("0〜3人", prompt)

    def test_prompt_allows_natural_closure_of_directed_companion_actions(self):
        prompt = self.make_game().companion_banter_prompt()

        self.assertIn("質問、依頼、心配、ツッコミ、茶化し", prompt)
        self.assertIn("袖を掴むなどの働きかけ", prompt)
        self.assertIn("相手が自然なら短く応答してよい", prompt)
        self.assertIn("独立コメントの列で終わらせる必要はない", prompt)
        self.assertIn("沈黙や無視が自然なら応答しなくてもよい", prompt)
        self.assertIn("短い応答でまとまればそこで終える", prompt)
        self.assertIn("掛け合いは必須ではない", prompt)

    def test_prompt_broadens_each_companion_beyond_evidence_roles(self):
        prompt = self.make_game().companion_banter_prompt()

        self.assertIn("証拠をまとめる解説役ではない", prompt)
        self.assertIn("足場、作業の負担、道具、仲間の安全", prompt)
        self.assertIn("推理もするが", prompt)
        self.assertIn("ツッコミ、気遣い、便乗、沈黙を選べる", prompt)
        self.assertIn("事件仮説に限らず", prompt)
        self.assertIn("妙な例え", prompt)
        self.assertIn("妙な例え、疑問、使い道", prompt)
        self.assertIn("身体感覚、急な脱線", prompt)
        self.assertIn("有益である必要もない", prompt)
        self.assertIn("怖がるだけでなく", prompt)
        self.assertIn("景色や物、匂いや汚れ、疲れ", prompt)
        self.assertIn("仲間へ反応し", prompt)
        self.assertIn("事件分析をまとめる役ではない", prompt)
        self.assertIn("Discoverable開示時も原因や仮説を述べなくてよい", prompt)

    def test_prompt_treats_non_investigative_curiosity_as_normal(self):
        prompt = self.make_game().companion_banter_prompt()

        self.assertIn("事件の意味だけに注目しなくてよい", prompt)
        self.assertIn("環境、物の性質、身体的な負担", prompt)
        self.assertIn("仲間の様子、どうでもよい細部", prompt)
        self.assertIn("正規の話題", prompt)
        self.assertIn("シナリオ上の重要度と人物の興味は別", prompt)
        self.assertIn("推理しても別のことを気にしてもよい", prompt)

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
        self.assertEqual(
            sent["safe_banter_packet"]["current_observations"],
            [game.objects["lighthouse_lens"]["surface_banter_observation"]],
        )
        self.assertNotIn(public_text, sent["safe_banter_packet"]["current_observations"])

    def test_gm_context_keeps_all_script_discoveries_for_gm_and_both(self):
        cases = (
            ("broken_lantern", "broken_lantern_clue", "ランタンを見る"),
            ("cliff_footprints", "cliff_tracks_to_shore", "足跡を見る"),
            ("blood_stain", "blood_drag_clue", "染みを見る"),
            ("rope_marks", "rope_to_shore", "ロープ跡を見る"),
            ("lighthouse_lens", "lens_misaligned", "レンズを見る"),
            ("oil_valve", "oil_valve_tampered", "供給弁を見る"),
        )
        for display in ("gm", "both"):
            for target_id, discoverable_id, raw in cases:
                with self.subTest(display=display, target=target_id):
                    game = self.make_game()
                    state = State("light_room")
                    public_text = game.disc[discoverable_id]["public_text"]
                    captured = []
                    game.post_json = lambda url, body, timeout, tag: (
                        captured.append(json.loads(body["messages"][1]["content"]))
                        or {"choices": [{"message": {"content": "GM: 表層描写。\nニコ: 気になるね。"}}]}
                    )

                    with patch.dict(os.environ, {"LLM_PROVIDER": "llama_cpp", "DISCOVERY_DISPLAY": display}):
                        rendered, _ = game.render_table_turn(
                            ["GM: 表層を確認した。", "発見: " + public_text],
                            {"raw": raw, "action_type": "inspect", "target_id": target_id},
                            {"status": "ok", "category": "discoverable"},
                            [{"type": "discoverable_revealed", "id": discoverable_id}], state,
                        )

                    self.assertEqual(captured[0]["discovery_display"], display)
                    self.assertEqual(captured[0]["discovery_log_lines_for_context"], ["発見: " + public_text])
                    self.assertNotIn(public_text, captured[0]["safe_banter_packet"]["current_observations"])
                    official_line = "GM: " + public_text
                    self.assertIn(official_line, rendered)
                    self.assertLess(rendered.index("GM: 表層描写。"), rendered.index(official_line))
                    self.assertLess(rendered.index(official_line), rendered.index("ニコ: 気になるね。"))
                    if display == "gm":
                        self.assertNotIn("発見: " + public_text, rendered)
                    else:
                        self.assertIn("発見: " + public_text, rendered)

    def test_tag_display_retains_separate_discovery_context_without_gm_repetition_instruction(self):
        game = self.make_game()
        state = State("light_room")
        public_text = game.disc["lens_misaligned"]["public_text"]
        captured = []
        game.post_json = lambda url, body, timeout, tag: (
            captured.append(body) or {"choices": [{"message": {"content": "GM: レンズを確認した。"}}]}
        )

        with patch.dict(os.environ, {"LLM_PROVIDER": "llama_cpp", "DISCOVERY_DISPLAY": "tag"}):
            rendered, _ = game.render_table_turn(
                ["GM: レンズを確認した。", "発見: " + public_text],
                {"raw": "レンズを見る", "action_type": "inspect", "target_id": "lighthouse_lens"},
                {"status": "ok", "category": "discoverable"},
                [{"type": "discoverable_revealed", "id": "lens_misaligned"}], state,
            )

        packet = json.loads(captured[0]["messages"][1]["content"])
        prompt = captured[0]["messages"][0]["content"]
        self.assertEqual(packet["discovery_log_lines_for_context"], ["発見: " + public_text])
        self.assertIn("エンジンが別表示する正式発見", prompt)
        self.assertEqual(rendered, ["GM: レンズを確認した。", "発見: " + public_text])
        self.assertNotIn("GM: " + public_text, rendered)

    def test_official_discoveries_use_structured_events_and_avoid_double_prefix(self):
        game = self.make_game()
        events = [
            {"type": "discoverable_revealed", "id": "lens_misaligned"},
            {"type": "ignored", "id": "oil_valve_tampered"},
        ]
        public_text = game.disc["lens_misaligned"]["public_text"]

        self.assertEqual(game.official_discovery_texts(events), [public_text])
        self.assertEqual(game.official_discovery_gm_lines(events), ["GM: " + public_text])

        game.disc["lens_misaligned"]["public_text"] = "GM: 既に接頭辞がある。"
        self.assertEqual(game.official_discovery_gm_lines(events), ["GM: 既に接頭辞がある。"])

    def test_invalid_renderer_still_places_official_discovery_once(self):
        for response in ("", "```invalid```", "GM: 観察。\n発見: 禁止ラベル"):
            with self.subTest(response=response):
                game = self.make_game()
                state = State("light_room")
                public_text = game.disc["lens_misaligned"]["public_text"]
                calls = []
                game.post_json = lambda url, body, timeout, tag: (
                    calls.append(tag) or {"choices": [{"message": {"content": response}}]}
                )

                with patch.dict(os.environ, {"LLM_PROVIDER": "llama_cpp", "DISCOVERY_DISPLAY": "gm"}):
                    rendered, banter = game.render_table_turn(
                        ["GM: レンズを確認した。", "発見: " + public_text],
                        {"raw": "レンズを見る", "action_type": "inspect", "target_id": "lighthouse_lens"},
                        {"status": "ok", "category": "discoverable"},
                        [{"type": "discoverable_revealed", "id": "lens_misaligned"}], state,
                    )

                self.assertEqual(calls, ["TABLE_TURN"])
                self.assertEqual(rendered, ["GM: レンズを確認した。", "GM: " + public_text])
                self.assertEqual(banter, "")
                self.assertEqual(game.last_companion_turn, {})

    def test_companion_history_preserves_repeated_speaker_order(self):
        game = self.make_game()
        state = State("light_room")
        lines = ["ニコ: 一言目。", "ピピ: 返答。", "ニコ: 再応答。"]
        game.remember_companion_turn(
            lines,
            {"raw": "レンズを見る", "action_type": "inspect", "target_id": "lighthouse_lens"},
            state,
        )

        self.assertEqual(game.recent_companion_lines(), lines)

    def test_invalid_unified_responses_clear_history_without_second_llm_call(self):
        for response in ("", "```invalid```", "GM: 弁を調べた。\n発見: 禁止ラベル"):
            with self.subTest(response=response):
                game = self.make_game()
                state = State("light_room")
                game.remember_companion_turn(
                    ["ニコ: 前回の台詞。"],
                    {"action_type": "inspect", "target_id": "lighthouse_lens"}, state,
                )
                calls = []

                def fake_post_json(url, body, timeout, tag):
                    calls.append(tag)
                    return {"choices": [{"message": {"content": response}}]}

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
