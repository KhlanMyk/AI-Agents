from __future__ import annotations

from typing import List

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Appointment, ChatLead


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
        return lead


def list_leads(limit: int = 100) -> List[ChatLead]:
    with SessionLocal() as db:
        rows = db.execute(select(ChatLead).order_by(ChatLead.id.desc()).limit(limit)).scalars().all()
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
        return item


def list_appointments(limit: int = 100) -> List[Appointment]:
    with SessionLocal() as db:
        rows = db.execute(select(Appointment).order_by(Appointment.id.desc()).limit(limit)).scalars().all()
        return list(rows)
