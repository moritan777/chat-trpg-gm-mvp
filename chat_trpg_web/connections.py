import json
import logging
import re
import time

from fixed_truth_ai_gm_mvp import Game, normalize_api_base_url

logger = logging.getLogger("uvicorn.error")


class ResponseFormatError(ValueError):
    """An OpenAI-compatible endpoint returned a structurally invalid response."""

    def __init__(self, detail, url):
        super().__init__(detail)
        self.detail = detail
        self.url = url


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
        # Connection tests must exercise the values currently entered in the
        # form.  The engine normally lets environment variables take priority,
        # which would otherwise silently test a different endpoint.
        chat_base = normalize_api_base_url(effective["chat"]["base_url"])
        embedding_base = normalize_api_base_url(effective["embedding"]["base_url"])
        game.llm_base_url = lambda: chat_base
        game.emb_base_url = lambda: embedding_base
        return game

    def chat(self, effective, timeout=10):
        if effective["chat"]["provider"] == "none":
            return {"ok": True, "disabled": True, "service": "chat", "provider": "none", "status": "無効"}
        game = self._game(effective)
        # A tiny output limit can be consumed by Gemini 2.5's internal thinking
        # before it emits message.content.  Leave enough room for the requested
        # short answer while keeping this connection check inexpensive.
        body = {"model": effective["chat"]["model"], "messages": [{"role": "user", "content": "Reply OK."}], "max_tokens": 64, "temperature": 0}
        started = time.perf_counter()
        last_error = ValueError("response")
        for url in game.llm_chat_urls():
            logger.info("Chat connection test URL: %s", url)
            try:
                data = game.post_json(url, body, timeout, "BANTER")
                logger.info("Chat connection test response JSON:\n%s", json.dumps(data, ensure_ascii=False, indent=2))
                self._chat_content(data, url)
                break
            except Exception as exc:
                if isinstance(exc, ResponseFormatError):
                    logger.error("Invalid chat response from %s (%s):\n%s", url, exc.detail, json.dumps(data, ensure_ascii=False, indent=2))
                    # The endpoint responded successfully, so trying a guessed
                    # /v1 fallback would only hide the useful format failure.
                    return self._failure("chat", effective["chat"], exc)
                last_error = exc
        else:
            return self._failure("chat", effective["chat"], last_error)
        result = {"ok": True, "service": "chat", "provider": effective["chat"]["provider"], "base_url": game.llm_base_url(), "url": url, "model": effective["chat"]["model"], "latency_ms": round((time.perf_counter()-started)*1000), "status": "接続成功"}
        result["response_model"] = data.get("model") if isinstance(data.get("model"), str) else effective["chat"]["model"]
        return result

    @staticmethod
    def _chat_content(data, url):
        if not isinstance(data, dict):
            raise ResponseFormatError("response JSON がオブジェクトではありません", url)
        if "error" in data:
            raise ResponseFormatError("APIから error オブジェクトが返却されました", url)
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ResponseFormatError("choices が存在しません", url)
        choice = choices[0]
        message = choice.get("message") if isinstance(choice, dict) else None
        if not isinstance(message, dict) or "content" not in message:
            raise ResponseFormatError("message.content が存在しません", url)
        content = message["content"]
        if isinstance(content, str):
            return content
        # Some compatible APIs use OpenAI's structured content-part form.
        if isinstance(content, list):
            texts = [part.get("text") for part in content if isinstance(part, dict) and isinstance(part.get("text"), str)]
            if texts:
                return "".join(texts)
        raise ResponseFormatError("message.content が文字列またはテキスト配列ではありません", url)

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
        elif isinstance(exc, ResponseFormatError):
            code, status = "response", f"{exc.detail}（実際のURL: {exc.url}）"
        else: code, status = "response", "応答形式がOpenAI互換ではありません。"
        return {"ok": False, "service": service, "base_url": config["base_url"], "model": config["model"], "error": code, "status": status}
