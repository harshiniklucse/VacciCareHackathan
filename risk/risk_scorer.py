from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import numpy as np

app = FastAPI(title="VacciCare Risk Scorer", version="1.0")

# Logistic regression coefficients (trained on synthetic HMIS dropout data)
# Features: [no_show_count, reminders_sent, distance_km, prev_missed_doses,
#            is_migrated, mother_age_under_20, rural_flag]
COEF = np.array([0.82, 0.35, 0.04, 0.61, 1.20, 0.45, 0.28])
INTERCEPT = -3.10


class RiskRequest(BaseModel):
    child_id: str
    no_show_count: int = 0
    reminders_sent: int = 0
    distance_km: float = 0.0
    prev_missed_doses: int = 0
    is_migrated: bool = False
    mother_age_under_20: bool = False
    rural_flag: bool = False


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + np.exp(-x))


def risk_label(score: float) -> str:
    if score >= 0.70:
        return "HIGH"
    if score >= 0.40:
        return "MEDIUM"
    return "LOW"


@app.get("/health")
def health():
    return {"status": "ok", "service": "risk-scorer"}


@app.post("/score")
def score_risk(req: RiskRequest):
    features = np.array([
        req.no_show_count,
        req.reminders_sent,
        req.distance_km,
        req.prev_missed_doses,
        int(req.is_migrated),
        int(req.mother_age_under_20),
        int(req.rural_flag),
    ])

    log_odds = float(np.dot(COEF, features)) + INTERCEPT
    score = round(float(sigmoid(log_odds)), 4)
    label = risk_label(score)

    # Top contributing factors
    contributions = {
        "no_show_count":       round(COEF[0] * req.no_show_count, 3),
        "reminders_sent":      round(COEF[1] * req.reminders_sent, 3),
        "distance_km":         round(COEF[2] * req.distance_km, 3),
        "prev_missed_doses":   round(COEF[3] * req.prev_missed_doses, 3),
        "is_migrated":         round(COEF[4] * int(req.is_migrated), 3),
        "mother_age_under_20": round(COEF[5] * int(req.mother_age_under_20), 3),
        "rural_flag":          round(COEF[6] * int(req.rural_flag), 3),
    }
    top_factor = max(contributions, key=lambda k: contributions[k])

    return {
        "ChildID":              req.child_id,
        "RiskScore":            score,
        "RiskLabel":            label,
        "EscalateImmediately":  score >= 0.70,
        "TopRiskFactor":        top_factor,
        "Contributions":        contributions,
    }
