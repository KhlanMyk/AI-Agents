from __future__ import annotations

from typing import Dict, List, Optional

from sqlalchemy import func, select

from app.cache import cache_with_ttl, invalidate_cache
from app.db import SessionLocal
from app.models import Appointment, ChatLead


LEADS_CACHE_NAMESPACE = "leads"
APPOINTMENTS_CACHE_NAMESPACE = "appointments"


def save_lead(session_id: str, name: str, contact: str, message: str, intent: str) -> ChatLead:
    with SessionLocal() as db:
        lead = ChatLead(
            session_id=session_id,
            name=name,
            contact=contact,
            message=message,
            intent=intent,
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)
    invalidate_cache(LEADS_CACHE_NAMESPACE)
    return lead


@cache_with_ttl(ttl_seconds=30, namespace=LEADS_CACHE_NAMESPACE)
def list_leads(limit: int = 100, offset: int = 0) -> List[ChatLead]:
    with SessionLocal() as db:
        rows = db.execute(
            select(ChatLead)
            .order_by(ChatLead.id.desc())
            .limit(limit)
            .offset(offset)
        ).scalars().all()
        return list(rows)


@cache_with_ttl(ttl_seconds=30, namespace=LEADS_CACHE_NAMESPACE)
def search_leads(intent: Optional[str] = None, name: Optional[str] = None, limit: int = 100) -> List[ChatLead]:
    """Filter leads by intent and/or name (case-insensitive partial match)."""
    with SessionLocal() as db:
        stmt = select(ChatLead).order_by(ChatLead.id.desc())
        if intent:
            stmt = stmt.where(ChatLead.intent == intent)
        if name:
            stmt = stmt.where(ChatLead.name.ilike(f"%{name}%"))
        rows = db.execute(stmt.limit(limit)).scalars().all()
        return list(rows)


def create_appointment(session_id: str, patient_name: str, slot: str, notes: str = "") -> Appointment:
    with SessionLocal() as db:
        item = Appointment(
            session_id=session_id,
            patient_name=patient_name,
            slot=slot,
            notes=notes,
            status="confirmed",
        )
        db.add(item)
        db.commit()
        db.refresh(item)
    invalidate_cache(APPOINTMENTS_CACHE_NAMESPACE)
    return item


@cache_with_ttl(ttl_seconds=30, namespace=APPOINTMENTS_CACHE_NAMESPACE)
def list_appointments(limit: int = 100, offset: int = 0) -> List[Appointment]:
    with SessionLocal() as db:
        rows = db.execute(
            select(Appointment)
            .order_by(Appointment.id.desc())
            .limit(limit)
            .offset(offset)
        ).scalars().all()
        return list(rows)


def count_leads() -> int:
    """Return total number of leads in the database."""
    with SessionLocal() as db:
        return db.execute(select(func.count()).select_from(ChatLead)).scalar_one()


def count_appointments() -> int:
    """Return total number of appointments in the database."""
    with SessionLocal() as db:
        return db.execute(select(func.count()).select_from(Appointment)).scalar_one()


@cache_with_ttl(ttl_seconds=30, namespace=LEADS_CACHE_NAMESPACE)
def count_leads_by_intent() -> Dict[str, int]:
    """Return grouped lead counts by intent."""
    with SessionLocal() as db:
        rows = db.execute(
            select(ChatLead.intent, func.count(ChatLead.id))
            .group_by(ChatLead.intent)
        ).all()
    return {intent: int(count) for intent, count in rows}


@cache_with_ttl(ttl_seconds=30, namespace=APPOINTMENTS_CACHE_NAMESPACE)
def count_appointments_by_status() -> Dict[str, int]:
    """Return grouped appointment counts by status."""
    with SessionLocal() as db:
        rows = db.execute(
            select(Appointment.status, func.count(Appointment.id))
            .group_by(Appointment.status)
        ).all()
    return {status: int(count) for status, count in rows}


def update_appointment_status(appointment_id: int, new_status: str) -> Optional[Appointment]:
    """Update the status of an appointment. Returns updated record or None if not found."""
    allowed = {"confirmed", "cancelled", "no_show", "pending"}
    if new_status not in allowed:
        raise ValueError(f"status must be one of: {', '.join(sorted(allowed))}")
    with SessionLocal() as db:
        appt = db.get(Appointment, appointment_id)
        if appt is None:
            return None
        appt.status = new_status
        db.commit()
        db.refresh(appt)
    invalidate_cache(APPOINTMENTS_CACHE_NAMESPACE)
    return appt


def get_lead_by_id(lead_id: int) -> Optional[ChatLead]:
    """Fetch a single lead by primary key. Returns None if not found."""
    with SessionLocal() as db:
        return db.get(ChatLead, lead_id)


def get_appointment_by_id(appointment_id: int) -> Optional[Appointment]:
    """Fetch a single appointment by primary key. Returns None if not found."""
    with SessionLocal() as db:
        return db.get(Appointment, appointment_id)
