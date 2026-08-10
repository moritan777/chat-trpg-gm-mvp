import re
import time

from fixed_truth_ai_gm_mvp import Game


class ConnectionTester:
    """Connection-only adapter reusing the engine's OpenAI-compatible HTTP path."""

    def _game(self, effective):
        game = Game.__new__(Game)
        game.debug = game.debug_llm = game.debug_embedding = False
        game.runtime_settings = {
            "chat_base_url": effective["chat"]["base_url"], "chat_model": effective["chat"]["model"],
            "chat_api_key": effective["chat"].get("api_key", ""),
            "embedding_base_url": effective["embedding"]["base_url"], "embedding_model": effective["embedding"]["model"],
            "embedding_api_key": effective["embedding"].get("api_key", ""),
        }
        return game

    def chat(self, effective, timeout=10):
        if effective["chat"]["provider"] == "none":
            return {"ok": True, "disabled": True, "service": "chat", "provider": "none", "status": "無効"}
        game = self._game(effective)
        body = {"model": effective["chat"]["model"], "messages": [{"role": "user", "content": "Reply OK."}], "max_tokens": 3, "temperature": 0}
        started = time.perf_counter()
        last_error = ValueError("response")
        for url in game.llm_chat_urls():
            try:
                data = game.post_json(url, body, timeout, "BANTER")
                content = data.get("choices", [{}])[0].get("message", {}).get("content")
                if not isinstance(content, str): raise ValueError("response")
                break
            except Exception as exc:
                last_error = exc
        else:
            return self._failure("chat", effective["chat"], last_error)
        result = {"ok": True, "service": "chat", "provider": effective["chat"]["provider"], "base_url": game.llm_base_url(), "model": effective["chat"]["model"], "latency_ms": round((time.perf_counter()-started)*1000), "status": "接続成功"}
        if isinstance(data.get("model"), str): result["response_model"] = data["model"]
        return result

    def embedding(self, effective, timeout=10):
        game = self._game(effective)
        body = {"model": effective["embedding"]["model"], "input": ["test"]}
        started = time.perf_counter()
        last_error = ValueError("response")
        for url in game.emb_urls():
            try:
                data = game.post_json(url, body, timeout, "EMB")
                vectors = game.parse_embeddings(data)
                if len(vectors) != 1 or not isinstance(vectors[0], list): raise ValueError("response")
                break
            except Exception as exc:
                last_error = exc
        else:
            return self._failure("embedding", effective["embedding"], last_error)
        return {"ok": True, "service": "embedding", "base_url": game.emb_base_url(), "model": effective["embedding"]["model"], "dimensions": len(vectors[0]), "latency_ms": round((time.perf_counter()-started)*1000), "status": "接続成功"}

    @staticmethod
    def _failure(service, config, exc):
        message = str(exc)
        status_match = re.search(r"HTTP (\d{3})", message)
        if status_match and status_match.group(1) in {"401", "403"}: code, status = "authentication", "認証に失敗しました。APIキーを確認してください。"
        elif status_match and status_match.group(1) == "404": code, status = "not_found", "URLまたはモデル名を確認してください。"
        elif status_match and status_match.group(1) in {"408"}: code, status = "timeout", "接続がタイムアウトしました。"
        elif status_match and status_match.group(1) == "429": code, status = "rate_limit", "利用上限またはレート制限に達しました。"
        elif status_match: code, status = "http", f"サーバーがHTTP {status_match.group(1)}を返しました。"
        elif isinstance(exc, TimeoutError): code, status = "timeout", "接続がタイムアウトしました。"
        elif isinstance(exc, (ConnectionError, OSError)): code, status = "connection", "接続できません。サーバーが起動しているか確認してください。"
        else: code, status = "response", "応答形式がOpenAI互換ではありません。"
        return {"ok": False, "service": service, "base_url": config["base_url"], "model": config["model"], "error": code, "status": status}
