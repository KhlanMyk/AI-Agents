from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List
import random
import re


@dataclass
class ChatState:
    patient_name: str | None = None
    symptoms: List[str] = field(default_factory=list)
    appointment_requested: bool = False
    offered_slots: List[str] = field(default_factory=list)
    confirmed_slot: str | None = None
    last_intent: str | None = None
    last_confidence: float | None = None
    last_suggestions: List[str] = field(default_factory=list)

    def add_symptom(self, symptom: str) -> None:
        """Add symptom if not already recorded (deduplicates)."""
        if symptom not in self.symptoms:
            self.symptoms.append(symptom)

    def symptom_summary(self) -> dict:
        """Return a structured symptom summary for reporting."""
        return {
            "count": len(self.symptoms),
            "symptoms": list(self.symptoms),
            "has_symptoms": len(self.symptoms) > 0,
        }


class DentistAIAgent:
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
    PROMO = "New patients get 20% off their first cleaning. Ask us for details!"
    TEAM = "Our team includes Dr. Sarah Chen (general dentistry), Dr. James Rodriguez (orthodontics), and 4 other experienced specialists."
    ABOUT = (
        "Maple Dental Clinic was founded in 2010. "
        "We have a team of 6 experienced dentists and offer a full range of dental services "
        "in a comfortable, modern environment."
    )

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
        "cracked",
        "broken",
        "loose",
        "cavity",
        "abscess",
        "sore",
        "ache",
    }

    def __init__(self) -> None:
        self.state = ChatState()

    def reset(self) -> None:
        self.state = ChatState()

    def _extract_name(self, text: str) -> str | None:
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
        slot = dt.replace(hour=11, minute=0, second=0, microsecond=0)
        return slot.strftime("%A, %d %b at %H:%M")

    def _available_slots(self) -> List[str]:
        base = datetime.now() + timedelta(days=1)
        slot1 = base.replace(hour=11, minute=0, second=0, microsecond=0)
        slot2 = base.replace(hour=15, minute=0, second=0, microsecond=0)
        fmt = "%A, %d %b at %H:%M"
        return [slot1.strftime(fmt), slot2.strftime(fmt)]

    # Maps intent name → (trigger_words, confidence)
    # Higher confidence = stronger signal (unambiguous keywords)
    _INTENT_MAP: List[tuple] = [
        ("emergency",  [],                                                           1.00),
        ("goodbye",    ["bye", "goodbye", "see you"],                               0.95),
        ("tip",        ["tip", "advice", "recommend"],                              0.88),
        ("faq",        ["referral", "long is", "how long", "first visit", "x-ray", "faq"], 0.90),
        ("gratitude",  ["thanks", "thank you", "thx"],                              0.95),
        ("summary",    ["summary", "status"],                                        0.92),
        ("help",       ["help"],                                                      0.85),
        ("prepare",    ["prepare", "bring", "what to", "before appointment"],        0.88),
        ("appointment",["book", "appointment", "schedule", "visit"],                0.92),
        ("waitlist",   ["waitlist"],                                                  0.90),
        ("about",      ["about", "clinic", "who are you", "tell me about"],          0.85),
        ("feedback",   ["feedback", "review", "rate", "rating"],                    0.88),
        ("pricing",    ["price", "cost", "how much", "fee"],                         0.92),
        ("hours",      ["hour", "open", "close", "working time"],                   0.90),
        ("weekend",    ["weekend", "saturday", "sunday"],                            0.92),
        ("reminder",   ["reminder", "don't forget", "reminder for"],                0.88),
        ("promo",      ["promo", "discount", "deal", "special"],                    0.88),
        ("team",       ["staff", "team", "dentist", "doctor"],                      0.85),
        ("payment",    ["payment", "pay", "card", "cash"],                          0.88),
        ("parking",    ["parking"],                                                   0.90),
        ("kids",       ["kid", "child", "children", "pediatric"],                   0.90),
        ("contact",    ["phone", "contact", "call", "number"],                      0.88),
        ("location",   ["address", "location", "where", "find you"],                0.88),
        ("insurance",  ["insurance"],                                                 0.92),
        ("services",   ["service", "offer", "do you have", "treatment"],            0.85),
        ("symptom",    ["toothache", "pain", "sensitive", "gum"],                   0.85),
        ("greeting",   ["hello", "hi", "hey"],                                       0.80),
    ]

    def _intent_with_confidence(self, text: str) -> tuple[str, float]:
        """Detect intent and return (intent_name, confidence 0.0–1.0)."""
        lowered = text.lower()

        if self._detect_emergency(lowered):
            return "emergency", 1.00

        for intent_name, keywords, confidence in self._INTENT_MAP:
            if intent_name == "emergency":
                continue
            if any(word in lowered for word in keywords):
                # Boost confidence if multiple keywords match
                matched = sum(1 for w in keywords if w in lowered)
                boosted = min(1.0, confidence + 0.03 * (matched - 1))
                return intent_name, round(boosted, 2)

        return "fallback", 0.30

    def _intent(self, text: str) -> str:
        intent, _ = self._intent_with_confidence(text)
        return intent

    def _suggest_topics(self, text: str, top_n: int = 3) -> List[str]:
        """
        For a fallback message, compute keyword-overlap scores and return
        the top_n most likely topic names to guide the user.
        """
        lowered = text.lower()
        words = set(re.split(r'\W+', lowered))
        scores: Dict[str, int] = {}
        for intent_name, keywords, _ in self._INTENT_MAP:
            if intent_name in ("emergency", "fallback"):
                continue
            score = sum(
                1
                for kw in keywords
                if any(w in kw or kw in w for w in words if len(w) >= 3)
            )
            if score > 0:
                scores[intent_name] = score

        # Sort by score descending, return top_n names
        ranked = sorted(scores, key=lambda k: scores[k], reverse=True)
        return ranked[:top_n] if ranked else ["appointments", "pricing", "services"]

    def respond(self, message: str) -> str:
        clean_message = message.strip()
        if not clean_message:
            return "Please type a message so I can help you."

        lowered_message = clean_message.lower()

        for symptom in self.SYMPTOM_KEYWORDS:
            if symptom in lowered_message:
                self.state.add_symptom(symptom)

        if "confirm appointment" in lowered_message:
            if self.state.appointment_requested:
                slot = self.state.offered_slots[0] if self.state.offered_slots else self._next_available_slot()
                self.state.appointment_requested = False
                self.state.confirmed_slot = slot
                self.state.offered_slots = []
                return f"Great! Your appointment is confirmed for {slot}. Please arrive 10 minutes early."
            return "I can help with that—please ask to book an appointment first."

        if lowered_message in {"reset", "clear chat"}:
            self.reset()
            return "Chat state cleared. We can start fresh."

        name = self._extract_name(clean_message)
        if name:
            self.state.patient_name = name

        intent, confidence = self._intent_with_confidence(clean_message)
        self.state.last_intent = intent
        self.state.last_confidence = confidence
        self.state.last_suggestions = []
        user = self.state.patient_name or "there"

        if intent == "greeting":
            return (
                f"Hi {user}! 🦷 I'm your dentist assistant bot. "
                "I can help with appointments, prices, services, and basic dental advice. "
                "Type 'help' to see all options."
            )
        if intent == "appointment":
            self.state.appointment_requested = True
            slots = self._available_slots()
            self.state.offered_slots = slots
            return (
                f"Sure, {user}. Available slots: 1) {slots[0]}  2) {slots[1]}. "
                "Reply with 'confirm appointment' for slot 1 or type '2' for slot 2."
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
        if intent == "weekend":
            return "We are open on Saturday from 10:00 to 14:00 and closed on Sunday."
        if intent == "payment":
            return f"We accept {self.PAYMENT_METHODS}."
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
            return "Common questions: no referral needed, checkup ~45 min, X-rays once a year."
        if intent == "gratitude":
            return "You're welcome! Happy to help with your dental questions anytime."
        if intent == "goodbye":
            return "Goodbye! If you need help later, just message me again."
        if intent == "help":
            return (
                "You can ask me about appointments, prices, services, clinic hours, insurance, "
                "payment, location, and symptoms like tooth pain."
            )
        if intent == "waitlist":
            return "I can add you to the waitlist. Please share preferred day/time window."
        if intent == "about":
            return self.ABOUT
        if intent == "feedback":
            return "You can leave a review on Google Maps or call us at " + self.PHONE + "."
        if intent == "prepare":
            return "Please bring photo ID, insurance card, and arrive 10 minutes early."
        if intent == "promo":
            return self.PROMO
        if intent == "team":
            return self.TEAM
        if intent == "parking":
            return "Street parking is available nearby and a paid garage is one block away."
        if intent == "kids":
            return "Yes, we see children ages 5+ for checkups, cleanings, and basic treatments."
        if intent == "summary":
            name_text = self.state.patient_name or "unknown"
            symptoms_text = ", ".join(self.state.symptoms) if self.state.symptoms else "none"
            pending = "yes" if self.state.appointment_requested else "no"
            return f"Patient: {name_text}. Pending appointment: {pending}. Discussed symptoms: {symptoms_text}."
        if intent == "emergency":
            return (
                "This may be a dental emergency. If you have severe swelling, bleeding, or fever, "
                "seek urgent in-person care now."
            )

        # Fallback: suggest relevant topics based on partial keyword match
        suggestions = self._suggest_topics(clean_message)
        self.state.last_suggestions = suggestions
        hint = ", ".join(suggestions)
        return (
            f"I didn't fully catch that. Based on your message, you might be asking about: {hint}. "
            "Type 'help' to see all available topics."
        )
