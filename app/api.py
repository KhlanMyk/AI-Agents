from __future__ import annotations

from pathlib import Path
from typing import Dict
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app.agent import DentistAIAgent

app = FastAPI(title="Dentist Assistant API", version="0.1.0")

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str


class ResetRequest(BaseModel):
    session_id: str


sessions: Dict[str, DentistAIAgent] = {}


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
    return ChatResponse(reply=reply, session_id=session_id)


@app.post("/reset")
def reset(payload: ResetRequest) -> dict[str, str]:
    agent = get_agent(payload.session_id)
    agent.reset()
    return {"status": "reset"}
