import json
import os
import tempfile
import unittest
from pathlib import Path

from chat_trpg_web.settings import DEFAULTS, SettingsService, normalize_base_url, settings_path


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "nested" / "settings.json"
        self.scenarios = lambda: [{"id": "lighthouse", "title": "消えた灯台守", "available": True}]

    def tearDown(self): self.temp.cleanup()
    def service(self, env=None): return SettingsService(self.path, environ=env or {}, scenario_provider=self.scenarios)

    def test_windows_and_portable_paths(self):
        self.assertEqual(Path(r"C:\Users\me\AppData\Local") / "ChatTtrpgGm" / "settings.json", settings_path({"LOCALAPPDATA": r"C:\Users\me\AppData\Local"}, "nt"))
        portable = settings_path({}, "posix", Path(self.temp.name))
        self.assertNotEqual(Path.cwd(), portable.parent)

    def test_utf8_version_unknown_fields_and_atomic_save(self):
        service = self.service()
        value = {**DEFAULTS, "unknown": "ignored", "chat": {**DEFAULTS["chat"], "model": "日本語モデル"}}
        service.save(value)
        raw = self.path.read_text(encoding="utf-8")
        self.assertIn("日本語モデル", raw)
        self.assertNotIn("unknown", raw)
        self.assertEqual(1, json.loads(raw)["settings_version"])
        self.assertEqual("日本語モデル", self.service().saved["chat"]["model"])
        self.assertEqual([], list(self.path.parent.glob("*.tmp")))

    def test_corrupt_json_recovers_and_reset_removes_file(self):
        self.path.parent.mkdir(parents=True); self.path.write_text("{secret broken", encoding="utf-8")
        service = self.service()
        self.assertEqual(DEFAULTS["chat"]["model"], service.saved["chat"]["model"])
        self.assertIsNotNone(service.warning)
        service.save(DEFAULTS); service.reset()
        self.assertFalse(self.path.exists())

    def test_priority_and_sources(self):
        service = self.service(); service.save({**DEFAULTS, "chat": {**DEFAULTS["chat"], "model": "saved"}})
        self.assertEqual("saved", service.effective()["chat"]["model"])
        self.assertEqual("settings.json", service.effective()["sources"]["chat.model"])
        env_service = SettingsService(self.path, environ={"LLM_MODEL": "environment"}, scenario_provider=self.scenarios)
        self.assertEqual("environment", env_service.effective()["chat"]["model"])
        self.assertEqual("environment:LLM_MODEL", env_service.effective()["sources"]["chat.model"])

    def test_secrets_are_separate_never_saved_or_public(self):
        service = self.service(); service.save(DEFAULTS, "chat-secret", "embedding-secret")
        self.assertNotIn("secret", self.path.read_text(encoding="utf-8"))
        public = json.dumps(service.get_public_settings())
        self.assertNotIn("chat-secret", public); self.assertNotIn("embedding-secret", public)
        self.assertTrue(service.get_public_settings()["api_keys"]["chat"]["configured"])
        service.clear_session_secrets()
        self.assertFalse(service.get_public_settings()["api_keys"]["chat"]["configured"])

    def test_validation_and_normalization(self):
        self.assertEqual("http://localhost:8080/v1", normalize_base_url(" http://localhost:8080/v1/v1/ "))
        for bad in ("", "file:///tmp/x", "http://"):
            with self.assertRaises(ValueError): normalize_base_url(bad)
        service = self.service()
        with self.assertRaises(ValueError): service.validate({**DEFAULTS, "selected_scenario": "missing"})
        with self.assertRaises(ValueError): service.validate({**DEFAULTS, "chat": {**DEFAULTS["chat"], "model": " "}})

    def test_openai_compatible_is_saved_without_secret_and_unknown_is_rejected(self):
        service = self.service()
        value = {**DEFAULTS, "chat": {"provider": "openai_compatible", "base_url": "https://example.invalid/v1/v1", "model": "example-model"}}
        service.save(value, "TOP-SECRET")
        saved = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual("openai_compatible", saved["chat"]["provider"])
        self.assertEqual("https://example.invalid/v1", saved["chat"]["base_url"])
        self.assertNotIn("TOP-SECRET", json.dumps(saved))
        self.assertEqual("外部 OpenAI互換API", service.get_public_settings()["chat_provider_label"])
        with self.assertRaises(ValueError): service.validate({**DEFAULTS, "chat": {**DEFAULTS["chat"], "provider": "unknown"}})


if __name__ == "__main__": unittest.main()
