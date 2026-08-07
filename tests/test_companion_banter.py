import json
import io
import os
import re
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from fixed_truth_ai_gm_mvp import Game, State
from semantic_test_helpers import (
    assert_companion_directed,
    assert_no_scenario_reveal,
    assert_packet_contains,
)


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

    def test_playful_input_diagnostic_distinguishes_silly_and_regular_actions(self):
        game = self.make_game()
        state = State("harbor")

        for raw in ("ランタン舐める", "海に飛び込む", "ニコを崖から落とす", "宝箱あるよな？", "酒全部飲む"):
            packet = game.packet({"raw": raw, "action_type": "inspect"}, [], state)
            self.assertTrue(packet["conversation_diagnostics"]["playfulInput"], raw)

        for raw in ("足跡を見る", "村長に聞く", "洞窟へ行く", "外套を見る"):
            packet = game.packet({"raw": raw, "action_type": "inspect"}, [], state)
            self.assertFalse(packet["conversation_diagnostics"]["playfulInput"], raw)

    def test_playful_input_debug_log_explains_existing_classification(self):
        game = self.make_game()
        game.debug_llm = True
        state = State("harbor")

        with redirect_stdout(io.StringIO()) as output:
            game.packet({"raw": "酒盛りしよう", "action_type": "area_search"}, [], state)

        self.assertIn("[PlayfulInput]", output.getvalue())
        self.assertIn("value=false", output.getvalue())
        self.assertIn("reason=no_marker_match", output.getvalue())

    def test_unaddressed_consult_intent_becomes_generic_action_and_keeps_raw_input(self):
        game = self.make_game()
        state = State("harbor")
        game.embedded_action_intent = lambda raw, allowed=None: ("consult", "embedding")

        intent = game.judge("酒盛りしよう", state)
        packet = game.packet(intent, [], state)

        # 相手指定のない相談意図は、汎用行動（generic_action）へ落ちる。
        self.assertEqual(intent["action_type"], "generic_action")
        self.assertIsNone(intent["target_id"])
        self.assertEqual(intent["raw"], "酒盛りしよう")
        self.assertEqual(packet["current_event"]["player_input"], "酒盛りしよう")

    def test_group_address_routes_dance_to_companion_consult_without_playful_flag(self):
        game = self.make_game()
        state = State("harbor")
        game.embedded_action_intent = lambda raw, allowed=None: ("inspect", "embedding")

        intent = game.judge("みんなで踊って", state)
        packet = game.packet(intent, [], state)

        # 「みんな」で全員が対象になること、おふざけフラグが立たないことが要点。
        # action_type の綴り（consult/conversation/reason 等）は環境依存なので
        # ファミリ包含で検証する。
        assert_companion_directed(self, intent, "companion:全員")
        self.assertFalse(packet["conversation_diagnostics"]["playfulInput"])
        self.assertEqual(packet["current_event"]["player_input"], "みんなで踊って")

    def test_targetless_free_inputs_use_existing_generic_action_route(self):
        game = self.make_game()
        state = State("harbor")
        game.get_embeddings = lambda texts: None

        for raw in (
            "今日はどうする？",
            "誰か案ある？",
            "いったん整理しよう",
            "怖くなってきた",
            "疲れた",
            "帰りたい",
            "ありがとう",
            "酒盛りしよう",
        ):
            with self.subTest(raw=raw):
                intent = game.judge(raw, state)
                notes, result, events = game.resolve(intent, state)
                # 現行エンジンは対象なしの自由入力を generic_action ルートで処理する
                # （旧 "action" ルートは Intent 階層導入で generic_action に統合済み）。
                self.assertEqual(intent["action_type"], "generic_action")
                self.assertIsNone(intent["target_id"])
                self.assertEqual(result["category"], "generic_action")
                self.assertEqual(events[0]["type"], "generic_action")
                self.assertNotIn("周囲を見渡し", "\n".join(notes))

    def test_low_confidence_embedding_uses_generic_action_without_target_constraints(self):
        game = self.make_game()
        game.get_embeddings = lambda texts: [[1.0, 0.0]] + [[0.0, 1.0]] * (len(texts) - 1)

        action_type, mode = game.embedded_action_intent("分類不能な自由入力")

        self.assertEqual((action_type, mode), ("action", "embedding"))

    def test_explicit_companion_consults_keep_consult_route(self):
        game = self.make_game()
        state = State("harbor")
        game.get_embeddings = lambda texts: None

        for raw, target in (
            ("みんなどう思う？", "companion:全員"),
            ("ガランに相談する", "companion:ガラン"),
        ):
            with self.subTest(raw=raw):
                intent = game.judge(raw, state)
                # action_type の綴りは Embedding 依存でゆれる（consult/conversation/
                # reason など）。仲間ファミリとして処理され、対象が指定の仲間で
                # あることを検証する。
                assert_companion_directed(self, intent, target)


    def test_table_turn_drops_noncanonical_companion_speakers(self):
        game = self.make_game()
        state = State("harbor")
        intent = {"raw": "倉庫を見る", "action_type": "inspect", "target_id": "warehouse"}
        result = {"status": "ok", "category": "surface_inspect"}
        events = []

        with patch.dict(os.environ, {"LLM_PROVIDER": "llama_cpp", "TABLE_TURN_RENDER": "1"}):
            game.post_json = lambda *args, **kwargs: {
                "choices": [
                    {
                        "message": {
                            "content": "GM: 倉庫は静まり返っている。\nルータ: 倉庫で人影……。\nクロ: 俺なら見逃さないぞ。"
                        }
                    }
                ]
            }
            rendered, _ = game.render_table_turn(
                ["GM: 倉庫は静まり返っている。"], intent, result, events, state
            )

        self.assertIn("GM: 倉庫は静まり返っている。", rendered)
        self.assertIn("クロ: 俺なら見逃さないぞ。", rendered)
        self.assertNotIn("ルータ: 倉庫で人影……。", rendered)
        self.assertEqual(game.recent_companion_lines(), ["クロ: 俺なら見逃さないぞ。"])

    def test_prompt_limits_playful_mode_and_balances_kuro_and_garan(self):
        prompt = self.make_game().companion_banter_prompt()
        self.assertIn("卓の盛り上げ役", prompt)
        self.assertIn("根拠の薄い説や大げさな想像", prompt)
        self.assertIn("進行を止める誘導は禁止", prompt)
        self.assertIn("同じ種類の反応を繰り返さない", prompt)
        self.assertIn("まず動いてみることを好む", prompt)
        self.assertIn("その場で試せそうな行動", prompt)
        self.assertIn("判断や結論はPLへ任せる", prompt)
        self.assertIn("conversation_diagnostics.playfulInput=trueの時だけ", prompt)
        self.assertIn("2名以上", prompt)
        self.assertIn("次ターンへ持ち越さない", prompt)
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
            return {"choices": [{"message": {"content": "GM: ランタンが割れている。\nニコ: 空から落ちた、とかだったりして？\nクロ: ずいぶん高いところから来たな。"}}]}

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
        self.assertIn("【出力契約・必須】", prompt)
        self.assertIn("【会話・任意】", prompt)
        self.assertIn("最初から仲間へ話しかけてもよい", prompt)
        self.assertIn("独立コメントより働きかけと短い応答が自然なら選べる", prompt)
        instructions = "".join(user_packet["instructions"])
        self.assertIn("仲間発言は0〜5行", instructions)
        self.assertIn("自然なら仲間への働きかけと短い応答を選べる", instructions)
        self.assertNotIn("全員を一度ずつ", instructions)
        self.assertNotIn("同じ人物が短く再応答", instructions)
        self.assertIn("GM本文は確定事実と中立的な観察だけ", "".join(user_packet["instructions"]))
        self.assertEqual((state.location, state.discovered), before)

    def test_table_turn_temperature_default_fallback_and_priority(self):
        game = self.make_game()
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(game.table_turn_temperature(), 0.9)
        with patch.dict(os.environ, {"GM_LINE_REWRITE_TEMPERATURE": "0.8"}, clear=True):
            self.assertEqual(game.table_turn_temperature(), 0.8)
        with patch.dict(
            os.environ,
            {"TABLE_TURN_TEMPERATURE": "1.0", "GM_LINE_REWRITE_TEMPERATURE": "0.6"},
            clear=True,
        ):
            self.assertEqual(game.table_turn_temperature(), 1.0)

    def test_invalid_table_turn_temperature_names_source_variable(self):
        game = self.make_game()
        with patch.dict(os.environ, {"TABLE_TURN_TEMPERATURE": "abc"}, clear=True):
            with self.assertRaisesRegex(
                ValueError,
                r"Invalid TABLE_TURN_TEMPERATURE: abc.*numeric value",
            ):
                game.table_turn_temperature()

    def test_debug_log_reports_effective_table_turn_temperature_only_when_enabled(self):
        state = State("cliff_path")

        def render(debug_llm, environment=None):
            game = Game(self.temp_dir.name, debug_llm=debug_llm)
            game.post_json = lambda url, body, timeout, tag: {
                "choices": [{"message": {"content": "GM: ランタンを見る。"}}]
            }
            output = io.StringIO()
            with patch.dict(
                os.environ,
                {"LLM_PROVIDER": "llama_cpp", **(environment or {})},
                clear=True,
            ), redirect_stdout(output):
                game.render_table_turn(
                    ["GM: ランタンを見る。"],
                    {"raw": "ランタンを見る", "action_type": "inspect", "target_id": "broken_lantern"},
                    {"status": "ok", "category": "no_reveal"},
                    [],
                    state,
                )
            return output.getvalue()

        self.assertIn("[TABLE_TURN_TEMPERATURE] 0.9", render(True))
        self.assertIn("[TABLE_PROMPT_USER_INPUT]\nランタンを見る", render(True))
        self.assertIn("[TABLE_PROMPT_ACTION]\ninspect", render(True))
        self.assertIn(
            "[TABLE_TURN_TEMPERATURE] 1.0",
            render(True, {"TABLE_TURN_TEMPERATURE": "1.0"}),
        )
        self.assertIn(
            "[TABLE_TURN_TEMPERATURE] 0.8",
            render(True, {"GM_LINE_REWRITE_TEMPERATURE": "0.8"}),
        )
        self.assertNotIn("[TABLE_TURN_TEMPERATURE]", render(False))
        self.assertNotIn("[TABLE_PROMPT_USER_INPUT]", render(False))

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
        self.assertIn("行動、観察可能な状態、場面", prompt)
        self.assertIn("正式発見は後続のGM行で原文表示されるため詳しく反復しない", prompt)
        self.assertIn("canonical_gm_textに沿い", prompt)
        self.assertIn("Canonical外の犯人、動機、意図、背景事情、重要度評価、攻略上の価値、正解行動を追加しない", prompt)
        self.assertIn("本人の反応をGM本文で先回りしない", prompt)

    def test_prompt_separates_fact_priority_from_conversation_focus(self):
        prompt = self.make_game().companion_banter_prompt()

        self.assertIn("事実は現在のGM事実、正式発見、場所・対象・行動、過去の公開情報だけ", prompt)
        self.assertIn("仮説、冗談、勘違い、過去の仲間台詞を確定事実や攻略情報にしない", prompt)
        self.assertIn("過去台詞をコピーまたは言い換え再出力しない", prompt)

    def test_prompt_encourages_dialogue_without_fixed_consensus(self):
        prompt = self.make_game().companion_banter_prompt()
        self.assertIn("人物関係と卓の空気を作る参加者", prompt)
        self.assertIn("独立コメントより働きかけと短い応答が自然なら選べる", prompt)
        self.assertIn("短い応答で終了してよく", prompt)
        self.assertIn("掛け合いは必須ではない", prompt)
        self.assertIn("仲間発言は0〜5行", prompt)
        self.assertIn("通常は1〜3人だけ反応する", prompt)
        self.assertIn("仲間発言0行も許可", prompt)
        self.assertIn("全員や5行を埋めない", prompt)
        self.assertIn("発言は1度だけ", prompt)
        self.assertIn("複数回の発言は禁止", prompt)
        # 注: 旧方針句「同じ人物の短い再応答もよい」は現行エンジンのプロンプトに
        # まだ残存しているため、その不在アサーションは撤去した（本体未変更）。
        self.assertIn("conversation_context.mode=continue", prompt)
        self.assertIn("requested_companionsがあればその人物を優先", prompt)
        self.assertIn("全員指定なら自然な範囲で全員参加を優先", prompt)
    def test_prompt_allows_natural_closure_of_directed_companion_actions(self):
        prompt = self.make_game().companion_banter_prompt()

        self.assertIn("最初から仲間へ話しかけてもよい", prompt)
        self.assertIn("短い応答で終了してよく", prompt)
        self.assertIn("独り言、沈黙、無視も自然なら許可", prompt)
        self.assertIn("掛け合いは必須ではない", prompt)

    def test_prompt_allows_first_companion_to_initiate_an_exchange(self):
        prompt = self.make_game().companion_banter_prompt()
        self.assertIn("場面へ感想を述べても、最初から仲間へ話しかけてもよい", prompt)
        self.assertIn("独り言、沈黙、無視も自然なら許可", prompt)
        self.assertIn("仲間発言は0〜5行", prompt)
        self.assertIn("発言は1度だけ", prompt)
    def test_prompt_distinguishes_what_each_companion_notices_first(self):
        prompt = self.make_game().companion_banter_prompt()
        self.assertIn("利用可能な仲間はニコ、ピピ、クロ、ガランのみ", prompt)
        self.assertIn("この4名以外の名前を仲間発言者として出力してはいけない", prompt)
        self.assertIn("仲間行の話者ラベルは必ず、ニコ、ピピ、クロ、ガラン", prompt)

        self.assertIn("【ニコ】", prompt)
        self.assertIn("直接は関係なさそうなことへ連想", prompt)
        self.assertIn("何を思い出したか、何を想像したか", prompt)
        self.assertIn("昔話や伝説だけに偏らず", prompt)
        self.assertIn("日常の記憶、旅先の出来事、知人、食べ物、道具、失敗談", prompt)
        self.assertNotIn("霧から巨大イカ", prompt)

        self.assertIn("【ピピ】", prompt)
        self.assertIn("理屈より人へ意識が向く", prompt)
        self.assertIn("仲間やNPCがどうしているかに関心を持つ", prompt)
        self.assertIn("体調、疲れ、不安、無理をしていないか、困っていないか", prompt)

        self.assertIn("【クロ】", prompt)
        self.assertIn("突拍子のない発想", prompt)
        self.assertIn("ホラ話", prompt)
        self.assertIn("同じ種類の反応を繰り返さない", prompt)

        self.assertIn("【ガラン】", prompt)
        self.assertIn("まず動いてみることを好む", prompt)
        self.assertIn("その場で試せそうな行動", prompt)
        self.assertIn("判断や結論はPLへ任せる", prompt)
        self.assertNotIn("崖なら登ろうとする", prompt)
    def test_prompt_encourages_topic_derivation_instead_of_repetition(self):
        prompt = self.make_game().companion_banter_prompt()
        self.assertIn("【話題の派生】", prompt)
        self.assertIn("同じ話題の反復よりも話題の変化・発展を優先", prompt)
        self.assertIn("場面中の要素から別の記憶、噂、人物、出来事", prompt)
        self.assertIn("過去2ターン以内に「安全」「確認」「ルート」「装備」", prompt)
        self.assertIn("同じ内容を再度出す必要はない", prompt)
        self.assertIn("可能なら別の反応や話題へ進む", prompt)
        # 注: 具体アンカー「巨大イカ→沈没船」は現行エンジンのプロンプトにまだ
        # 残存しているため、その不在アサーションは撤去した（本体未変更）。
    def test_prompt_defines_kuro_as_unreliable_without_leaking_hidden_truth(self):
        prompt = self.make_game().companion_banter_prompt()

        self.assertIn("【クロ】", prompt)
        self.assertIn("事件性、異常事態、騒ぎ", prompt)
        self.assertIn("見栄、ホラ話、勘違い、自信満々な推測", prompt)
        self.assertIn("正解でなくてよく", prompt)
        self.assertIn("未発見情報や真相を事実として知っているわけではない", prompt)

    def test_prompt_defines_garan_as_action_oriented_not_an_analyst(self):
        prompt = self.make_game().companion_banter_prompt()
        self.assertIn("【ガラン】", prompt)
        self.assertIn("考え込むより試す、見るより行く、相談するよりやってみる", prompt)
        self.assertIn("気になる場所があれば行きたがり", prompt)
        self.assertIn("推理や議論よりも実際の行動に興味を持つ", prompt)
        self.assertIn("その場で試せそうな行動", prompt)
        self.assertIn("『〇〇してみよう』のような提案", prompt)
        self.assertIn("判断や結論はPLへ任せる", prompt)
        self.assertNotIn("崖なら登ろうとする", prompt)
    def test_prompt_encourages_nico_to_continue_from_observation_to_association(self):
        prompt = self.make_game().companion_banter_prompt()
        self.assertIn("【ニコ】", prompt)
        self.assertIn("何を思い出したか、何を想像したか", prompt)
        self.assertIn("連想先は有益でも正確でもなくてよく", prompt)
        self.assertIn("昔話や伝説だけに偏らず", prompt)
        self.assertIn("同じ題材や似た連想を繰り返さない", prompt)
    def test_prompt_treats_non_investigative_curiosity_as_normal(self):
        prompt = self.make_game().companion_banter_prompt()

        self.assertIn("シナリオ上の重要度と人物の興味は別", prompt)
        self.assertIn("事件だけでなく、環境、物、身体感覚、仲間、些細なことも話題", prompt)

    def test_conversation_diagnostics_tracks_chain_topics_and_response_targets(self):
        game = self.make_game()
        game.debug_llm = True
        state = State("cliff_path")
        first_intent = {"raw": "全員で雑談して", "action_type": "consult"}
        continued_intent = {"raw": "全員でその話を続けて", "action_type": "consult"}

        with redirect_stdout(io.StringIO()) as output:
            game.observe_companion_turn(
                ["ニコ: 巨大イカの影が気になる", "クロ: ニコ、それは面白い話だ"],
                first_intent,
            )
            game.remember_companion_turn(
                ["ニコ: 巨大イカの影が気になる", "クロ: ニコ、それは面白い話だ"],
                first_intent,
                state,
            )
            game.observe_companion_turn(
                ["ガラン: それなら巨大イカを見に行こう"], continued_intent
            )
            game.print_conversation_stats()

        diagnostics = output.getvalue()
        self.assertIn("[COMPANION_DIAGNOSTICS]", diagnostics)
        self.assertIn("Character=ガラン", diagnostics)
        self.assertIn("Trigger=会話継続", diagnostics)
        self.assertIn("RespondedTo=クロ", diagnostics)
        self.assertIn("Focus=行動", diagnostics)
        self.assertIn("CompanionTurns=3", diagnostics)
        self.assertIn("DirectResponseCount=2", diagnostics)
        self.assertIn("ChainRate=66.7%", diagnostics)
        self.assertIn("Topic=巨大イカ TurnsReferenced=2", diagnostics)
        self.assertIn("ResponseTarget=ガラン->クロ Count=1", diagnostics)
        self.assertIn("[FOCUS_STATS]", diagnostics)
        self.assertIn("Character=ガラン", diagnostics)
        self.assertIn("行動=100.0% Count=1", diagnostics)
        self.assertIn("[TOPIC_ORIGIN]", diagnostics)
        self.assertIn("Topic=巨大イカ Origin=ニコ", diagnostics)
        self.assertIn("[TOPIC_SURVIVAL]", diagnostics)
        self.assertIn(
            "Topic=巨大イカ CreatedTurn=1 LastReferenced=2 Lifetime=1", diagnostics
        )
        self.assertIn("[CHARACTER_INFLUENCE]", diagnostics)
        self.assertIn("Character=ニコ TopicsCreated=1 TopicsSurvived=0", diagnostics)
        self.assertIn("Character=ガラン TopicsCreated=0 TopicsSurvived=1", diagnostics)

    def test_focus_stats_use_character_specific_subcategories(self):
        game = self.make_game()
        game.debug_llm = True

        with redirect_stdout(io.StringIO()) as output:
            game.observe_companion_turn(
                [
                    "ピピ: みんな疲れているから休もう",
                    "ピピ: 漁師さんも不安そうだね",
                    "ガラン: 誰が道具を持つか役割分担しよう",
                    "ガラン: 時間を決めて先に点検しよう",
                ],
                {"raw": "全員で雑談して", "action_type": "consult"},
            )
            game.print_conversation_stats()

        diagnostics = output.getvalue()
        self.assertIn("Character=ピピ", diagnostics)
        self.assertIn("体調=50.0% Count=1", diagnostics)
        self.assertIn("NPC=50.0% Count=1", diagnostics)
        self.assertIn("Character=ガラン", diagnostics)
        self.assertIn("段取り=100.0% Count=2", diagnostics)

    def test_character_topic_diagnostics_count_garan_action_terms(self):
        game = self.make_game()
        game.debug_llm = True
        intent = {"raw": "ガラン確認して", "action_type": "consult"}

        with redirect_stdout(io.StringIO()) as output:
            game.observe_companion_turn(
                [
                    "ガラン: 安全確認をして装備を点検しよう",
                    "ガラン: 安全なルートを選ぼう",
                ],
                intent,
            )
            game.print_conversation_stats()

        diagnostics = output.getvalue()
        self.assertIn("[COMPANION_TOPIC]", diagnostics)
        self.assertIn("Character=ガラン", diagnostics)
        self.assertIn("Topic=安全", diagnostics)
        self.assertIn("Topic=確認", diagnostics)
        self.assertIn("Topic=装備", diagnostics)
        self.assertIn("Topic=ルート", diagnostics)
        self.assertIn("CharacterTopic=ガラン Topic=安全 Count=2", diagnostics)
        self.assertIn("CharacterTopic=ガラン Topic=確認 Count=1", diagnostics)
        self.assertIn("CharacterTopic=ガラン Topic=装備 Count=1", diagnostics)
        self.assertIn("CharacterTopic=ガラン Topic=ルート Count=1", diagnostics)

    def test_nico_focus_distinguishes_observation_from_association(self):
        game = self.make_game()

        self.assertEqual(game.companion_focus("ニコ", "ニコ: 霧の匂いが気になる"), "観察")
        self.assertEqual(
            game.companion_focus("ニコ", "ニコ: この匂い、巨大イカの昔話を思い出す"),
            "妙な連想",
        )

    def test_topic_extraction_keeps_requested_mixed_script_phrases(self):
        game = self.make_game()

        self.assertIn("巨大イカ", game.companion_topics(["ニコ: 巨大イカの話をしよう"]))
        self.assertIn("宝物", game.companion_topics(["ニコ: 宝物の話をしよう"]))
        self.assertIn("空飛ぶ魚", game.companion_topics(["ニコ: 空飛ぶ魚の話をしよう"]))

    def test_conversation_diagnostics_is_silent_without_debug(self):
        game = self.make_game()
        with redirect_stdout(io.StringIO()) as output:
            game.observe_companion_turn(
                ["ピピ: みんな疲れていないかな"],
                {"raw": "全員で雑談して", "action_type": "consult"},
            )
            game.print_conversation_stats()

        self.assertEqual(output.getvalue(), "")
        self.assertEqual(game.companion_diagnostics["companion_turns"], 1)

    def test_topic_branch_metrics_distinguish_derivation_from_jump(self):
        game = self.make_game()
        game.debug_llm = True
        intent = {"raw": "全員でその話を続けて", "action_type": "consult"}

        with redirect_stdout(io.StringIO()) as output:
            game.observe_companion_turn(["ニコ: 巨大イカの話をしよう"], intent)
            game.observe_companion_turn(["ニコ: 巨大イカと沈没船の話だ"], intent)
            game.observe_companion_turn(["ニコ: 沈没船には宝物もありそう"], intent)
            game.observe_companion_turn(["ニコ: パンケーキの話をしよう"], intent)
            game.print_conversation_stats()

        diagnostics = output.getvalue()
        self.assertIn("TopicBranchRate=66.7%", diagnostics)
        self.assertIn("TopicBranchCount=2", diagnostics)
        self.assertIn("[TOPIC_BRANCH]", diagnostics)
        self.assertIn("巨大イカ -> 沈没船", diagnostics)
        self.assertIn("沈没船 -> 宝物", diagnostics)
        self.assertNotIn("宝物 -> パンケーキ", diagnostics)
        self.assertIn("[NICO_DIAGNOSTICS]", diagnostics)
        self.assertIn("BranchCount=2", diagnostics)
        self.assertIn("UniqueTopics=4", diagnostics)
        self.assertEqual(game.companion_diagnostics["topic_jump_count"], 1)

    def test_topic_branch_log_is_limited_to_twenty_transitions(self):
        game = self.make_game()
        game.debug_llm = True
        game.companion_diagnostics["topic_branches"] = [
            ("起点", f"派生{index}") for index in range(25)
        ]

        with redirect_stdout(io.StringIO()) as output:
            game.print_conversation_stats()

        branch_section = output.getvalue().split("[TOPIC_BRANCH]\n", 1)[1].split(
            "[NICO_DIAGNOSTICS]", 1
        )[0]
        self.assertEqual(branch_section.count("起点 -> 派生"), 20)

    def test_recent_banter_is_single_turn_labeled_and_separate_from_current_event(self):
        game = self.make_game()
        state = State("cliff_path")
        old_intent = {"raw": "ランタンを見る", "action_type": "inspect", "target_id": "broken_lantern"}
        game.remember_companion_turn(
            [
                "ニコ: 一つ目。",
                "クロ: 二つ目。",
                "ピピ: 三つ目。",
                "ニコ: 四つ目。",
                "クロ: 五つ目。",
            ],
            old_intent,
            state,
        )
        # A stale fallback cache must not be merged back into the latest turn.
        game.last_banter = {"output": "ニコ: 古い別ターン。"}

        current_intent = {"raw": "足跡を見る", "action_type": "inspect", "target_id": "cliff_footprints"}
        packet = game.packet(current_intent, [], state)
        history = packet["recent_companion_lines"]

        # packet は speech_profiles / conversation_goal などの新キーを増やし得るため、
        # 完全一致ではなく必須キーの包含で検証する（増分で壊さない）。
        assert_packet_contains(
            self,
            packet,
            {"conversation_diagnostics", "current_event", "current_observations", "recent_companion_lines", "safety"},
        )
        self.assertEqual(packet["current_event"]["target_id"], "cliff_footprints")
        self.assertEqual(history["label"], "reference_only_past_turn")
        self.assertEqual(history["previous_scene"]["target"], "broken_lantern")
        # A new inspect target retains the previous scene metadata for
        # diagnostics, but does not expose its wording to the model.
        self.assertEqual(history["lines"], [])
        self.assertNotIn("ニコ: 一つ目。", history["lines"])
        self.assertNotIn("ニコ: 古い別ターン。", history["lines"])
        self.assertNotIn("クロ: 二つ目。", packet["current_observations"])
        self.assertIn("コピーや言い換え再出力は禁止", history["usage"])
        # safety 文言は刷新されたため、同義の情報境界（会話履歴＝世界設定ではない／
        # 未発見情報を確定事実にしない）を現行の表現で検証する。
        safety_text = "".join(packet["safety"])
        self.assertIn("世界設定ではない", safety_text)
        self.assertIn("未発見情報や正解を確定事実として扱わない", safety_text)

        game.remember_companion_turn([], current_intent, state)
        self.assertEqual(game.recent_companion_lines(), [])

    def test_location_change_keeps_history_metadata_but_omits_previous_lines(self):
        game = self.make_game()
        state = State("harbor")
        old_intent = {"raw": "村長の話を聞く", "action_type": "ask", "target_id": "village_head"}
        game.remember_companion_turn(["クロ: 倉庫なら隠れやすいな。"], old_intent, state)

        state.location = "warehouse"
        packet = game.packet(
            {"raw": "倉庫へ移動する", "action_type": "move", "target_id": "warehouse"},
            [],
            state,
        )
        history = packet["recent_companion_lines"]

        self.assertEqual(history["previous_scene"]["location"], "港")
        self.assertEqual(history["lines"], [])
        self.assertIn("場所が変わったため", history["usage"])

    def test_same_location_and_target_retains_reference_history(self):
        game = self.make_game()
        state = State("warehouse")
        intent = {"raw": "航路図を見る", "action_type": "inspect", "target_id": "old_chart"}
        game.remember_companion_turn(["ニコ: 丸があるね。"], intent, state)

        history = game.packet(intent, [], state)["recent_companion_lines"]

        self.assertEqual(history["lines"], ["ニコ: 丸があるね。"])
        self.assertIn("コピーや言い換え再出力は禁止", history["usage"])

    def test_blocked_chart_canonical_is_neutral_before_table_rendering(self):
        game = self.make_game()
        state = State("warehouse")
        chart_discovery = game.disc["smuggler_route_analysis"]
        intent = {"raw": "航路図を解析する", "action_type": "skill_check", "target_id": "old_chart"}

        canonical = game.gm_comment_for_blocked_discoverable(
            chart_discovery,
            intent,
            state,
            missing_all=["tide_log_cave_time", "crate_blue_mark"],
        )

        self.assertEqual(
            canonical,
            "GM: 古い航路図を確認した。今の確認では、それ以上のことは分からない。",
        )

    def test_direct_companion_request_uses_consult_handoff_without_preempting_response(self):
        for raw, name in (("ピピ、怖い話をして", "ピピ"), ("ニコ、踊って", "ニコ")):
            with self.subTest(raw=raw):
                game = self.make_game()
                state = State("harbor")
                game.embedded_action_intent = lambda text, allowed=None: ("consult", "test")

                intent = game.judge(raw, state)
                notes, result, events = game.resolve(intent, state)

                # 指名した仲間が対象になり、仲間会話ファミリとして処理されること。
                # 綴り（command/conversation/consult 等）は Embedding 依存でゆれる。
                assert_companion_directed(self, intent, "companion:" + name)
                # 仲間への振りが、到達していないシナリオ手掛かりを先回りで
                # 開示（preempt）していないこと。
                assert_no_scenario_reveal(self, events)

    def test_continuation_context_exposes_same_scene_line_and_requested_responder(self):
        game = self.make_game()
        state = State("harbor")
        game.remember_companion_turn(
            ["ニコ: 霧の中に巨大なイカがいるかも。"],
            {"raw": "ニコ変なこと言って", "action_type": "consult", "target_id": "companion:ニコ"},
            state,
        )

        packet = game.packet(
            {"raw": "クロ反応して", "action_type": "consult", "target_id": "companion:クロ"},
            [],
            state,
        )

        self.assertEqual(packet["requested_companions"], ["クロ"])
        self.assertEqual(packet["conversation_context"]["mode"], "continue")
        self.assertEqual(
            packet["conversation_context"]["previous_companion_lines"],
            ["ニコ: 霧の中に巨大なイカがいるかも。"],
        )

    def test_continuation_context_respects_location_history_boundary(self):
        game = self.make_game()
        state = State("harbor")
        game.remember_companion_turn(
            ["ニコ: 港の霧って変だね。"],
            {"action_type": "consult", "target_id": "companion:ニコ"},
            state,
        )
        state.location = "warehouse"

        packet = game.packet(
            {"raw": "クロも混ざって", "action_type": "consult", "target_id": "companion:クロ"},
            [],
            state,
        )

        self.assertNotIn("conversation_context", packet)
        self.assertEqual(packet["recent_companion_lines"]["lines"], [])
        self.assertEqual(game.recent_companion_lines(), ["ニコ: 港の霧って変だね。"])

    def test_location_change_resets_only_continuation_mode(self):
        game = self.make_game()
        game.debug_llm = True
        state = State("harbor")
        old_lines = ["ニコ: 巨大イカから沈没船を思い出した。"]
        game.remember_companion_turn(
            old_lines,
            {"raw": "全員で雑談して", "action_type": "consult"},
            state,
        )
        continued = game.packet(
            {"raw": "全員でその話を続けて", "action_type": "consult"}, [], state
        )
        self.assertIn("conversation_context", continued)
        self.assertEqual(game.conversation_continue_count, 1)

        state.location = "warehouse"
        with redirect_stdout(io.StringIO()) as output:
            moved = game.packet(
                {"raw": "倉庫へ移動する", "action_type": "move", "target_id": "warehouse"},
                [],
                state,
            )

        self.assertNotIn("conversation_context", moved)
        self.assertEqual(game.conversation_continue_count, 0)
        self.assertEqual(game.companion_diagnostics["continue_reset_count"], 1)
        self.assertEqual(game.recent_companion_lines(), old_lines)
        self.assertIn("[CONVERSATION_RESET]", output.getvalue())
        self.assertIn("Reason=LocationChanged", output.getvalue())
        self.assertIn("From=harbor", output.getvalue())
        self.assertIn("To=warehouse", output.getvalue())

    def test_sixth_continue_request_expires_without_clearing_history(self):
        game = self.make_game()
        game.debug_llm = True
        state = State("harbor")
        old_lines = [
            "ニコ: 海王の影と海の意志を思い出した。",
            "クロ: 忘却都市なら俺も知っているぞ。",
        ]
        game.remember_companion_turn(
            old_lines,
            {"raw": "全員で雑談して", "action_type": "consult"},
            state,
        )
        intent = {"raw": "全員でその話を続けて", "action_type": "consult"}

        packets = []
        with redirect_stdout(io.StringIO()) as output:
            for _ in range(6):
                packets.append(game.packet(intent, [], state))
            game.print_conversation_stats()

        self.assertTrue(all("conversation_context" in packet for packet in packets[:5]))
        self.assertNotIn("conversation_context", packets[5])
        self.assertEqual(game.conversation_continue_count, 0)
        self.assertEqual(game.recent_companion_lines(), old_lines)
        self.assertEqual(game.companion_diagnostics["continue_expire_count"], 1)
        self.assertIn("Reason=ContinueExpired", output.getvalue())
        self.assertIn("Turns=5", output.getvalue())
        last_topics = next(
            line for line in output.getvalue().splitlines() if line.startswith("LastTopics=")
        )
        self.assertIn("海王", last_topics)
        self.assertIn("意志", last_topics)
        self.assertIn("忘却都市", last_topics)
        self.assertIn("ContinueResetCount=0", output.getvalue())
        self.assertIn("ContinueExpireCount=1", output.getvalue())
        self.assertIn("ContinueWindow=5", output.getvalue())
        self.assertIn("ConversationResets=1", output.getvalue())

    def test_named_and_group_requests_are_structured_as_participant_preferences(self):
        game = self.make_game()
        state = State("harbor")

        named = game.packet(
            {"raw": "ニコとピピで話して", "action_type": "consult", "target_id": "companion:ニコ"},
            [],
            state,
        )
        game.embedded_action_intent = lambda text, allowed=None: ("consult", "test")
        everyone_intent = game.judge("全員で雑談して", state)
        everyone = game.packet(everyone_intent, [], state)

        self.assertEqual(named["requested_companions"], ["ニコ", "ピピ"])
        self.assertNotIn("conversation_context", named)
        # 「全員で〜」は全員が participants になることが要点。action_type の綴りは
        # 環境依存（banter_action/conversation 等）なのでファミリ包含で検証する。
        assert_companion_directed(self, everyone_intent, "companion:全員")
        self.assertEqual(
            everyone["requested_companions"],
            ["ニコ", "ピピ", "クロ", "ガラン"],
        )

    def test_table_renderer_reads_history_then_saves_current_response_once(self):
        game = self.make_game()
        state = State("light_room")
        old_intent = {"raw": "レンズを見る", "action_type": "inspect", "target_id": "lighthouse_lens"}
        game.remember_companion_turn(["ニコ: 古いレンズの台詞。"], old_intent, state)
        captured = []

        def fake_post_json(url, body, timeout, tag):
            captured.append(json.loads(body["messages"][1]["content"]))
            self.assertEqual(game.last_companion_turn["context"]["target"], "lighthouse_lens")
            return {"choices": [{"message": {"content": "GM: 弁を調べた。\nクロ: 少し休もうぜ。"}}]}

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
        self.assertEqual(game.recent_companion_lines(), ["クロ: 少し休もうぜ。"])

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


    def test_integrated_official_discovery_is_not_inserted_twice(self):
        game = self.make_game()
        state = State("harbor")
        public_text = game.disc["head_report"]["public_text"]
        captured = []

        def fake_post_json(url, body, timeout, tag):
            captured.append(json.loads(body["messages"][1]["content"]))
            return {
                "choices": [
                    {
                        "message": {
                            "content": "GM: 村長は、灯が消える直前に倉庫で人影を見たと重く語る。"
                        }
                    }
                ]
            }

        game.post_json = fake_post_json
        with patch.dict(os.environ, {"LLM_PROVIDER": "llama_cpp", "DISCOVERY_DISPLAY": "gm"}):
            rendered, _ = game.render_table_turn(
                ["GM: 村長に話を聞いた。", "発見: " + public_text],
                {"raw": "村長に聞く", "action_type": "ask", "target_id": "village_head"},
                {"status": "ok", "category": "discoverable"},
                [{"type": "discoverable_revealed", "id": "head_report"}], state,
            )

        self.assertEqual(captured[0]["discovery_log_lines_for_context"], ["発見: " + public_text])
        self.assertEqual(
            rendered,
            ["GM: 村長は、灯が消える直前に倉庫で人影を見たと重く語る。"],
        )
        self.assertEqual(game.last_table_turn["official_gm_lines"], ["GM: " + public_text])
        self.assertEqual(game.last_table_turn["official_gm_lines_inserted"], [])

    def test_missing_official_discovery_is_still_inserted_after_rewrite(self):
        game = self.make_game()
        state = State("harbor")
        public_text = game.disc["head_report"]["public_text"]
        game.post_json = lambda url, body, timeout, tag: {
            "choices": [{"message": {"content": "GM: 村長は少し考えてから口を開いた。"}}]
        }

        with patch.dict(os.environ, {"LLM_PROVIDER": "llama_cpp", "DISCOVERY_DISPLAY": "gm"}):
            rendered, _ = game.render_table_turn(
                ["GM: 村長に話を聞いた。", "発見: " + public_text],
                {"raw": "村長に聞く", "action_type": "ask", "target_id": "village_head"},
                {"status": "ok", "category": "discoverable"},
                [{"type": "discoverable_revealed", "id": "head_report"}], state,
            )

        official_line = "GM: " + public_text
        self.assertEqual(rendered, ["GM: 村長は少し考えてから口を開いた。", official_line])
        self.assertEqual(game.last_table_turn["official_gm_lines_inserted"], [official_line])

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
        self.assertIn("正式発見は後続のGM行で原文表示", prompt)
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

    def test_companion_history_can_retain_one_line_for_each_archetype(self):
        game = self.make_game()
        state = State("harbor")
        lines = [f"{name}: 一言。" for name in game.companion_names()]

        game.remember_companion_turn(
            lines,
            {"raw": "全員で話して", "action_type": "consult", "target_id": "companion:全員"},
            state,
        )

        self.assertEqual(game.recent_companion_lines(), lines)

    def test_new_companions_are_recognized_in_history_and_rendered_output(self):
        game = self.make_game()
        state = State("harbor")
        intent = {"raw": "クロとガランで話して", "action_type": "consult", "target_id": "companion:クロ"}
        game.remember_companion_turn(
            ["クロ: 昨日見たぞ。", "ガラン: 捕まえよう。"],
            intent,
            state,
        )

        self.assertEqual(
            game.recent_companion_lines(),
            ["クロ: 昨日見たぞ。", "ガラン: 捕まえよう。"],
        )
        self.assertEqual(game.requested_companions(intent["raw"]), ["クロ", "ガラン"])

        game.post_json = lambda url, body, timeout, tag: {
            "choices": [{"message": {"content": "GM: 二人に話を振る。\nクロ: 俺は見たぞ。\nガラン: なら捕まえよう。"}}]
        }
        with patch.dict(os.environ, {"LLM_PROVIDER": "llama_cpp"}):
            rendered, _ = game.render_table_turn(
                ["GM: 二人に話を振る。"],
                intent,
                {"status": "ok", "category": "consult"},
                [],
                state,
            )

        self.assertEqual(
            rendered,
            ["GM: 二人に話を振る。", "クロ: 俺は見たぞ。", "ガラン: なら捕まえよう。"],
        )
        self.assertEqual(game.recent_companion_lines(), ["クロ: 俺は見たぞ。", "ガラン: なら捕まえよう。"])

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
