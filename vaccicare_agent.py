"""
VacciCare Maestro — UiPath Python Agent

This module is the single entry point that UiPath Orchestrator calls.
Each public function maps to one Maestro stage action.
The agent uses the UiPath SDK (uipath 2.x) for queue/asset integration
and calls the local FastAPI microservices for business logic.
"""

import json
import httpx
from typing import Any

from uipath.platform import UiPath, UiPathApiConfig

# ── Service base URLs (override via UiPath assets in production) ──────────────
SERVICE_URLS = {
    "schedule":  "http://localhost:8001",
    "migration": "http://localhost:8002",
    "reminder":  "http://localhost:8003",
    "risk":      "http://localhost:8004",
    "cert":      "http://localhost:8005",
}

_http = httpx.Client(timeout=30)


def _call(service: str, path: str, payload: dict) -> dict:
    url = SERVICE_URLS[service] + path
    r = _http.post(url, json=payload)
    r.raise_for_status()
    return r.json()


def _health(service: str) -> dict:
    url = SERVICE_URLS[service] + "/health"
    r = _http.get(url, timeout=5)
    r.raise_for_status()
    return r.json()


# ── Stage 2 — Schedule Planning ───────────────────────────────────────────────

def stage2_schedule_planning(
    child_id: str,
    dob: str,
    birth_weight_grams: int = 2500,
    gestation_weeks: int = 40,
) -> dict[str, Any]:
    """
    Call the Schedule Builder service and return the full IAP 2024 schedule.
    Maestro reads NextDueVaccine, NextDueDate, TotalDoses from the result.
    """
    return _call("schedule", "/schedule", {
        "child_id":            child_id,
        "dob":                 dob,
        "birth_weight_grams":  birth_weight_grams,
        "gestation_weeks":     gestation_weeks,
    })


# ── Stage 3 — Reminder Dispatch ───────────────────────────────────────────────

def stage3_compose_reminder(
    child_id: str,
    child_name: str,
    parent_name: str,
    vaccine_name: str,
    due_date: str,
    clinic_name: str,
    clinic_address: str,
    language: str = "en",
    reminder_number: int = 1,
) -> dict[str, Any]:
    """
    Call the Reminder Composer service.
    Returns MessageBody and DLTTemplateID ready for MSG91 dispatch.
    """
    return _call("reminder", "/compose", {
        "child_id":        child_id,
        "child_name":      child_name,
        "parent_name":     parent_name,
        "vaccine_name":    vaccine_name,
        "due_date":        due_date,
        "clinic_name":     clinic_name,
        "clinic_address":  clinic_address,
        "language":        language,
        "reminder_number": reminder_number,
    })


# ── Stage 7 — No-show Risk Scoring ────────────────────────────────────────────

def stage7_score_risk(
    child_id: str,
    no_show_count: int = 0,
    reminders_sent: int = 0,
    distance_km: float = 0.0,
    prev_missed_doses: int = 0,
    is_migrated: bool = False,
    mother_age_under_20: bool = False,
    rural_flag: bool = False,
) -> dict[str, Any]:
    """
    Call the Risk Scorer service.
    If EscalateImmediately=True, Maestro routes to high-priority queue.
    """
    return _call("risk", "/score", {
        "child_id":            child_id,
        "no_show_count":       no_show_count,
        "reminders_sent":      reminders_sent,
        "distance_km":         distance_km,
        "prev_missed_doses":   prev_missed_doses,
        "is_migrated":         is_migrated,
        "mother_age_under_20": mother_age_under_20,
        "rural_flag":          rural_flag,
    })


# ── Stage 8 — Migration Handling ──────────────────────────────────────────────

def stage8_detect_migration(
    child_id: str,
    original_district: str,
    whatsapp_message: str,
    original_clinic_code: str,
) -> dict[str, Any]:
    """
    Call the Migration Agent to detect relocation from a WhatsApp message.
    Returns migration_detected, new_location, suggested_clinic_type.
    """
    return _call("migration", "/detect-migration", {
        "child_id":             child_id,
        "original_district":    original_district,
        "whatsapp_message":     whatsapp_message,
        "original_clinic_code": original_clinic_code,
    })


# ── Stage 9 — Case Closure / Certificate ─────────────────────────────────────

def stage9_generate_certificate(
    child_id: str,
    child_name: str,
    dob: str,
    parent_name: str,
    clinic_name: str,
    district: str,
    vaccines: list[dict],
    abha_id: str | None = None,
) -> dict[str, Any]:
    """
    Generate the bilingual PDF immunisation certificate.
    Returns CertPath and TotalDoses.
    """
    return _call("cert", "/generate", {
        "child_id":    child_id,
        "child_name":  child_name,
        "dob":         dob,
        "parent_name": parent_name,
        "clinic_name": clinic_name,
        "district":    district,
        "abha_id":     abha_id,
        "vaccines":    vaccines,
    })


# ── Health probe for all services ────────────────────────────────────────────

def health_check_all() -> dict[str, str]:
    results = {}
    for svc in SERVICE_URLS:
        try:
            r = _health(svc)
            results[svc] = r.get("status", "ok")
        except Exception as exc:
            results[svc] = f"ERROR: {exc}"
    return results


# ── UiPath Orchestrator queue integration ────────────────────────────────────

def process_queue_item(queue_item: dict) -> dict[str, Any]:
    """
    Generic dispatcher: reads action from a Maestro queue item and routes
    it to the correct stage function.

    Expected queue item shape:
    {
        "action": "stage2_schedule" | "stage3_reminder" | "stage7_risk" |
                  "stage8_migration" | "stage9_cert",
        "payload": { ...stage-specific fields... }
    }
    """
    action = queue_item.get("action", "")
    payload = queue_item.get("payload", {})

    dispatch = {
        "stage2_schedule":   lambda p: stage2_schedule_planning(**p),
        "stage3_reminder":   lambda p: stage3_compose_reminder(**p),
        "stage7_risk":       lambda p: stage7_score_risk(**p),
        "stage8_migration":  lambda p: stage8_detect_migration(**p),
        "stage9_cert":       lambda p: stage9_generate_certificate(**p),
    }

    if action not in dispatch:
        raise ValueError(f"Unknown action '{action}'. Valid: {list(dispatch)}")

    return dispatch[action](payload)
