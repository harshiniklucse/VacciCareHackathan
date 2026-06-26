import os
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import anthropic

app = FastAPI(title="VacciCare Reminder Composer", version="1.0")
_client: Optional[anthropic.Anthropic] = None

# Pre-registered DLT template IDs (MSG91 requires government-approved templates)
DLT_TEMPLATES = {
    "en": "VACCICARE_EN_REMINDER_001",
    "ta": "VACCICARE_TA_REMINDER_001",
    "hi": "VACCICARE_HI_REMINDER_001",
}


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


class ReminderRequest(BaseModel):
    child_id: str
    child_name: str
    parent_name: str
    vaccine_name: str
    due_date: str  # YYYY-MM-DD
    clinic_name: str
    clinic_address: str
    language: str  # en / ta / hi
    reminder_number: int = 1  # 1st, 2nd, or 3rd reminder


LANGUAGE_NAMES = {"en": "English", "ta": "Tamil", "hi": "Hindi"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "reminder-composer"}


@app.post("/compose")
def compose_reminder(req: ReminderRequest):
    lang_name = LANGUAGE_NAMES.get(req.language, "English")
    urgency = "gentle" if req.reminder_number == 1 else ("firm" if req.reminder_number == 2 else "urgent")

    prompt = f"""Compose a WhatsApp vaccination reminder message in {lang_name} for the following:

Child: {req.child_name}
Parent: {req.parent_name}
Vaccine due: {req.vaccine_name}
Due date: {req.due_date}
Clinic: {req.clinic_name}, {req.clinic_address}
Reminder number: {req.reminder_number} (tone should be {urgency})

Rules:
- Maximum 160 characters (SMS/WhatsApp limit for DLT compliance)
- Include child name, vaccine name, due date, and clinic name
- Use respectful address (Respected {req.parent_name} / மதிப்பிற்குரிய / आदरणीय)
- End with a call to action
- If Tamil or Hindi, use proper Unicode script (not romanized)
- Do NOT include URLs or phone numbers

Respond ONLY as JSON:
{{"MessageBody": "the message text", "CharCount": number}}"""

    message = get_client().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )

    import json
    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    result = json.loads(raw.strip())
    result["ChildID"] = req.child_id
    result["Language"] = req.language
    result["DLTTemplateID"] = DLT_TEMPLATES.get(req.language, DLT_TEMPLATES["en"])
    return result
