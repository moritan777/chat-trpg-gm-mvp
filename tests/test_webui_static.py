import unittest
from pathlib import Path


class WebUiStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = Path("webui/index.html").read_text(encoding="utf-8")
        cls.script = Path("webui/app.js").read_text(encoding="utf-8")
        cls.style = Path("webui/style.css").read_text(encoding="utf-8")

    def test_settings_form_and_password_fields_exist(self):
        for field in ("scenario", "chat-provider", "chat-url", "chat-model", "embedding-url", "embedding-model", "save-settings", "reset-settings", "clear-keys"):
            self.assertIn(f'id="{field}"', self.html)
        self.assertIn('id="chat-key" type="password"', self.html)
        self.assertIn('id="embedding-key" type="password"', self.html)

    def test_summary_collapse_and_connection_states_exist(self):
        for field in (
            "settings-summary", "settings-details", "summary-scenario",
            "summary-chat-state", "summary-embedding-state", "summary-save-state",
        ):
            self.assertIn(f'id="{field}"', self.html)
        self.assertIn("接続設定を開く", self.html)
        self.assertIn("接続設定を閉じる", self.html)
        for state in ("未確認", "接続成功", "接続失敗"):
            self.assertIn(state, self.script)

    def test_api_key_controls_and_game_focus_behavior_exist(self):
        self.assertIn('id="chat-key-use" type="checkbox"', self.html)
        self.assertIn('id="embedding-key-use" type="checkbox"', self.html)
        self.assertIn('settingsDetails.open = false', self.script)
        self.assertIn('commandInput.focus()', self.script)
        self.assertIn('setSettingsDisabled(true)', self.script)
        self.assertIn('resetConnectionState(service)', self.script)
        self.assertIn('byId(`${service}-${suffix}`).addEventListener("input"', self.script)

    def test_browser_does_not_persist_log_or_render_secrets_as_html(self):
        for forbidden in ("localStorage", "sessionStorage", "innerHTML", "console."):
            self.assertNotIn(forbidden, self.script)
        self.assertIn("textContent", self.script)

    def test_browser_only_uses_same_origin_api(self):
        self.assertIn('fetch(path', self.script)
        self.assertIn('"/api/', self.script)
        self.assertNotIn("http://127.0.0.1:8080", self.script)
        self.assertNotIn("http://127.0.0.1:8081", self.script)

    def test_conditional_history_follow_and_notification(self):
        self.assertIn('id="history"', self.html)
        self.assertIn('id="new-message"', self.html)
        self.assertIn("HISTORY_BOTTOM_THRESHOLD = 120", self.script)
        self.assertIn("scrollHeight - history.scrollTop - history.clientHeight", self.script)
        self.assertIn("requestAnimationFrame", self.script)
        self.assertIn("const follow = isHistoryNearBottom()", self.script)
        self.assertIn("overflow-y: auto", self.style)

    def test_rendered_lines_preserve_gm_npc_and_companion_speakers(self):
        self.assertIn("function renderedLine(line)", self.script)
        self.assertIn("data.lines.map(renderedLine)", self.script)

    def test_three_chat_providers_are_present(self):
        for provider in ("llama_cpp", "openai_compatible", "none"):
            self.assertIn(f'value="{provider}"', self.html)

    def test_stale_python_server_is_detected_and_explained(self):
        self.assertIn("data.chat_providers", self.script)
        self.assertIn("更新後はWebサーバーを再起動してください", self.script)
        self.assertIn("Chat Providerはllama_cppまたはnone", self.script)

    def test_windows_launcher_offers_debug_all(self):
        launcher = Path("start_web.bat").read_text(encoding="utf-8")
        self.assertIn("--debug-all", launcher)
        self.assertIn("python -u web_api.py", launcher)


if __name__ == "__main__": unittest.main()
