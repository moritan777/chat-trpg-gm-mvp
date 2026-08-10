from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from chat_trpg_web.session_manager import SessionManager
from fixed_truth_ai_gm_mvp import VERSION


ROOT = Path(__file__).resolve().parent
WEBUI = ROOT / "webui"
app = FastAPI(title="Chat TTRPG GM Local API", version=VERSION)
manager = SessionManager()


class CreateSessionRequest(BaseModel):
    scenario_id: str


class CommandRequest(BaseModel):
    text: str


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
