import json
import os
import tempfile
import threading
from copy import deepcopy
from pathlib import Path

from fixed_truth_ai_gm_mvp import normalize_api_base_url


SETTINGS_VERSION = 1
CHAT_PROVIDERS = {
    "llama_cpp": "ローカル llama.cpp",
    "openai_compatible": "外部 OpenAI互換API",
    "none": "LLMを使用しない",
}
DEFAULTS = {
    "settings_version": SETTINGS_VERSION,
    "selected_scenario": "lighthouse",
    "chat": {"provider": "llama_cpp", "base_url": "http://127.0.0.1:8080/v1", "model": "local-model"},
    "embedding": {"base_url": "http://127.0.0.1:8081/v1", "model": "local-embedding"},
}


def settings_path(environ=None, platform=None, home=None):
    env = os.environ if environ is None else environ
    platform = os.name if platform is None else platform
    if platform == "nt" and env.get("LOCALAPPDATA"):
        return Path(env["LOCALAPPDATA"]) / "ChatTtrpgGm" / "settings.json"
    if env.get("XDG_CONFIG_HOME"):
        return Path(env["XDG_CONFIG_HOME"]) / "chat-ttrpg-gm" / "settings.json"
    return Path(home or Path.home()) / ".config" / "chat-ttrpg-gm" / "settings.json"


def normalize_base_url(value):
    try:
        return normalize_api_base_url(value)
    except ValueError:
        raise ValueError("Base URLはhttpまたはhttpsの有効なURLを指定してください。")


class SettingsService:
    """Canonical resolver for environment, persisted Web settings and secrets."""

    def __init__(self, path=None, environ=None, scenario_provider=None):
        self.path = Path(path) if path else settings_path(environ=environ)
        self.environ = os.environ if environ is None else environ
        self.scenario_provider = scenario_provider or (lambda: [{"id": "lighthouse", "title": "消えた灯台守"}])
        self._secrets = {"chat": "", "embedding": ""}
        self._lock = threading.RLock()
        self.warning = None
        self.saved = self.load()

    def load(self):
        self.warning = None
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return self.validate(raw, allow_scenario_fallback=True)
        except FileNotFoundError:
            return deepcopy(DEFAULTS)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            self.warning = "設定ファイルを読み込めなかったため、初期設定を使用しています。"
            return deepcopy(DEFAULTS)

    def validate(self, value, allow_scenario_fallback=False):
        if not isinstance(value, dict):
            raise ValueError("設定形式が不正です。")
        selected = str(value.get("selected_scenario", DEFAULTS["selected_scenario"])).strip()
        available = [item["id"] for item in self.scenario_provider()]
        warning = None
        if selected not in available:
            if not available:
                raise ValueError("利用可能なシナリオがありません。")
            if not allow_scenario_fallback:
                raise ValueError("選択されたシナリオは利用できません。")
            selected = available[0]
            warning = "保存されたシナリオが見つからないため、先頭のシナリオを選択しました。設定ファイルは自動更新していません。"
        chat = value.get("chat") or {}
        embedding = value.get("embedding") or {}
        provider = str(chat.get("provider", "llama_cpp")).strip()
        if provider not in CHAT_PROVIDERS:
            raise ValueError("Chat Providerはllama_cpp、openai_compatible、noneのいずれかを指定してください。")
        result = {
            "settings_version": SETTINGS_VERSION,
            "selected_scenario": selected,
            "chat": {
                "provider": provider,
                "base_url": normalize_base_url(chat.get("base_url", DEFAULTS["chat"]["base_url"])),
                "model": self._model(chat.get("model", DEFAULTS["chat"]["model"]), "Chat"),
            },
            "embedding": {
                "base_url": normalize_base_url(embedding.get("base_url", DEFAULTS["embedding"]["base_url"])),
                "model": self._model(embedding.get("model", DEFAULTS["embedding"]["model"]), "Embedding"),
            },
        }
        if warning:
            self.warning = warning
        return result

    @staticmethod
    def _model(value, label):
        value = str(value or "").strip()
        if not value:
            raise ValueError(f"{label} Modelを入力してください。")
        return value

    def save(self, value, chat_api_key=None, embedding_api_key=None):
        validated = self.validate(value)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix="settings-", suffix=".tmp", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(validated, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        except Exception:
            try: os.unlink(temporary)
            except OSError: pass
            raise
        with self._lock:
            self.saved = validated
            if chat_api_key is not None and chat_api_key != "":
                self._secrets["chat"] = chat_api_key
            if embedding_api_key is not None and embedding_api_key != "":
                self._secrets["embedding"] = embedding_api_key
        return self.get_public_settings()

    def reset(self):
        try: self.path.unlink()
        except FileNotFoundError: pass
        self.saved = deepcopy(DEFAULTS)
        self.warning = None
        self.clear_session_secrets()
        return self.get_public_settings()

    def clear_session_secrets(self):
        with self._lock:
            self._secrets = {"chat": "", "embedding": ""}

    def effective(self):
        env = self.environ
        def choose(names, stored, default):
            for name in names:
                if env.get(name): return env[name], f"environment:{name}"
            return (stored, "settings.json") if self.path.exists() else (default, "default")
        provider, provider_source = choose(["LLM_PROVIDER"], self.saved["chat"]["provider"], "llama_cpp")
        if provider not in CHAT_PROVIDERS:
            provider = "llama_cpp"
        chat_url, chat_url_source = choose(["LLAMA_CPP_BASE_URL", "LLM_BASE_URL", "OPENAI_BASE_URL"], self.saved["chat"]["base_url"], DEFAULTS["chat"]["base_url"])
        chat_model, chat_model_source = choose(["LLAMA_CPP_MODEL", "LLM_MODEL", "OPENAI_MODEL"], self.saved["chat"]["model"], DEFAULTS["chat"]["model"])
        emb_url, emb_url_source = choose(["EMBEDDING_BASE_URL", "EMB_BASE_URL"], self.saved["embedding"]["base_url"], DEFAULTS["embedding"]["base_url"])
        emb_model, emb_model_source = choose(["EMBEDDING_MODEL", "EMB_MODEL"], self.saved["embedding"]["model"], DEFAULTS["embedding"]["model"])
        table_temp, table_source = choose(["TABLE_TURN_TEMPERATURE", "GM_LINE_REWRITE_TEMPERATURE"], "0.9", "0.9")
        discovery, discovery_source = choose(["DISCOVERY_DISPLAY"], "gm", "gm")
        with self._lock: secrets = dict(self._secrets)
        return {
            "selected_scenario": self.saved["selected_scenario"],
            "chat": {"provider": provider, "base_url": normalize_base_url(chat_url), "model": chat_model.strip(), "api_key": secrets["chat"]},
            "embedding": {"base_url": normalize_base_url(emb_url), "model": emb_model.strip(), "api_key": secrets["embedding"]},
            "advanced": {"table_turn_temperature": table_temp, "discovery_display": discovery},
            "sources": {"selected_scenario": "settings.json" if self.path.exists() else "default", "chat.provider": provider_source, "chat.base_url": chat_url_source, "chat.model": chat_model_source, "embedding.base_url": emb_url_source, "embedding.model": emb_model_source, "table_turn_temperature": table_source, "discovery_display": discovery_source},
        }

    def get_public_settings(self):
        effective = self.effective()
        safe_effective = deepcopy(effective)
        safe_effective["chat"].pop("api_key", None)
        safe_effective["embedding"].pop("api_key", None)
        return {
            "settings_version": SETTINGS_VERSION,
            "settings_path": str(self.path),
            "saved": deepcopy(self.saved),
            "effective": safe_effective,
            "api_keys": {"chat": self._key_status("chat"), "embedding": self._key_status("embedding")},
            "chat_providers": [{"value": value, "label": label} for value, label in CHAT_PROVIDERS.items()],
            "chat_provider_label": CHAT_PROVIDERS.get(effective["chat"]["provider"], effective["chat"]["provider"]),
            "chat_disabled": effective["chat"]["provider"] == "none",
            "scenarios": self.scenario_provider(),
            "selected_scenario": self.saved["selected_scenario"],
            "warning": self.warning,
        }

    def _key_status(self, service):
        with self._lock: configured = bool(self._secrets[service])
        return {"configured": configured, "source": "session" if configured else "unset"}
