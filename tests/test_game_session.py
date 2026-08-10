import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from fixed_truth_ai_gm_mvp import GameSession


class GameSessionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        scenario = {
            "title": "session test",
            "opening_scene": "harbor",
            "opening": ["GM: opening"],
            "player": {"skills": {}},
            "locations": [
                {"id": "harbor", "name": "港", "intro": "港。", "exits": ["tavern"]},
                {"id": "tavern", "name": "酒場", "intro": "酒場。", "exits": ["harbor"]},
            ],
            "objects": [], "npcs": [], "discoverables": [], "goals": [],
        }
        Path(self.temp_dir.name, "scenario.json").write_text(
            json.dumps(scenario, ensure_ascii=False), encoding="utf-8"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_start_and_process_use_canonical_game(self):
        session = GameSession(self.temp_dir.name)
        self.assertEqual(["GM: opening"], session.start()["opening"])
        turn = session.process_command("酒場へ行く")
        self.assertEqual("tavern", turn["current_location"]["id"])
        self.assertTrue(any("酒場" in line for line in turn["lines"]))

    def test_sessions_have_independent_state(self):
        first = GameSession(self.temp_dir.name)
        second = GameSession(self.temp_dir.name)
        first.process_command("酒場へ行く")
        self.assertEqual("harbor", second.get_public_state()["current_location"]["id"])

    def test_empty_and_finished_commands_are_rejected(self):
        session = GameSession(self.temp_dir.name)
        with self.assertRaises(ValueError):
            session.process_command("  ")
        session.close()
        with self.assertRaises(RuntimeError):
            session.process_command("status")

    def test_debug_is_separate_from_display_lines(self):
        session = GameSession(self.temp_dir.name, debug_judge=True)
        turn = session.process_command("酒場へ行く")
        self.assertTrue(turn["debug"])
        self.assertFalse(any(line.startswith("[") for line in turn["lines"]))

    def test_echo_debug_prints_captured_diagnostics(self):
        session = GameSession(self.temp_dir.name, debug_judge=True, echo_debug=True)
        output = StringIO()
        with redirect_stdout(output):
            turn = session.process_command("酒場へ行く")
        self.assertTrue(turn["debug"])
        self.assertIn(turn["debug"][0], output.getvalue())


if __name__ == "__main__":
    unittest.main()
