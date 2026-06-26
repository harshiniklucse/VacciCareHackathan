import os
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import anthropic

app = FastAPI(title="VacciCare Migration Agent", version="1.0")
_client: Optional[anthropic.Anthropic] = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


class MigrationRequest(BaseModel):
    child_id: str
    original_district: str
    whatsapp_message: str  # free-text reply from parent, may be Tamil/Hindi/English
    original_clinic_code: str


@app.get("/health")
def health():
    return {"status": "ok", "service": "migration-agent"}


@app.post("/detect-migration")
def detect_migration(req: MigrationRequest):
    prompt = f"""You are analyzing a WhatsApp message from a parent whose child is enrolled in a vaccination programme in {req.original_district}, Tamil Nadu, India.

Parent message: "{req.whatsapp_message}"

Tasks:
1. Detect if the parent has moved or is living in a different location from {req.original_district}.
2. If moved, extract the new city/district/village name (in English).
3. Estimate confidence (0.0–1.0) that a migration has occurred.
4. Suggest the nearest government clinic type (PHC / CHC / District Hospital).

Respond ONLY as valid JSON with these keys:
{{
  "migration_detected": true/false,
  "new_location": "city or district name or null",
  "confidence": 0.0-1.0,
  "suggested_clinic_type": "PHC/CHC/District Hospital/null",
  "summary": "one sentence English summary"
}}"""

    message = get_client().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )

    import json
    raw = message.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    result = json.loads(raw.strip())
    result["ChildID"] = req.child_id
    result["OriginalDistrict"] = req.original_district
    return result
