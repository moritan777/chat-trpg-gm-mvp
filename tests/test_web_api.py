import os
import unittest
from pathlib import Path

os.environ["LLM_PROVIDER"] = "none"
os.environ["EMBEDDING_PROVIDER"] = "none"

try:
    from fastapi.testclient import TestClient
    from web_api import app
except ImportError:
    TestClient = None
    app = None


@unittest.skipUnless(TestClient is not None, "requirements-web.txt is not installed")
class WebApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def create_session(self):
        response = self.client.post("/api/sessions", json={"scenario_id": "lighthouse"})
        self.assertEqual(201, response.status_code)
        return response.json()

    def test_health_and_scenario_list(self):
        health = self.client.get("/api/health")
        self.assertEqual(200, health.status_code)
        self.assertEqual("ok", health.json()["status"])
        scenarios = self.client.get("/api/scenarios").json()["scenarios"]
        self.assertIn("lighthouse", {item["id"] for item in scenarios})

    def test_creation_opening_command_and_location(self):
        created = self.create_session()
        self.assertTrue(created["opening"])
        self.assertEqual("harbor", created["current_location"]["id"])
        session_id = created["session_id"]
        current = self.client.get(f"/api/sessions/{session_id}")
        self.assertEqual("harbor", current.json()["current_location"]["id"])
        turn = self.client.post(
            f"/api/sessions/{session_id}/commands", json={"text": "酒場へ行く"}
        )
        self.assertEqual(200, turn.status_code)
        self.assertEqual("tavern", turn.json()["current_location"]["id"])
        self.assertTrue(turn.json()["lines"])

    def test_empty_unknown_delete_and_deleted_command(self):
        unknown = "00000000-0000-0000-0000-000000000000"
        self.assertEqual(404, self.client.get(f"/api/sessions/{unknown}").status_code)
        created = self.create_session()
        path = f"/api/sessions/{created['session_id']}"
        self.assertEqual(400, self.client.post(path + "/commands", json={"text": " "}).status_code)
        self.assertEqual(204, self.client.delete(path).status_code)
        self.assertEqual(404, self.client.post(path + "/commands", json={"text": "status"}).status_code)

    def test_finished_session_rejects_more_commands(self):
        created = self.create_session()
        path = f"/api/sessions/{created['session_id']}/commands"
        self.assertTrue(self.client.post(path, json={"text": "quit"}).json()["finished"])
        self.assertEqual(409, self.client.post(path, json={"text": "status"}).status_code)

    def test_sessions_are_isolated_and_responses_are_public_only(self):
        first, second = self.create_session(), self.create_session()
        self.client.post(f"/api/sessions/{first['session_id']}/commands", json={"text": "酒場へ行く"})
        second_state = self.client.get(f"/api/sessions/{second['session_id']}").json()
        self.assertEqual("harbor", second_state["current_location"]["id"])
        allowed = {"session_id", "opening", "current_location", "finished"}
        self.assertLessEqual(set(first), allowed)
        serialized = str(first).lower()
        for forbidden in ("discovered", "discoverables", "api_key", "environment", "llama_cpp_base_url"):
            self.assertNotIn(forbidden, serialized)

    def test_static_ui(self):
        index = self.client.get("/")
        self.assertEqual(200, index.status_code)
        self.assertIn("Chat TTRPG GM", index.text)
        script = self.client.get("/static/app.js")
        style = self.client.get("/static/style.css")
        self.assertEqual(200, script.status_code)
        self.assertEqual(200, style.status_code)
        self.assertNotIn("innerHTML", script.text)
        self.assertIn("textContent", script.text)
        self.assertNotIn("LLAMA_CPP_BASE_URL", script.text)


if __name__ == "__main__":
    unittest.main()
