"""Regression observations for the lighthouse NPC ask-routing investigation.

These tests intentionally lock down the current behavior without changing the
engine, scenario vocabulary, embedding thresholds, or prompts.  They document
the distinction between authored topic-map routing and the lexical fallback.
"""

import os
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from fixed_truth_ai_gm_mvp import Game, State


ROOT = Path(__file__).resolve().parent.parent
SCENARIO_DIR = ROOT / "web" / "public" / "scenarios" / "lighthouse"


class LighthouseNpcAskRoutingInvestigationTests(unittest.TestCase):
    def setUp(self):
        self.embedding_disabled = patch.dict(
            os.environ,
            {"EMBEDDING_PROVIDER": "none", "LLM_PROVIDER": "none"},
        )
        self.embedding_disabled.start()
        self.game = Game(SCENARIO_DIR, runtime_settings={"chat_provider": "none"})

    def tearDown(self):
        self.embedding_disabled.stop()

    def resolve_fresh(self, raw):
        state = State(self.game.sc["opening_scene"])
        self.game.last_embedding = {}
        intent = self.game.judge(raw, state)
        notes, result, events = self.game.resolve(intent, state)
        return intent, notes, result, events, dict(self.game.last_embedding)

    def test_topic_text_extraction_for_natural_village_head_questions(self):
        expected_topics = {
            "村長に話を聞く": "話",
            "村長にユアンのことを聞く": "ユアン",
            "村長にユアンについて聞く": "ユアン",
            "村長に灯台守について聞く": "灯台守",
            "村長に昨夜のことを聞く": "昨夜",
            "村長に行方不明者について聞く": "行方不明者",
            "村長に青い光について聞く": "青い光",
            "村長に灯台について聞く": "灯台",
        }

        for raw, topic in expected_topics.items():
            with self.subTest(raw=raw):
                intent = self.game.judge(raw, State(self.game.sc["opening_scene"]))
                self.assertEqual("village_head", intent["target_id"])
                self.assertEqual(topic, intent["topic_text"])

    def test_topic_text_normalizes_intervening_about_talk_phrase(self):
        for raw, expected in (
            ("村長に青い光について聞く", "青い光"),
            ("村長に青い光のことを聞く", "青い光"),
            ("村長に青い光について話を聞く", "青い光"),
            ("村長にユアンについて話を聞く", "ユアン"),
        ):
            with self.subTest(raw=raw):
                intent = self.game.judge(raw, State(self.game.sc["opening_scene"]))
                self.assertEqual(expected, intent["topic_text"])

    def test_keeper_role_and_public_names_reveal_head_report_without_embeddings(self):
        for raw in (
            "村長に灯台守のことを聞く",
            "村長にユアンのことを聞く",
            "村長に灯台守ユアンについて聞く",
            "村長に灯台について聞く",
        ):
            with self.subTest(raw=raw):
                intent, notes, result, events, judged = self.resolve_fresh(raw)
                self.assertEqual("ask", intent["action_type"])
                self.assertEqual("village_head", intent["target_id"])
                self.assertEqual({}, judged)
                self.assertEqual("ok", result["status"])
                self.assertEqual("discoverable", result["category"])
                self.assertEqual("ask_topic", result["resolver"])
                self.assertEqual([{"type": "discoverable_revealed", "id": "head_report"}], events)
                self.assertIn("発見:", "\n".join(notes))

    def test_authored_lighthouse_keeper_topic_bypasses_similarity_judge(self):
        _intent, notes, result, events, judged = self.resolve_fresh(
            "村長に灯台守について聞く"
        )

        self.assertEqual({}, judged)
        self.assertEqual({"status": "ok", "category": "discoverable", "resolver": "ask_topic"}, result)
        self.assertEqual([{"type": "discoverable_revealed", "id": "head_report"}], events)
        self.assertIn("発見:", "\n".join(notes))

    def test_blue_light_is_an_authored_topic_unknown_to_village_head(self):
        _intent, notes, result, events, judged = self.resolve_fresh(
            "村長に青い光について聞く"
        )

        self.assertEqual({}, judged)
        self.assertEqual("ok", result["status"])
        self.assertEqual("no_reveal", result["category"])
        self.assertEqual("npc_topic_unknown", result["reason"])
        self.assertEqual([], events)
        self.assertIn("詳しいことを知らない", "\n".join(notes))

    def test_unmatched_candidate_has_distinct_internal_reason(self):
        _intent, _notes, result, events, judged = self.resolve_fresh("村長に話を聞く")
        self.assertEqual("candidate_below_threshold", judged["reason"])
        self.assertEqual("candidate_below_threshold", result["reason"])
        self.assertEqual([], events)

    def test_authored_topic_does_not_bypass_npc_presence(self):
        _intent, notes, result, events, judged = self.resolve_fresh(
            "漁師バロに青い光について聞く"
        )

        self.assertEqual({}, judged)
        self.assertEqual("fail", result["status"])
        self.assertEqual("npc_absent", result["category"])
        self.assertEqual("npc_absent", result["reason"])
        self.assertEqual([], events)
        self.assertIn("港にはいない", "\n".join(notes))

    def test_present_fisherman_reveals_blue_light(self):
        state = State("tavern")
        intent = self.game.judge("漁師バロに青い光について聞く", state)
        notes, result, events = self.game.resolve(intent, state)

        self.assertEqual("ok", result["status"])
        self.assertEqual("discoverable", result["category"])
        self.assertEqual([{"type": "discoverable_revealed", "id": "fisherman_blue_light"}], events)
        self.assertIn("発見:", "\n".join(notes))

    def test_embedding_provider_none_reports_lexical_fallback_reason(self):
        self.game.debug_embedding = True
        output = StringIO()
        with redirect_stdout(output):
            self.assertIsNone(self.game.get_embeddings(["query", "candidate"]))

        self.assertIn("[EMB_FALLBACK]", output.getvalue())
        self.assertIn("reason=provider_none", output.getvalue())
        self.assertIn("mode=lexical", output.getvalue())

    def test_embedding_request_failure_records_session_fallback_reason(self):
        game = Game(SCENARIO_DIR, debug_embedding=True, runtime_settings={"chat_provider": "none"})
        output = StringIO()
        with patch.dict(os.environ, {"EMBEDDING_PROVIDER": "local"}), patch.object(
            game, "post_json", side_effect=RuntimeError("HTTP 400 provider payload omitted")
        ), redirect_stdout(output):
            self.assertIsNone(game.get_embeddings(["query", "candidate"]))

        self.assertTrue(game.emb_disabled)
        self.assertEqual("http_4xx", game.emb_disabled_reason)
        self.assertIn("reason=http_4xx", output.getvalue())
        self.assertIn("session_disabled=true", output.getvalue())


if __name__ == "__main__":
    unittest.main()
