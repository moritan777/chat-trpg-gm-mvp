import json
import re
import unittest
from pathlib import Path


class OpeningGeographyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        text = Path("author_scenario_lighthouse_v2150.md").read_text(encoding="utf-8")
        match = re.search(r"```scenario-json\s*(.*?)\s*```", text, re.S)
        if not match:
            raise AssertionError("scenario-json block not found")
        cls.scenario = json.loads(match.group(1))

    def test_opening_explains_main_location_connections_once(self):
        opening = self.scenario["opening"]
        opening_text = "\n".join(opening)

        self.assertEqual(opening_text.count("この村の主な場所は次のようになっています"), 1)
        self.assertIn(
            "港\n├ 酒場\n├ 倉庫\n└ 岬の道\n      ├ 灯台\n      └ 岩場の海岸\n             └ 海蝕洞（干潮時のみ）",
            opening_text,
        )
        self.assertIn("調査を進める中で、新しい場所や情報が見つかるかもしれません", opening_text)

    def test_opening_map_matches_authored_exits(self):
        locations = {location["id"]: location for location in self.scenario["locations"]}

        self.assertEqual(self.scenario["opening_scene"], "harbor")
        self.assertTrue({"tavern", "warehouse", "cliff_path"} <= set(locations["harbor"]["exits"]))
        self.assertTrue(
            {"lighthouse_entrance", "rocky_shore"} <= set(locations["cliff_path"]["exits"])
        )
        self.assertIn("sea_cave", locations["rocky_shore"]["exits"])

    def test_opening_geography_contains_no_route_recommendation(self):
        opening_text = "\n".join(self.scenario["opening"])

        for forbidden in ("重要な手掛かりがある", "倉庫を先に", "灯台が正解ルート"):
            self.assertNotIn(forbidden, opening_text)

    def test_opening_invites_free_actions(self):
        opening_text = "\n".join(self.scenario["opening"])

        for phrase in ("自由な行動", "崖を登る", "足跡を追う", "隠れて様子を見る", "説得する", "技能判定"):
            self.assertIn(phrase, opening_text)

    def test_locations_offer_free_action_hooks(self):
        locations = {location["id"]: location for location in self.scenario["locations"]}

        self.assertIn("登れそう", locations["cliff_path"]["intro"])
        self.assertIn("足跡", locations["cliff_path"]["intro"])
        self.assertIn("足跡", locations["rocky_shore"]["intro"])
        self.assertIn("物陰", locations["warehouse"]["intro"])
        self.assertIn("表情", locations["tavern"]["intro"])


    def test_lighthouse_entrance_foreshadows_assistant_key_question(self):
        locations = {location["id"]: location for location in self.scenario["locations"]}
        npcs = {npc["id"]: npc for npc in self.scenario["npcs"]}
        entrance = locations["lighthouse_entrance"]
        assistant = npcs["assistant"]

        entrance_text = "\n".join(
            entrance.get(field, "")
            for field in ("intro", "banter_observation", "surface_banter_observation")
        )
        assistant_text = "\n".join(
            assistant.get(field, "")
            for field in ("banter_observation", "surface_banter_observation")
        )

        self.assertIn("半開き", entrance_text)
        self.assertTrue("錠前" in entrance_text or "扉" in entrance_text)
        self.assertTrue(any(term in entrance_text for term in ("壊された形跡はなく", "壊れていない", "破壊痕")))
        self.assertIn("鍵", entrance_text)
        self.assertIn("鍵束", assistant_text)
        self.assertIn("気にする", assistant_text)
        self.assertNotIn("倉庫番", entrance_text + assistant_text)
        self.assertNotIn("予備鍵を貸した", entrance_text + assistant_text)

    def test_lighthouse_action_checks_have_partial_success_space(self):
        checks = {check["id"]: check for check in self.scenario["action_checks"]}

        self.assertIn("on_partial_success", checks["climb_cliff"])
        self.assertIn("中腹", checks["climb_cliff"]["on_partial_success"]["text"])
        self.assertIn("track_cliff_footprints", checks)
        self.assertIn("海岸側", checks["track_cliff_footprints"]["on_partial_success"]["text"])


if __name__ == "__main__":
    unittest.main()
