from __future__ import annotations

from pathlib import Path
from typing import Dict
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app.agent import DentistAIAgent
from app.config import ADMIN_TOKEN
from app.db import init_db
from app.repository import create_appointment, list_appointments, list_leads, save_lead

app = FastAPI(title="Dentist Assistant API", version="0.1.0")

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    intent: str | None = None


class ResetRequest(BaseModel):
    session_id: str


sessions: Dict[str, DentistAIAgent] = {}

init_db()


def get_agent(session_id: str) -> DentistAIAgent:
    if session_id not in sessions:
        sessions[session_id] = DentistAIAgent()
    return sessions[session_id]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request=request, name="chat.html")


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    session_id = payload.session_id or str(uuid4())
    agent = get_agent(session_id)
    reply = agent.respond(payload.message)
    state = agent.state
    intent = state.last_intent

    save_lead(
        session_id=session_id,
        name=state.patient_name or "",
        contact="",
        message=payload.message,
        intent=intent or "unknown",
    )

    if "appointment is confirmed for" in reply.lower():
        slot = reply.split("confirmed for", maxsplit=1)[-1].split(".", maxsplit=1)[0].strip()
        create_appointment(
            session_id=session_id,
            patient_name=state.patient_name or "",
            slot=slot,
            notes="auto-saved from chat",
        )

    return ChatResponse(reply=reply, session_id=session_id, intent=intent)


@app.post("/reset")
def reset(payload: ResetRequest) -> dict[str, str]:
    agent = get_agent(payload.session_id)
    agent.reset()
    return {"status": "reset"}


def _check_admin_token(x_admin_token: str | None) -> None:
    if not x_admin_token or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="invalid admin token")


@app.get("/admin/leads")
def admin_leads(x_admin_token: str | None = Header(default=None)) -> list[dict[str, str]]:
    _check_admin_token(x_admin_token)
    rows = list_leads()
    return [
        {
            "id": str(r.id),
            "session_id": r.session_id,
            "name": r.name,
            "message": r.message,
            "intent": r.intent,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@app.get("/admin/appointments")
def admin_appointments(x_admin_token: str | None = Header(default=None)) -> list[dict[str, str]]:
    _check_admin_token(x_admin_token)
    rows = list_appointments()
    return [
        {
            "id": str(r.id),
            "session_id": r.session_id,
            "patient_name": r.patient_name,
            "slot": r.slot,
            "status": r.status,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
