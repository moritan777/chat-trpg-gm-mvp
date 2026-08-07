import ast
import unittest
from collections import Counter
from pathlib import Path


class GameStructureTests(unittest.TestCase):
    def test_game_class_has_no_duplicate_methods(self):
        source = Path("fixed_truth_ai_gm_mvp.py").read_text(encoding="utf-8")
        module = ast.parse(source)
        game_class = next(
            node
            for node in module.body
            if isinstance(node, ast.ClassDef) and node.name == "Game"
        )
        method_counts = Counter(
            node.name
            for node in game_class.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        )

        duplicates = {
            name: count for name, count in method_counts.items() if count > 1
        }
        self.assertEqual({}, duplicates)
        for required in ("judge", "resolve", "packet", "render_table_turn", "companion_banter_prompt"):
            self.assertIn(required, method_counts)


if __name__ == "__main__":
    unittest.main()
