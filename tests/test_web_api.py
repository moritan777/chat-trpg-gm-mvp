import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ["LLM_PROVIDER"] = "none"
os.environ["EMBEDDING_PROVIDER"] = "none"

try:
    from fastapi.testclient import TestClient
    import web_api
    from chat_trpg_web.settings import SettingsService
    app = web_api.app
except ImportError:
    TestClient = None
    app = None


@unittest.skipUnless(TestClient is not None, "requirements-web.txt is not installed")
class WebApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        service = SettingsService(Path(self.temp.name) / "settings.json", environ={}, scenario_provider=web_api.catalog.list_public)
        web_api.settings_service = service
        web_api.manager.settings_service = service

    def tearDown(self):
        self.temp.cleanup()

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
        for forbidden in ("localStorage", "sessionStorage", "innerHTML", "console."):
            self.assertNotIn(forbidden, script.text)

    def test_settings_get_put_clear_reset_and_validation(self):
        initial = self.client.get("/api/settings")
        self.assertEqual(200, initial.status_code)
        payload = {
            "selected_scenario": "lighthouse",
            "chat": {"provider": "llama_cpp", "base_url": "http://localhost:8080/v1/", "model": "chat", "api_key": "CHAT-SECRET"},
            "embedding": {"base_url": "http://localhost:8081/v1", "model": "embed", "api_key": "EMB-SECRET"},
        }
        saved = self.client.put("/api/settings", json=payload)
        self.assertEqual(200, saved.status_code)
        self.assertNotIn("SECRET", saved.text)
        self.assertNotIn("SECRET", Path(saved.json()["settings_path"]).read_text(encoding="utf-8"))
        self.assertTrue(saved.json()["api_keys"]["chat"]["configured"])
        cleared = self.client.post("/api/settings/secrets/clear")
        self.assertFalse(cleared.json()["api_keys"]["chat"]["configured"])
        self.assertEqual(400, self.client.put("/api/settings", json={**payload, "selected_scenario": "missing"}).status_code)
        bad_url = {**payload, "chat": {**payload["chat"], "base_url": "file:///tmp/key"}}
        self.assertEqual(400, self.client.put("/api/settings", json=bad_url).status_code)
        empty_model = {**payload, "embedding": {**payload["embedding"], "model": " "}}
        self.assertEqual(400, self.client.put("/api/settings", json=empty_model).status_code)
        self.assertEqual(200, self.client.post("/api/settings/reset").status_code)

    def test_openai_compatible_settings_are_accepted_by_api(self):
        payload = {
            "selected_scenario": "lighthouse",
            "chat": {
                "provider": "openai_compatible",
                "base_url": "https://provider.example.invalid/v1/v1/",
                "model": "contract-model",
                "api_key": "CHAT-SECRET",
            },
            "embedding": {
                "base_url": "http://localhost:8081/v1",
                "model": "embed",
                "api_key": "",
            },
        }
        response = self.client.put("/api/settings", json=payload)
        self.assertEqual(200, response.status_code, response.text)
        body = response.json()
        self.assertEqual("openai_compatible", body["saved"]["chat"]["provider"])
        self.assertEqual("https://provider.example.invalid/v1", body["saved"]["chat"]["base_url"])
        self.assertEqual("外部 OpenAI互換API", body["chat_provider_label"])
        self.assertNotIn("CHAT-SECRET", response.text)
        self.assertNotIn("CHAT-SECRET", Path(body["settings_path"]).read_text(encoding="utf-8"))

    def test_connection_endpoints_do_not_create_game_session(self):
        before = set(web_api.manager._sessions)
        with patch.object(web_api.connection_tester, "chat", return_value={"ok": True, "service": "chat"}), patch.object(web_api.connection_tester, "embedding", return_value={"ok": True, "service": "embedding", "dimensions": 3}):
            self.assertTrue(self.client.post("/api/connections/chat/test", json={}).json()["ok"])
            self.assertEqual(3, self.client.post("/api/connections/embedding/test", json={}).json()["dimensions"])
        self.assertEqual(before, set(web_api.manager._sessions))

    def test_gemini_connection_and_new_session_table_turn_share_latest_settings(self):
        payload = {
            "selected_scenario": "lighthouse",
            "chat": {
                "provider": "openai_compatible",
                "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
                "model": "gemini-3.5-flash",
                "api_key": "GEMINI-SECRET",
            },
            "embedding": {"base_url": "http://localhost:8081/v1", "model": "embed", "api_key": ""},
        }
        self.assertEqual(200, self.client.put("/api/settings", json=payload).status_code)
        calls = []

        def compatible_response(game, url, body, timeout, tag):
            calls.append((game, url, body, tag))
            return {"choices": [{"message": {"content": "GM: 風が吹いている。"}}]}

        with patch("fixed_truth_ai_gm_mvp.Game.post_json", autospec=True, side_effect=compatible_response):
            tested = self.client.post("/api/connections/chat/test", json={}).json()
            self.assertTrue(tested["ok"])
            created = self.client.post(
                "/api/sessions", json={"scenario_id": "lighthouse"}
            )
            self.assertEqual(201, created.status_code, created.text)
            session = web_api.manager.get(created.json()["session_id"])
            notes, _banter = session.game.render_table_turn(
                ["GM: 風が吹いている。"],
                {"raw": "海を見る", "action_type": "inspect"},
                {"status": "ok", "category": "no_reveal"},
                [],
                session.state,
            )

        expected = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
        self.assertEqual(["BANTER", "TABLE_TURN"], [call[3] for call in calls])
        self.assertEqual([expected, expected], [call[1] for call in calls])
        self.assertEqual("openai_compatible", session.game.runtime_settings["chat_provider"])
        self.assertEqual("gemini-3.5-flash", session.game.runtime_settings["chat_model"])
        self.assertEqual("GEMINI-SECRET", session.game.runtime_settings["chat_api_key"])
        self.assertEqual("gemini-3.5-flash", session.game.llm_model())
        self.assertEqual(
            ["gemini-3.5-flash", "gemini-3.5-flash"],
            [call[2]["model"] for call in calls],
        )
        self.assertTrue(any("風が吹いている" in note for note in notes))


if __name__ == "__main__":
    unittest.main()
