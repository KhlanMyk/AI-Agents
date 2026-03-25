from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List
import re


@dataclass
class ChatState:
    patient_name: str | None = None
    symptoms: List[str] = field(default_factory=list)
    appointment_requested: bool = False
    last_intent: str | None = None


class DentistAIAgent:
    """A basic rule-based dentist chatbot agent.

    """

    SERVICES: Dict[str, str] = {
        "cleaning": "$80 - basic dental cleaning",
        "whitening": "$180 - take-home kit included",
        "filling": "$120+ depending on cavity size",
        "root canal": "$550+ depending on tooth",
        "checkup": "$60 - consultation and exam",
    }

    HOURS = "Mon-Fri 09:00-18:00, Sat 10:00-14:00, Sun closed"

    INSURANCE_TEXT = (
        "We accept most major insurance plans. "
        "Please bring your insurance card, photo ID, and previous dental records if available."
    )

    EMERGENCY_KEYWORDS = {
        "bleeding",
        "swelling",
        "trauma",
        "knocked out",
        "severe pain",
        "fever",
        "abscess",
        "pus",
    }

    def __init__(self) -> None:
        self.state = ChatState()

    def _extract_name(self, text: str) -> str | None:
        # Handles: "my name is Anna", "I am Anna", "I'm Anna"
        patterns = [
            r"my name is\s+([A-Za-z][A-Za-z\-']+)",
            r"i am\s+([A-Za-z][A-Za-z\-']+)",
            r"i'm\s+([A-Za-z][A-Za-z\-']+)",
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                return m.group(1).strip().title()
        return None

    def _detect_emergency(self, text: str) -> bool:
        lowered = text.lower()
        return any(keyword in lowered for keyword in self.EMERGENCY_KEYWORDS)

    def _next_available_slot(self) -> str:
        dt = datetime.now() + timedelta(days=1)
        # simple deterministic slot at 11:00 tomorrow
        slot = dt.replace(hour=11, minute=0, second=0, microsecond=0)
        return slot.strftime("%A, %d %b at %H:%M")

    def _intent(self, text: str) -> str:
        lowered = text.lower()

        if self._detect_emergency(lowered):
            return "emergency"
        if "help" in lowered:
            return "help"
        if any(word in lowered for word in ["book", "appointment", "schedule", "visit"]):
            return "appointment"
        if any(word in lowered for word in ["price", "cost", "how much", "fee"]):
            return "pricing"
        if any(word in lowered for word in ["hour", "open", "close", "working time"]):
            return "hours"
        if "insurance" in lowered:
            return "insurance"
        if any(word in lowered for word in ["service", "offer", "do you have", "treatment"]):
            return "services"
        if any(word in lowered for word in ["toothache", "pain", "sensitive", "gum"]):
            return "symptom"
        if any(word in lowered for word in ["hello", "hi", "hey"]):
            return "greeting"
        return "fallback"

    def respond(self, message: str) -> str:
        if not message.strip():
            return "Please type a message so I can help you."

        lowered_message = message.lower()

        if "confirm appointment" in lowered_message:
            if self.state.appointment_requested:
                slot = self._next_available_slot()
                self.state.appointment_requested = False
                return f"Great! Your appointment is confirmed for {slot}. Please arrive 10 minutes early."
            return "I can help with that—please ask to book an appointment first."

        if "cancel appointment" in lowered_message:
            if self.state.appointment_requested:
                self.state.appointment_requested = False
                return "Your appointment request has been cancelled. Let me know if you need anything else."
            return "You don't have a pending appointment to cancel."

        name = self._extract_name(message)
        if name:
            self.state.patient_name = name

        intent = self._intent(message)
        self.state.last_intent = intent

        user = self.state.patient_name or "there"

        if intent == "greeting":
            return (
                f"Hi {user}! 🦷 I'm your dentist assistant bot. "
                "I can help with appointments, prices, services, and basic dental advice. "
                "Type 'help' to see all options."
            )

        if intent == "emergency":
            return (
                "This may be a dental emergency. Please call emergency dental care immediately. "
                "If you have severe swelling, bleeding, or fever, seek urgent in-person care now."
            )

        if intent == "appointment":
            self.state.appointment_requested = True
            slot = self._next_available_slot()
            return (
                f"Sure, {user}. I can offer the next available slot: {slot}. "
                "Reply with 'confirm appointment' to book it."
            )

        if intent == "pricing":
            services = "\n".join([f"- {name.title()}: {price}" for name, price in self.SERVICES.items()])
            return f"Here is our price guide:\n{services}"

        if intent == "hours":
            return f"Our clinic hours are: {self.HOURS}."

        if intent == "insurance":
            return self.INSURANCE_TEXT

        if intent == "services":
            items = ", ".join(s.title() for s in self.SERVICES.keys())
            return f"We currently offer: {items}."

        if intent == "symptom":
            return (
                "For mild tooth pain: rinse with warm salt water, avoid very hot/cold food, "
                "and use over-the-counter pain relief if safe for you. "
                "If pain lasts more than 24-48 hours, book an exam."
            )

        if intent == "help":
            return (
                "You can ask me about appointments, prices, services, clinic hours, insurance, "
                "or symptoms like tooth pain."
            )

        return (
            "I didn't fully catch that. You can ask me about: appointments, prices, services, hours, "
            "insurance, or tooth pain."
        )


def run_chat() -> None:
    agent = DentistAIAgent()
    print("Dentist AI Agent is ready. Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit", "bye"}:
            print("Bot: Thanks for chatting. Take care of your smile! 😄")
            break

        reply = agent.respond(user_input)
        print(f"Bot: {reply}\n")


if __name__ == "__main__":
    run_chat()
