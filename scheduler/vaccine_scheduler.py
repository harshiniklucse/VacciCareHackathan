from fastapi import FastAPI
from pydantic import BaseModel
from datetime import date, timedelta
from typing import Optional
import math

app = FastAPI(title="VacciCare Schedule Builder", version="1.0")


class ScheduleRequest(BaseModel):
    child_id: str
    dob: str  # YYYY-MM-DD
    birth_weight_grams: Optional[int] = 2500
    gestation_weeks: Optional[int] = 40


# IAP 2024 schedule: (vaccine_name, weeks_from_birth, dose_number)
IAP_SCHEDULE = [
    ("BCG",         0,   1),
    ("OPV0",        0,   1),
    ("Hep-B",       0,   1),
    ("OPV1",        6,   1),
    ("DTwP1",       6,   1),
    ("IPV1",        6,   1),
    ("HiB1",        6,   1),
    ("Hep-B2",      6,   2),
    ("PCV1",        6,   1),
    ("Rota1",       6,   1),
    ("OPV2",        10,  2),
    ("DTwP2",       10,  2),
    ("IPV2",        10,  2),
    ("HiB2",        10,  2),
    ("PCV2",        10,  2),
    ("Rota2",       10,  2),
    ("OPV3",        14,  3),
    ("DTwP3",       14,  3),
    ("IPV3",        14,  3),
    ("HiB3",        14,  3),
    ("Hep-B3",      14,  3),
    ("PCV3",        14,  3),
    ("Measles1",    36,  1),
    ("MMR1",        52,  1),
    ("DTP-B1",      72,  1),
    ("OPV-B1",      72,  1),
    ("MMR2",        78,  2),
    ("Typhoid",     104, 1),
]


def corrected_dob(dob: date, gestation_weeks: int) -> date:
    """Adjust birth date for premature babies (< 37 weeks)."""
    if gestation_weeks >= 37:
        return dob
    deficit_weeks = 37 - gestation_weeks
    return dob + timedelta(weeks=deficit_weeks)


@app.get("/health")
def health():
    return {"status": "ok", "service": "schedule-builder"}


@app.post("/schedule")
def generate_schedule(req: ScheduleRequest):
    dob = date.fromisoformat(req.dob)
    ref_date = corrected_dob(dob, req.gestation_weeks or 40)
    today = date.today()

    schedule = []
    next_due = None
    next_vaccine = None

    for vaccine, weeks, dose in IAP_SCHEDULE:
        due = ref_date + timedelta(weeks=weeks)
        status = "overdue" if due < today else ("due_today" if due == today else "upcoming")
        entry = {
            "Vaccine": vaccine,
            "DoseNumber": dose,
            "DueDate": due.isoformat(),
            "Status": status,
        }
        schedule.append(entry)
        if status in ("due_today", "upcoming") and next_due is None:
            next_due = due.isoformat()
            next_vaccine = vaccine

    premature = (req.gestation_weeks or 40) < 37
    return {
        "ChildID": req.child_id,
        "DOB": req.dob,
        "Premature": premature,
        "CorrectedDOB": ref_date.isoformat() if premature else req.dob,
        "TotalDoses": len(IAP_SCHEDULE),
        "NextDueVaccine": next_vaccine,
        "NextDueDate": next_due,
        "Schedule": schedule,
    }
