from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from chat_trpg_web.connections import ConnectionTester
from chat_trpg_web.session_manager import ScenarioCatalog, SessionManager
from chat_trpg_web.settings import SettingsService
from fixed_truth_ai_gm_mvp import VERSION


ROOT = Path(__file__).resolve().parent
WEBUI = ROOT / "webui"
app = FastAPI(title="Chat TTRPG GM Local API", version=VERSION)
catalog = ScenarioCatalog()
settings_service = SettingsService(scenario_provider=catalog.list_public)
manager = SessionManager(catalog, settings_service)
connection_tester = ConnectionTester()


class CreateSessionRequest(BaseModel):
    scenario_id: str


class CommandRequest(BaseModel):
    text: str


class ChatSettingsRequest(BaseModel):
    provider: str
    base_url: str
    model: str
    api_key: str = ""


class EmbeddingSettingsRequest(BaseModel):
    base_url: str
    model: str
    api_key: str = ""


class SettingsRequest(BaseModel):
    selected_scenario: str
    chat: ChatSettingsRequest
    embedding: EmbeddingSettingsRequest


class ConnectionTestRequest(BaseModel):
    settings: SettingsRequest | None = None


def request_dict(request):
    return request.model_dump() if hasattr(request, "model_dump") else request.dict()


def effective_for_test(request):
    if request.settings is None:
        return settings_service.effective(), "effective"
    raw = request_dict(request.settings)
    validated = settings_service.validate(raw)
    effective = settings_service.effective()
    effective["selected_scenario"] = validated["selected_scenario"]
    for service in ("chat", "embedding"):
        effective[service].update(validated[service])
        supplied = raw[service].get("api_key", "")
        if supplied:
            effective[service]["api_key"] = supplied
    return effective, "form"


def public_session(session_id, session, opening=None):
    response = {"session_id": session_id, **session.get_public_state()}
    if opening is not None:
        response["opening"] = opening
    return response


def require_session(session_id):
    try:
        return manager.get(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found") from None


@app.get("/api/health")
def health():
    return {"status": "ok", "version": VERSION.split()[0]}


@app.get("/api/scenarios")
def scenarios():
    return {"scenarios": manager.catalog.list_public()}


@app.get("/api/settings")
def get_settings():
    return settings_service.get_public_settings()


@app.put("/api/settings")
def put_settings(request: SettingsRequest):
    raw = request_dict(request)
    try:
        return settings_service.save(raw, raw["chat"].get("api_key"), raw["embedding"].get("api_key"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@app.post("/api/settings/reset")
def reset_settings():
    return settings_service.reset()


@app.post("/api/settings/secrets/clear")
def clear_settings_secrets():
    settings_service.clear_session_secrets()
    return settings_service.get_public_settings()


@app.post("/api/connections/chat/test")
def test_chat_connection(request: ConnectionTestRequest):
    try:
        effective, source = effective_for_test(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    result = connection_tester.chat(effective)
    result["settings_source"] = source
    return result


@app.post("/api/connections/embedding/test")
def test_embedding_connection(request: ConnectionTestRequest):
    try:
        effective, source = effective_for_test(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    result = connection_tester.embedding(effective)
    result["settings_source"] = source
    return result


@app.post("/api/sessions", status_code=201)
def create_session(request: CreateSessionRequest):
    try:
        session_id, session = manager.create(request.scenario_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Scenario not found") from None
    started = session.start()
    return public_session(session_id, session, started["opening"])


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    return public_session(session_id, require_session(session_id))


@app.post("/api/sessions/{session_id}/commands")
def command(session_id: str, request: CommandRequest):
    session = require_session(session_id)
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Command text must not be empty")
    try:
        turn = session.process_command(request.text)
    except RuntimeError:
        raise HTTPException(status_code=409, detail="Session is finished") from None
    return {
        "session_id": session_id,
        "lines": turn["lines"],
        "success": turn["success"],
        "current_location": turn["current_location"],
        "finished": turn["finished"],
    }


@app.delete("/api/sessions/{session_id}", status_code=204)
def delete_session(session_id: str):
    try:
        manager.delete(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found") from None


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(WEBUI / "index.html")


app.mount("/static", StaticFiles(directory=WEBUI), name="static")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
