from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Dict
from uuid import uuid4
import re

from fastapi import FastAPI, Header, HTTPException, Request
import csv
import io

from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.agent import DentistAIAgent
from app.config import ADMIN_TOKEN, CORS_ORIGINS
from app.db import init_db, SessionLocal
from app.repository import (
    count_appointments,
    count_leads,
    create_appointment,
    get_appointment_by_id,
    get_lead_by_id,
    list_appointments,
    list_leads,
    save_lead,
    search_leads,
    update_appointment_status,
)
from app.security import sanitize_input, sanitize_for_sql
from app.session_manager import SessionManager
from app.chat_history import ChatHistory
from app.rate_limiter import RateLimiter
from app.logging_config import get_logger, log_error
from app.middleware import RequestMetricsMiddleware

app = FastAPI(title="Dentist Assistant API", version="0.1.0")

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
logger = get_logger(__name__)

# Register middleware for request/response tracking
app.add_middleware(RequestMetricsMiddleware)

# CORS – allow configured origins so browser-based frontends can call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=1500)
    session_id: str | None = None

    @field_validator("message")
    @classmethod
    def clean_message(cls, value: str) -> str:
        cleaned = sanitize_input(value)
        if not cleaned:
            raise ValueError("message cannot be blank")
        return cleaned

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if len(value) > 64 or not re.fullmatch(r"[A-Za-z0-9\-]+", value):
            raise ValueError("invalid session_id format")
        return value


class ChatResponse(BaseModel):
    """Response from chat endpoint with AI reply and session tracking."""
    reply: str
    session_id: str
    intent: str | None = None
    confidence: float | None = None
    suggestions: list[str] | None = None


class ErrorResponse(BaseModel):
    """Standard error response format."""
    detail: str
    error_code: str | None = None
    timestamp: str | None = None


class ResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) > 64 or not re.fullmatch(r"[A-Za-z0-9\-]+", cleaned):
            raise ValueError("invalid session_id format")
        return cleaned


sessions: Dict[str, DentistAIAgent] = {}
session_mgr = SessionManager(default_ttl_minutes=60)
chat_histories: Dict[str, ChatHistory] = {}
rate_limiter = RateLimiter(max_requests=30, window_seconds=60)

init_db()


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with logging."""
    log_error(
        logger,
        f"HTTP exception: {exc.detail}",
        endpoint=request.url.path,
        status_code=exc.status_code,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


def get_agent(session_id: str) -> DentistAIAgent:
    if session_id not in sessions:
        sessions[session_id] = DentistAIAgent()
        chat_histories[session_id] = ChatHistory()
    session_mgr.mark_active(session_id)
    return sessions[session_id]


@app.get("/health")
def health() -> dict:
    """
    Enhanced health check endpoint.
    
    Returns system status including database connectivity, API version,
    and uptime indicators.
    
    Status Codes:
        200: System is healthy and operational
        503: System has issues (database down, etc.)
    """
    db_status = "ok"
    try:
        # Check database connectivity
        with SessionLocal() as db:
            db.execute("SELECT 1")
    except Exception as e:
        db_status = f"error: {str(e)[:50]}"
    
    return {
        "status": "ok",
        "database": db_status,
        "version": "1.0.0",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    """Serve the web chat interface."""
    return templates.TemplateResponse(request=request, name="chat.html")


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    """
    Send a chat message and get AI response.
    
    - Rate limited to 30 requests per 60 seconds per session
    - Automatically tracks conversation history
    - Detects user intent and saves leads to database
    
    Args:
        payload: ChatRequest with message and optional session_id
        
    Returns:
        ChatResponse with AI reply, session_id, and detected intent
        
    Status Codes:
        200: Successful chat response
        400: Invalid request format
        422: Validation error (blank message, invalid session_id)
        429: Rate limit exceeded
    """
    session_id = payload.session_id or str(uuid4())
    
    # Check rate limit
    if not rate_limiter.is_allowed(session_id):
        raise HTTPException(
            status_code=429,
            detail="rate limit exceeded: max 30 requests per 60 seconds"
        )
    
    agent = get_agent(session_id)
    reply = agent.respond(payload.message)
    state = agent.state
    intent = state.last_intent
    confidence = state.last_confidence
    suggestions = state.last_suggestions or None

    # Track in chat history
    history = chat_histories[session_id]
    history.add_message("user", payload.message, intent)
    history.add_message("assistant", reply, intent)

    # Sanitize for SQL storage
    sanitized_msg = sanitize_for_sql(payload.message)
    
    save_lead(
        session_id=session_id,
        name=state.patient_name or "",
        contact=sanitize_for_sql(state.contact or ""),
        message=sanitized_msg,
        intent=intent,
    )

    slot = state.confirmed_slot
    if slot:
        create_appointment(
            session_id=session_id,
            patient_name=state.patient_name or "",
            slot=slot,
            notes="auto-saved from chat",
        )

    return ChatResponse(reply=reply, session_id=session_id, intent=intent, confidence=confidence, suggestions=suggestions)


@app.post("/reset")
def reset(payload: ResetRequest) -> dict[str, str]:
    """
    Reset chat session state.
    
    Clears the conversation history for a session without deleting database records.
    Useful for starting a fresh conversation with the same session_id.
    """
    agent = get_agent(payload.session_id)
    agent.reset()
    return {"status": "reset"}


def _check_admin_token(x_admin_token: str | None) -> None:
    if not x_admin_token or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="invalid admin token")


@app.get("/admin/leads")
def admin_leads(
    x_admin_token: str | None = Header(default=None),
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, str]]:
    """
    List chat leads with pagination (admin endpoint).

    Requires: x-admin-token header with correct admin token.
    Query params: limit (default 100), offset (default 0).
    Returns: Paginated list of leads with name, message, intent, and timestamp.
    """
    _check_admin_token(x_admin_token)
    rows = list_leads(limit=limit, offset=offset)
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
def admin_appointments(
    x_admin_token: str | None = Header(default=None),
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, str]]:
    """
    List appointments with pagination (admin endpoint).

    Requires: x-admin-token header with correct admin token.
    Query params: limit (default 100), offset (default 0).
    Returns: Paginated list of appointments with patient name, slot, status, and timestamp.
    """
    _check_admin_token(x_admin_token)
    rows = list_appointments(limit=limit, offset=offset)
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


@app.get("/admin/stats")
def admin_stats(x_admin_token: str | None = Header(default=None)) -> dict[str, int]:
    """
    Get aggregated chat statistics (admin endpoint).
    
    Requires: x-admin-token header with correct admin token.
    Returns: Total count of leads and appointments.
    """
    _check_admin_token(x_admin_token)
    return {
        "total_leads": count_leads(),
        "total_appointments": count_appointments(),
    }


@app.get("/admin/leads/export")
def export_leads_csv(
    x_admin_token: str | None = Header(default=None),
    limit: int = 5000,
) -> StreamingResponse:
    """
    Export all leads as a CSV file (admin endpoint).

    Requires: x-admin-token header with correct admin token.
    Query params: limit (default 5000).
    Returns: CSV file download with columns: id, session_id, name, contact, message, intent, created_at.
    """
    _check_admin_token(x_admin_token)
    rows = list_leads(limit=limit, offset=0)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "session_id", "name", "contact", "message", "intent", "created_at"])
    for r in rows:
        writer.writerow([
            r.id, r.session_id, r.name, r.contact, r.message, r.intent,
            r.created_at.isoformat(),
        ])
    output.seek(0)
    filename = f"leads_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/admin/appointments/export")
def export_appointments_csv(
    x_admin_token: str | None = Header(default=None),
    limit: int = 5000,
) -> StreamingResponse:
    """
    Export all appointments as a CSV file (admin endpoint).

    Requires: x-admin-token header with correct admin token.
    Query params: limit (default 5000).
    Returns: CSV file download with columns: id, session_id, patient_name, slot, notes, status, created_at.
    """
    _check_admin_token(x_admin_token)
    rows = list_appointments(limit=limit, offset=0)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "session_id", "patient_name", "slot", "notes", "status", "created_at"])
    for r in rows:
        writer.writerow([
            r.id, r.session_id, r.patient_name, r.slot, r.notes, r.status,
            r.created_at.isoformat(),
        ])
    output.seek(0)
    filename = f"appointments_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


class AppointmentStatusUpdate(BaseModel):
    """Request body for updating appointment status."""
    model_config = ConfigDict(extra="forbid")

    status: str = Field(description="New status: confirmed | cancelled | no_show | pending")

    @field_validator("status")
    @classmethod
    def check_status(cls, v: str) -> str:
        allowed = {"confirmed", "cancelled", "no_show", "pending"}
        if v not in allowed:
            raise ValueError(f"status must be one of: {', '.join(sorted(allowed))}")
        return v


@app.patch("/admin/appointments/{appointment_id}/status")
def update_appt_status(
    appointment_id: int,
    payload: AppointmentStatusUpdate,
    x_admin_token: str | None = Header(default=None),
) -> dict[str, str]:
    """
    Update appointment status (admin endpoint).

    Allows marking appointments as confirmed, cancelled, no_show, or pending.

    Requires: x-admin-token header with correct admin token.
    Returns: Updated appointment record.

    Status Codes:
        200: Status updated successfully
        401: Unauthorized
        404: Appointment not found
        422: Invalid status value
    """
    _check_admin_token(x_admin_token)
    updated = update_appointment_status(appointment_id, payload.status)
    if updated is None:
        raise HTTPException(status_code=404, detail="appointment not found")
    return {
        "id": str(updated.id),
        "patient_name": updated.patient_name,
        "slot": updated.slot,
        "status": updated.status,
        "updated": "true",
    }


@app.get("/admin/leads/search")
def admin_leads_search(
    x_admin_token: str | None = Header(default=None),
    intent: str | None = None,
    name: str | None = None,
    limit: int = 50,
) -> list[dict[str, str]]:
    """
    Search and filter leads by intent or patient name (admin endpoint).

    Requires: x-admin-token header with correct admin token.
    Query params: intent (exact match), name (partial match), limit (default 50).
    Returns: Filtered list of matching leads.
    """
    _check_admin_token(x_admin_token)
    rows = search_leads(intent=intent, name=name, limit=limit)
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


@app.get("/admin/leads/{lead_id}")
def admin_lead_detail(
    lead_id: int,
    x_admin_token: str | None = Header(default=None),
) -> dict[str, str]:
    """
    Get a single lead by ID (admin endpoint).

    Requires: x-admin-token header with correct admin token.
    Returns: Lead record with id, session_id, name, contact, message, intent, created_at.
    Status Codes:
        200: Lead found and returned
        404: Lead not found
    """
    _check_admin_token(x_admin_token)
    lead = get_lead_by_id(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead not found")
    return {
        "id": str(lead.id),
        "session_id": lead.session_id,
        "name": lead.name,
        "contact": lead.contact,
        "message": lead.message,
        "intent": lead.intent,
        "created_at": lead.created_at.isoformat(),
    }


@app.get("/admin/appointments/{appointment_id}")
def admin_appointment_detail(
    appointment_id: int,
    x_admin_token: str | None = Header(default=None),
) -> dict[str, str]:
    """
    Get a single appointment by ID (admin endpoint).

    Requires: x-admin-token header with correct admin token.
    Returns: Appointment record with id, session_id, patient_name, slot, status, notes, created_at.
    Status Codes:
        200: Appointment found and returned
        404: Appointment not found
    """
    _check_admin_token(x_admin_token)
    appt = get_appointment_by_id(appointment_id)
    if appt is None:
        raise HTTPException(status_code=404, detail="appointment not found")
    return {
        "id": str(appt.id),
        "session_id": appt.session_id,
        "patient_name": appt.patient_name,
        "slot": appt.slot,
        "status": appt.status,
        "notes": appt.notes,
        "created_at": appt.created_at.isoformat(),
    }


@app.get("/export/{session_id}")
def export_chat_history(session_id: str) -> dict:
    """
    Export chat conversation history in JSON format.
    
    Returns full message history for a session including timestamps and intents.
    
    Returns:
        Dict with message_count, export timestamp, and message list
        
    Status Codes:
        200: Successfully exported history
        404: Session not found
    """
    if session_id not in chat_histories:
        raise HTTPException(status_code=404, detail="session not found")
    
    history = chat_histories[session_id]
    return history.to_dict()


@app.get("/admin/sessions/active")
def active_sessions(
    x_admin_token: str | None = Header(default=None),
    limit: int = 200,
) -> dict:
    """
    Inspect in-memory sessions and their activity status (admin endpoint).

    Includes last access timestamp, active flag, and chat message count.

    Requires: x-admin-token header with correct admin token.
    Query params: limit (default 200) to cap returned session records.
    """
    _check_admin_token(x_admin_token)
    rows: list[dict[str, object]] = []
    for sid, last_access in list(session_mgr.sessions.items()):
        history = chat_histories.get(sid)
        rows.append(
            {
                "session_id": sid,
                "last_access": last_access.isoformat(),
                "is_active": session_mgr.is_active(sid),
                "has_agent": sid in sessions,
                "message_count": len(history.messages) if history else 0,
            }
        )

    rows.sort(key=lambda x: str(x["last_access"]), reverse=True)
    limited = rows[: max(0, limit)]

    return {
        "total": len(rows),
        "returned": len(limited),
        "sessions": limited,
    }


@app.post("/admin/sessions/cleanup")
def cleanup_sessions(
    x_admin_token: str | None = Header(default=None),
    dry_run: bool = False,
) -> dict:
    """
    Remove expired in-memory sessions (admin endpoint).

    Frees memory by evicting sessions that have exceeded their TTL (60 min idle).
    Database records (leads, appointments) are preserved.

    Query params:
    - dry_run: when true, only reports sessions that would be removed.

    Requires: x-admin-token header with correct admin token.
    Returns: Count of cleaned sessions and their IDs.
    """
    _check_admin_token(x_admin_token)

    if dry_run:
        now = datetime.now(UTC)
        expired_ids = [
            sid
            for sid, last_access in session_mgr.sessions.items()
            if now >= last_access + session_mgr.default_ttl
        ]
        return {
            "cleaned": len(expired_ids),
            "session_ids": expired_ids,
            "dry_run": True,
        }

    expired_ids = session_mgr.cleanup_expired()
    for sid in expired_ids:
        sessions.pop(sid, None)
        chat_histories.pop(sid, None)
    return {
        "cleaned": len(expired_ids),
        "session_ids": expired_ids,
        "dry_run": False,
    }


@app.get("/remind/{session_id}")
def appointment_reminder(session_id: str) -> dict:
    """
    Get a formatted appointment reminder for a session.

    Returns clinic details and the confirmed appointment slot so the
    frontend or notification service can display a reminder to the patient.

    Status Codes:
        200: Reminder returned successfully
        404: Session not found or no confirmed appointment yet
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="session not found")

    state = sessions[session_id].state
    agent = sessions[session_id]

    if not state.confirmed_slot:
        raise HTTPException(
            status_code=404,
            detail="no confirmed appointment found for this session"
        )

    return {
        "session_id": session_id,
        "patient_name": state.patient_name or "Patient",
        "appointment_slot": state.confirmed_slot,
        "clinic_name": "Maple Dental Clinic",
        "clinic_address": agent.ADDRESS,
        "clinic_phone": agent.PHONE,
        "clinic_hours": agent.HOURS,
        "reminder_message": (
            f"Reminder: your appointment at Maple Dental Clinic is confirmed for "
            f"{state.confirmed_slot}. Please arrive 10 minutes early and bring "
            "your photo ID and insurance card."
        ),
    }


@app.get("/session/{session_id}/summary")
def session_summary(session_id: str) -> dict:
    """
    Return a structured summary of the current session state.

    Includes patient name, symptom report, appointment status, last intent
    with confidence score, and message count from chat history.

    Status Codes:
        200: Summary returned successfully
        404: Session not found
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="session not found")

    state = sessions[session_id].state
    history = chat_histories.get(session_id)

    return {
        "session_id": session_id,
        "patient_name": state.patient_name,
        "contact": state.contact,
        "symptoms": state.symptom_summary(),
        "appointment_requested": state.appointment_requested,
        "confirmed_slot": state.confirmed_slot,
        "last_intent": state.last_intent,
        "last_confidence": state.last_confidence,
        "message_count": len(history.messages) if history else 0,
    }
