from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List
import re
import random


@dataclass
class ChatState:
    patient_name: str | None = None
    symptoms: List[str] = field(default_factory=list)
    appointment_requested: bool = False
    offered_slots: List[str] = field(default_factory=list)
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
    ADDRESS = "123 Maple Street, Suite 4, New York, NY 10001"
    PHONE = "+1 (212) 555-0198"
    PAYMENT_METHODS = "cash, credit/debit cards, Apple Pay, and Google Pay"

    INSURANCE_TEXT = (
        "We accept most major insurance plans. "
        "Please bring your insurance card, photo ID, and previous dental records if available."
    )

    TIPS: List[str] = [
        "Brush for at least 2 minutes twice a day.",
        "Floss daily to prevent gum disease.",
        "Replace your toothbrush every 3 months.",
        "Limit sugary drinks — they cause enamel erosion.",
        "Use a fluoride toothpaste for stronger enamel.",
        "Drink plenty of water — it helps wash away food particles.",
    ]

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

    SYMPTOM_KEYWORDS = {
        "toothache",
        "pain",
        "sensitive",
        "gum",
        "swelling",
        "bleeding",
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

    def _available_slots(self) -> List[str]:
        base = datetime.now() + timedelta(days=1)
        slot1 = base.replace(hour=11, minute=0, second=0, microsecond=0)
        slot2 = base.replace(hour=15, minute=0, second=0, microsecond=0)
        fmt = "%A, %d %b at %H:%M"
        return [slot1.strftime(fmt), slot2.strftime(fmt)]

    def _intent(self, text: str) -> str:
        lowered = text.lower()

        if self._detect_emergency(lowered):
            return "emergency"
        if any(word in lowered for word in ["bye", "goodbye", "see you"]):
            return "goodbye"
        if any(word in lowered for word in ["tip", "advice", "recommend"]):
            return "tip"
        if any(word in lowered for word in ["referral", "long is", "how long", "first visit", "x-ray", "faq"]):
            return "faq"
        if any(word in lowered for word in ["thanks", "thank you", "thx"]):
            return "gratitude"
        if any(word in lowered for word in ["summary", "status"]):
            return "summary"
        if "help" in lowered:
            return "help"
        if any(word in lowered for word in ["book", "appointment", "schedule", "visit"]):
            return "appointment"
        if "waitlist" in lowered:
            return "waitlist"
        if any(word in lowered for word in ["price", "cost", "how much", "fee"]):
            return "pricing"
        if any(word in lowered for word in ["hour", "open", "close", "working time"]):
            return "hours"
        if any(word in lowered for word in ["payment", "pay", "card", "cash"]):
            return "payment"
        if any(word in lowered for word in ["kid", "child", "children", "pediatric"]):
            return "kids"
        if any(word in lowered for word in ["phone", "contact", "call", "number"]):
            return "contact"
        if any(word in lowered for word in ["address", "location", "where", "find you"]):
            return "location"
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
        clean_message = message.strip()
        if not clean_message:
            return "Please type a message so I can help you."

        lowered_message = clean_message.lower()

        for symptom in self.SYMPTOM_KEYWORDS:
            if symptom in lowered_message and symptom not in self.state.symptoms:
                self.state.symptoms.append(symptom)

        if "confirm appointment" in lowered_message:
            if self.state.appointment_requested:
                slot = self.state.offered_slots[0] if self.state.offered_slots else self._next_available_slot()
                self.state.appointment_requested = False
                self.state.offered_slots = []
                return f"Great! Your appointment is confirmed for {slot}. Please arrive 10 minutes early."
            return "I can help with that—please ask to book an appointment first."

        if "cancel appointment" in lowered_message:
            if self.state.appointment_requested:
                self.state.appointment_requested = False
                self.state.offered_slots = []
                return "Your appointment request has been cancelled. Let me know if you need anything else."
            return "You don't have a pending appointment to cancel."

        if lowered_message in {"2", "slot 2", "second slot"} and self.state.appointment_requested:
            if len(self.state.offered_slots) > 1:
                slot = self.state.offered_slots[1]
                self.state.appointment_requested = False
                self.state.offered_slots = []
                return f"Done! Your appointment is confirmed for {slot}. Please arrive 10 minutes early."
            return "I only have one slot available right now."

        if lowered_message in {"yes", "y"} and self.state.appointment_requested:
            slot = self.state.offered_slots[0] if self.state.offered_slots else self._next_available_slot()
            self.state.appointment_requested = False
            self.state.offered_slots = []
            return f"Great! Your appointment is confirmed for {slot}. Please arrive 10 minutes early."

        if lowered_message in {"no", "n"} and self.state.appointment_requested:
            self.state.appointment_requested = False
            self.state.offered_slots = []
            return "No problem. I cancelled the pending appointment request."

        if lowered_message in {"reset", "clear chat"}:
            self.state = ChatState()
            return "Chat state cleared. We can start fresh."

        name = self._extract_name(clean_message)
        if name:
            self.state.patient_name = name

        intent = self._intent(clean_message)
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
            slots = self._available_slots()
            self.state.offered_slots = slots
            return (
                f"Sure, {user}. Available slots: 1) {slots[0]}  2) {slots[1]}. "
                "Reply with 'confirm appointment' for slot 1 or type '2' for slot 2."
            )

        if intent == "waitlist":
            return (
                "Got it. I can add you to the waitlist and notify you if an earlier slot opens up. "
                "Please share your preferred day and time window."
            )

        if intent == "pricing":
            lowered = clean_message.lower()
            for service_name, service_price in self.SERVICES.items():
                if service_name in lowered:
                    return f"{service_name.title()} costs {service_price}."
            services = "\n".join([f"- {name.title()}: {price}" for name, price in self.SERVICES.items()])
            return f"Here is our price guide:\n{services}"

        if intent == "hours":
            return f"Our clinic hours are: {self.HOURS}."

        if intent == "payment":
            return f"We accept {self.PAYMENT_METHODS}."

        if intent == "kids":
            return "Yes, we see children ages 5+ for checkups, cleanings, and basic treatments."

        if intent == "contact":
            return f"You can call us at {self.PHONE} or visit us at {self.ADDRESS}."

        if intent == "location":
            return f"You can find us at: {self.ADDRESS}. We are open {self.HOURS}."

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

        if intent == "tip":
            return "💡 Dental tip: " + random.choice(self.TIPS)

        if intent == "faq":
            lowered = clean_message.lower()
            if "referral" in lowered:
                return "No referral is needed. You can book directly."
            if "how long" in lowered or "long is" in lowered:
                return "A standard checkup takes about 45-60 minutes. Procedures may take longer."
            if "x-ray" in lowered:
                return "We take X-rays on your first visit and then as needed, usually once a year."
            if "first visit" in lowered:
                return "On your first visit please bring photo ID, insurance card, and any previous dental records."
            return "Common questions: no referral needed, checkup ~45 min, X-rays once a year."

        if intent == "gratitude":
            return "You're welcome! Happy to help with your dental questions anytime."

        if intent == "goodbye":
            return "Goodbye! If you need help later, just message me again."

        if intent == "help":
            return (
                "You can ask me about appointments (book/confirm/cancel), prices, services, "
                "clinic hours, insurance, payment, kids visits, location, contact number, "
                "or symptoms like tooth pain."
            )

        if intent == "summary":
            name_text = self.state.patient_name or "unknown"
            symptoms_text = ", ".join(self.state.symptoms) if self.state.symptoms else "none"
            pending = "yes" if self.state.appointment_requested else "no"
            return (
                f"Patient: {name_text}. Pending appointment: {pending}. "
                f"Discussed symptoms: {symptoms_text}."
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
