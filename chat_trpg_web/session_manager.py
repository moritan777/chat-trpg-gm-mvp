import json
import tempfile
import threading
import uuid
from pathlib import Path

from fixed_truth_ai_gm_mvp import GameSession
from md_to_scenario import load_scenario_markdown


ROOT = Path(__file__).resolve().parent.parent


class ScenarioCatalog:
    """Expose authored scenarios without creating a second scenario format."""

    def __init__(self):
        self._temporary = tempfile.TemporaryDirectory(prefix="chat-trpg-scenarios-")
        self._scenarios = {
            "lighthouse": {
                "id": "lighthouse",
                "title": "消えた灯台守",
                "author_path": ROOT / "author_scenario_lighthouse_v2150.md",
            }
        }

    def list_public(self):
        return [{"id": item["id"], "title": item["title"]} for item in self._scenarios.values()]

    def scenario_dir(self, scenario_id):
        item = self._scenarios.get(scenario_id)
        if item is None:
            raise KeyError(scenario_id)
        destination = Path(self._temporary.name) / scenario_id
        scenario_file = destination / "scenario.json"
        if not scenario_file.exists():
            scenario, _tests = load_scenario_markdown(item["author_path"])
            destination.mkdir(parents=True, exist_ok=True)
            scenario_file.write_text(
                json.dumps(scenario, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return destination


class SessionManager:
    def __init__(self, catalog=None):
        self.catalog = catalog or ScenarioCatalog()
        self._sessions = {}
        self._lock = threading.RLock()

    def create(self, scenario_id):
        scenario_dir = self.catalog.scenario_dir(scenario_id)
        session = GameSession(scenario_dir)
        session_id = str(uuid.uuid4())
        with self._lock:
            self._sessions[session_id] = session
        return session_id, session

    def get(self, session_id):
        with self._lock:
            session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(session_id)
        return session

    def delete(self, session_id):
        with self._lock:
            session = self._sessions.pop(session_id, None)
        if session is None:
            raise KeyError(session_id)
        session.close()
