import json
import os
import re
import tempfile
import unittest
from pathlib import Path

from fixed_truth_ai_gm_mvp import Game, State


class ObjectLocationScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        author_text = Path("author_scenario_lighthouse_v2150.md").read_text(encoding="utf-8")
        match = re.search(r"```scenario-json\s*(.*?)\s*```", author_text, re.S)
        if not match:
            raise AssertionError("scenario-json block not found")
        scenario = json.loads(match.group(1))
        scenario.pop("tests", None)
        cls.temp_dir = tempfile.TemporaryDirectory()
        Path(cls.temp_dir.name, "scenario.json").write_text(
            json.dumps(scenario, ensure_ascii=False), encoding="utf-8"
        )
        cls.old_llm_provider = os.environ.get("LLM_PROVIDER")
        cls.old_embedding_provider = os.environ.get("EMBEDDING_PROVIDER")
        os.environ["LLM_PROVIDER"] = "none"
        os.environ["EMBEDDING_PROVIDER"] = "none"

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()
        for key, value in (
            ("LLM_PROVIDER", cls.old_llm_provider),
            ("EMBEDDING_PROVIDER", cls.old_embedding_provider),
        ):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def make_game(self):
        return Game(self.temp_dir.name)

    def resolve_text(self, game, state, raw):
        intent = game.judge(raw, state)
        notes, result, events = game.resolve(intent, state)
        return intent, "\n".join(str(note) for note in notes), result, events

    def test_remote_object_is_not_selected_or_revealed(self):
        game = self.make_game()
        state = State("harbor")

        intent, text, result, events = self.resolve_text(game, state, "濡れたロープを調べる")

        self.assertNotEqual(intent["target_id"], "rope_marks")
        self.assertNotIn("rope_to_shore", state.discovered)
        self.assertNotIn("灯台入口の手すり", text)
        self.assertEqual(events, [])
        self.assertIn(result["category"], {"surface_inspect", "no_reveal", "object_not_present"})

    def test_resolve_defensively_rejects_remote_object(self):
        game = self.make_game()
        state = State("harbor")
        before = set(state.discovered)

        notes, result, events = game.resolve(
            {"raw": "ロープ跡を調べる", "action_type": "inspect", "target_id": "rope_marks"}, state
        )

        self.assertEqual(result["category"], "object_not_present")
        self.assertEqual(state.discovered, before)
        self.assertEqual(events, [])
        self.assertNotIn("灯台入口", "\n".join(notes))

    def test_objects_can_be_inspected_at_their_location(self):
        game = self.make_game()
        state = State("lighthouse_entrance")

        blood_intent, _, _, _ = self.resolve_text(game, state, "赤黒い染みを調べる")
        rope_intent, _, _, _ = self.resolve_text(game, state, "ロープ跡を調べる")

        self.assertEqual(blood_intent["target_id"], "blood_stain")
        self.assertEqual(rope_intent["target_id"], "rope_marks")
        self.assertIn("blood_drag_clue", state.discovered)
        self.assertIn("rope_to_shore", state.discovered)

    def test_current_location_object_still_reveals_discoverable(self):
        game = self.make_game()
        state = State("harbor")

        intent, _, _, _ = self.resolve_text(game, state, "潮汐表を見る")

        self.assertEqual(intent["target_id"], "tide_log")
        self.assertIn("tide_log_cave_time", state.discovered)

    def test_absent_npc_location_hint_is_preserved(self):
        game = self.make_game()
        state = State("harbor")

        intent, text, result, events = self.resolve_text(game, state, "漁師と話をする")

        self.assertEqual(intent["target_id"], "fisherman")
        self.assertEqual(result["category"], "npc_absent")
        self.assertIn("酒場にいるはず", text)
        self.assertEqual(events, [])

    def test_area_search_lists_only_current_area_entities(self):
        game = self.make_game()
        state = State("cliff_path")

        intent, text, result, _ = self.resolve_text(game, state, "崖道を調べる")

        self.assertEqual(intent["action_type"], "area_search")
        self.assertEqual(result["category"], "area_search")
        self.assertIn("割れたランタン", text)
        self.assertIn("崖道の足跡", text)

    def test_duplicate_alias_is_resolved_within_location(self):
        game = self.make_game()
        for location, expected in (("warehouse", "marked_crate"), ("sea_cave", "cave_crates")):
            with self.subTest(location=location):
                state = State(location)
                intent = game.judge("荷箱を見る", state)
                self.assertEqual(intent["target_id"], expected)



    def test_duplicate_alias_never_stops_at_invisible_first_candidate(self):
        game = self.make_game()
        state = State("sea_cave")
        intent = game.judge("荷箱を見る", state)
        self.assertNotEqual("marked_crate", intent["target_id"])
        self.assertEqual("cave_crates", intent["target_id"])
        _notes, result, _events = game.resolve(intent, state)
        self.assertNotEqual("object_not_present", result["category"])

if __name__ == "__main__":
    unittest.main()
