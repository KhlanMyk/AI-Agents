from __future__ import annotations

from datetime import timedelta
from typing import Dict, List, Optional

from sqlalchemy import delete, func, select

from app.cache import cache_with_ttl, invalidate_cache
from app.db import SessionLocal
from app.models import Appointment, ChatLead
from app.time_utils import utc_now


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


@cache_with_ttl(ttl_seconds=30, namespace=APPOINTMENTS_CACHE_NAMESPACE)
def search_appointments(
    session_id: Optional[str] = None,
    status: Optional[str] = None,
    patient_name: Optional[str] = None,
    slot: Optional[str] = None,
    limit: int = 100,
) -> List[Appointment]:
    """Filter appointments by status and/or patient/slot text."""
    with SessionLocal() as db:
        stmt = select(Appointment).order_by(Appointment.id.desc())
        if session_id:
            stmt = stmt.where(Appointment.session_id == session_id)
        if status:
            stmt = stmt.where(Appointment.status == status)
        if patient_name:
            stmt = stmt.where(Appointment.patient_name.ilike(f"%{patient_name}%"))
        if slot:
            stmt = stmt.where(Appointment.slot.ilike(f"%{slot}%"))
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


@cache_with_ttl(ttl_seconds=30, namespace=LEADS_CACHE_NAMESPACE)
def leads_daily_trend(days: int = 7) -> List[Dict[str, int | str]]:
    """Return daily lead counts for the requested trailing day window."""
    cutoff = utc_now() - timedelta(days=max(1, days) - 1)
    with SessionLocal() as db:
        rows = db.execute(
            select(
                func.date(ChatLead.created_at).label("day"),
                func.count(ChatLead.id).label("count"),
            )
            .where(ChatLead.created_at >= cutoff)
            .group_by(func.date(ChatLead.created_at))
            .order_by(func.date(ChatLead.created_at))
        ).all()
    return [{"date": str(day), "count": int(count)} for day, count in rows]


@cache_with_ttl(ttl_seconds=30, namespace=APPOINTMENTS_CACHE_NAMESPACE)
def appointments_daily_trend(days: int = 7) -> List[Dict[str, int | str]]:
    """Return daily appointment counts for the requested trailing day window."""
    cutoff = utc_now() - timedelta(days=max(1, days) - 1)
    with SessionLocal() as db:
        rows = db.execute(
            select(
                func.date(Appointment.created_at).label("day"),
                func.count(Appointment.id).label("count"),
            )
            .where(Appointment.created_at >= cutoff)
            .group_by(func.date(Appointment.created_at))
            .order_by(func.date(Appointment.created_at))
        ).all()
    return [{"date": str(day), "count": int(count)} for day, count in rows]


def cleanup_old_records(days: int = 90, dry_run: bool = True) -> Dict[str, int | bool]:
    """
    Remove records older than the specified number of days.

    Args:
        days: retention window in days (records older than this are candidates)
        dry_run: when True, only report candidate counts without deleting

    Returns:
        Summary containing candidate/deleted counts for leads and appointments.
    """
    cutoff = utc_now() - timedelta(days=max(1, days))

    with SessionLocal() as db:
        leads_candidates = db.execute(
            select(func.count()).select_from(ChatLead).where(ChatLead.created_at < cutoff)
        ).scalar_one()
        appointments_candidates = db.execute(
            select(func.count()).select_from(Appointment).where(Appointment.created_at < cutoff)
        ).scalar_one()

        if dry_run:
            return {
                "dry_run": True,
                "leads_candidates": int(leads_candidates),
                "appointments_candidates": int(appointments_candidates),
                "leads_deleted": 0,
                "appointments_deleted": 0,
            }

        leads_result = db.execute(delete(ChatLead).where(ChatLead.created_at < cutoff))
        appts_result = db.execute(delete(Appointment).where(Appointment.created_at < cutoff))
        db.commit()

    invalidate_cache(LEADS_CACHE_NAMESPACE)
    invalidate_cache(APPOINTMENTS_CACHE_NAMESPACE)

    return {
        "dry_run": False,
        "leads_candidates": int(leads_candidates),
        "appointments_candidates": int(appointments_candidates),
        "leads_deleted": int(leads_result.rowcount or 0),
        "appointments_deleted": int(appts_result.rowcount or 0),
    }


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
