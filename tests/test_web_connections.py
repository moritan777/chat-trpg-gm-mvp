import unittest
from unittest.mock import patch

from chat_trpg_web.connections import ConnectionTester
from chat_trpg_web.settings import DEFAULTS


def effective(chat_key="", embedding_key=""):
    return {
        "chat": {**DEFAULTS["chat"], "api_key": chat_key},
        "embedding": {**DEFAULTS["embedding"], "api_key": embedding_key},
    }


class ConnectionTests(unittest.TestCase):
    def setUp(self): self.tester = ConnectionTester()

    @patch("fixed_truth_ai_gm_mvp.Game.post_json")
    def test_chat_success(self, post):
        post.return_value = {"choices": [{"message": {"content": "OK"}}]}
        result = self.tester.chat(effective())
        self.assertTrue(result["ok"]); self.assertEqual("chat", result["service"])
        self.assertEqual(3, post.call_args.args[1]["max_tokens"])

    @patch("fixed_truth_ai_gm_mvp.Game.post_json")
    def test_chat_auth_connection_and_timeout_are_safe(self, post):
        for error, code in ((RuntimeError("HTTP 401 secret body"), "authentication"), (ConnectionRefusedError("secret"), "connection"), (TimeoutError("secret"), "timeout")):
            post.side_effect = error
            result = self.tester.chat(effective("TOP-SECRET"))
            self.assertFalse(result["ok"]); self.assertEqual(code, result["error"])
            self.assertNotIn("TOP-SECRET", str(result)); self.assertNotIn("secret body", str(result))

    @patch("fixed_truth_ai_gm_mvp.Game.post_json")
    def test_chat_status_classification(self, post):
        for status, code in ((403, "authentication"), (404, "not_found"), (408, "timeout"), (429, "rate_limit"), (500, "http")):
            post.side_effect = RuntimeError(f"HTTP {status} unsafe response")
            self.assertEqual(code, self.tester.chat(effective())["error"])

    def test_none_chat_is_disabled_without_request(self):
        config = effective(); config["chat"]["provider"] = "none"
        result = self.tester.chat(config)
        self.assertTrue(result["ok"]); self.assertTrue(result["disabled"])

    @patch("fixed_truth_ai_gm_mvp.Game.post_json")
    def test_embedding_success_uses_response_dimensions(self, post):
        post.return_value = {"data": [{"embedding": [0.1, 0.2, 0.3, 0.4]}]}
        result = self.tester.embedding(effective())
        self.assertTrue(result["ok"]); self.assertEqual(4, result["dimensions"])

    @patch("fixed_truth_ai_gm_mvp.Game.post_json")
    def test_embedding_failure_is_safe(self, post):
        post.side_effect = ValueError("TOP-SECRET")
        result = self.tester.embedding(effective(embedding_key="TOP-SECRET"))
        self.assertFalse(result["ok"]); self.assertNotIn("TOP-SECRET", str(result))

    def test_engine_sends_service_specific_keys_only_in_headers(self):
        captured = []
        class Response:
            status, reason = 200, "OK"
            def read(self): return b'{"ok":true}'
        class Connection:
            def __init__(self, *args, **kwargs): pass
            def request(self, method, path, body=None, headers=None): captured.append(headers)
            def getresponse(self): return Response()
            def close(self): pass
        game = self.tester._game(effective("CHAT-KEY", "EMBED-KEY"))
        with patch("fixed_truth_ai_gm_mvp.http.client.HTTPConnection", Connection):
            game.post_json("http://localhost/chat", {}, 1, "BANTER")
            game.post_json("http://localhost/embeddings", {}, 1, "EMB")
        self.assertEqual("Bearer CHAT-KEY", captured[0]["Authorization"])
        self.assertEqual("Bearer EMBED-KEY", captured[1]["Authorization"])


if __name__ == "__main__": unittest.main()
