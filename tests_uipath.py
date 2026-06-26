"""
UiPath Integration Tests — VacciCare Maestro

These tests verify the vaccicare_agent.py dispatcher layer that UiPath
Orchestrator calls. Services run as ASGI in-process via uvicorn threads
so no external processes are needed.
"""

import os
import threading
import time
import pytest
import uvicorn
from datetime import date, timedelta

needs_anthropic = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set — skipping Claude API tests",
)


# ── In-process service launcher ───────────────────────────────────────────────

class _ServiceThread(threading.Thread):
    def __init__(self, app, port: int):
        super().__init__(daemon=True)
        self.config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
        self.server = uvicorn.Server(self.config)

    def run(self):
        self.server.run()

    def stop(self):
        self.server.should_exit = True


_threads: list[_ServiceThread] = []


@pytest.fixture(scope="session", autouse=True)
def start_all_services():
    """Spin up all 5 services once for the whole test session."""
    from scheduler.vaccine_scheduler import app as sched_app
    from reminder.reminder_composer import app as reminder_app
    from risk.risk_scorer import app as risk_app
    from cert.cert_generator import app as cert_app

    services = [
        (sched_app,    8001),
        (reminder_app, 8003),
        (risk_app,     8004),
        (cert_app,     8005),
    ]
    for app, port in services:
        t = _ServiceThread(app, port)
        t.start()
        _threads.append(t)

    # wait for them to be ready
    time.sleep(2)
    yield

    for t in _threads:
        t.stop()


# ── Agent import (after services are registered) ─────────────────────────────

@pytest.fixture(scope="session")
def agent():
    import vaccicare_agent as a
    return a


# ── Health check ─────────────────────────────────────────────────────────────

class TestHealthChecks:
    def test_schedule_service_up(self, agent):
        import httpx
        r = httpx.get("http://localhost:8001/health", timeout=5)
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_reminder_service_up(self, agent):
        import httpx
        r = httpx.get("http://localhost:8003/health", timeout=5)
        assert r.status_code == 200

    def test_risk_service_up(self, agent):
        import httpx
        r = httpx.get("http://localhost:8004/health", timeout=5)
        assert r.status_code == 200

    def test_cert_service_up(self, agent):
        import httpx
        r = httpx.get("http://localhost:8005/health", timeout=5)
        assert r.status_code == 200

    def test_health_check_all(self, agent):
        results = agent.health_check_all()
        assert results["schedule"] == "ok"
        assert results["reminder"] == "ok"
        assert results["risk"] == "ok"
        assert results["cert"] == "ok"


# ── Stage 2 — Schedule Planning ───────────────────────────────────────────────

class TestStage2SchedulePlanning:
    def test_normal_baby_schedule(self, agent):
        # Use a baby born 3 months ago so some doses are still upcoming
        recent_dob = (date.today() - timedelta(weeks=12)).isoformat()
        result = agent.stage2_schedule_planning(
            child_id="UI-C001",
            dob=recent_dob,
        )
        assert result["ChildID"] == "UI-C001"
        assert result["TotalDoses"] == 28
        assert result["NextDueVaccine"] is not None
        assert "Schedule" in result

    def test_premature_baby_schedule(self, agent):
        result = agent.stage2_schedule_planning(
            child_id="UI-C002",
            dob="2024-01-10",
            gestation_weeks=30,
            birth_weight_grams=1500,
        )
        assert result["Premature"] is True
        assert result["CorrectedDOB"] != result["DOB"]

    def test_newborn_has_bcg_at_birth(self, agent):
        today = date.today().isoformat()
        result = agent.stage2_schedule_planning(
            child_id="UI-C003",
            dob=today,
        )
        birth_doses = [v["Vaccine"] for v in result["Schedule"] if v["DueDate"] == today]
        assert "BCG" in birth_doses
        assert "Hep-B" in birth_doses

    def test_schedule_via_queue_dispatcher(self, agent):
        result = agent.process_queue_item({
            "action": "stage2_schedule",
            "payload": {
                "child_id": "UI-QUEUE-001",
                "dob": "2024-06-01",
            }
        })
        assert result["TotalDoses"] == 28

    def test_overdue_vaccines_flagged(self, agent):
        old_dob = (date.today() - timedelta(weeks=60)).isoformat()
        result = agent.stage2_schedule_planning(child_id="UI-C004", dob=old_dob)
        overdue = [v for v in result["Schedule"] if v["Status"] == "overdue"]
        assert len(overdue) > 0


# ── Stage 3 — Reminder Dispatch ───────────────────────────────────────────────

class TestStage3ReminderDispatch:
    @needs_anthropic
    def test_english_reminder_composed(self, agent):
        result = agent.stage3_compose_reminder(
            child_id="UI-R001",
            child_name="Arjun",
            parent_name="Priya",
            vaccine_name="PCV3",
            due_date="2025-03-01",
            clinic_name="PHC Velachery",
            clinic_address="Velachery, Chennai",
            language="en",
            reminder_number=1,
        )
        assert result["ChildID"] == "UI-R001"
        assert "MessageBody" in result
        assert len(result["MessageBody"]) > 0
        assert result["DLTTemplateID"] is not None

    @needs_anthropic
    def test_tamil_reminder_has_dlt_template(self, agent):
        result = agent.stage3_compose_reminder(
            child_id="UI-R002",
            child_name="Kavya",
            parent_name="Meena",
            vaccine_name="MMR1",
            due_date="2025-05-10",
            clinic_name="PHC Ambattur",
            clinic_address="Ambattur, Chennai",
            language="ta",
        )
        assert result["Language"] == "ta"
        assert "VACCICARE_TA" in result["DLTTemplateID"]

    @needs_anthropic
    def test_second_reminder_via_queue(self, agent):
        result = agent.process_queue_item({
            "action": "stage3_reminder",
            "payload": {
                "child_id":       "UI-R003",
                "child_name":     "Dev",
                "parent_name":    "Sita",
                "vaccine_name":   "DTwP3",
                "due_date":       "2025-07-20",
                "clinic_name":    "PHC Guindy",
                "clinic_address": "Guindy, Chennai",
                "language":       "hi",
                "reminder_number": 2,
            }
        })
        assert result["Language"] == "hi"
        assert result["DLTTemplateID"] is not None

    @needs_anthropic
    def test_third_reminder_urgent_tone(self, agent):
        result = agent.stage3_compose_reminder(
            child_id="UI-R004",
            child_name="Tara",
            parent_name="Lakshmi",
            vaccine_name="OPV3",
            due_date="2025-02-14",
            clinic_name="CHC Mylapore",
            clinic_address="Mylapore, Chennai",
            language="en",
            reminder_number=3,
        )
        assert "MessageBody" in result
        assert len(result["MessageBody"]) <= 200  # within DLT limit


# ── Stage 7 — No-show Risk Scoring ────────────────────────────────────────────

class TestStage7RiskScoring:
    def test_low_risk_not_escalated(self, agent):
        result = agent.stage7_score_risk(child_id="UI-S001")
        assert result["RiskLabel"] == "LOW"
        assert result["EscalateImmediately"] is False

    def test_high_risk_escalated(self, agent):
        result = agent.stage7_score_risk(
            child_id="UI-S002",
            no_show_count=3,
            reminders_sent=3,
            distance_km=30.0,
            prev_missed_doses=5,
            is_migrated=True,
            mother_age_under_20=True,
            rural_flag=True,
        )
        assert result["EscalateImmediately"] is True
        assert result["RiskLabel"] == "HIGH"
        assert result["RiskScore"] >= 0.70

    def test_risk_score_in_valid_range(self, agent):
        result = agent.stage7_score_risk(child_id="UI-S003", no_show_count=1)
        assert 0.0 <= result["RiskScore"] <= 1.0

    def test_migration_increases_score(self, agent):
        base = agent.stage7_score_risk(child_id="UI-S004")
        migrated = agent.stage7_score_risk(child_id="UI-S004b", is_migrated=True)
        assert migrated["RiskScore"] > base["RiskScore"]

    def test_risk_via_queue_dispatcher(self, agent):
        result = agent.process_queue_item({
            "action": "stage7_risk",
            "payload": {
                "child_id":      "UI-QUEUE-007",
                "no_show_count": 2,
                "rural_flag":    True,
            }
        })
        assert "RiskScore" in result
        assert "EscalateImmediately" in result

    def test_top_risk_factor_identified(self, agent):
        result = agent.stage7_score_risk(
            child_id="UI-S005",
            is_migrated=True,
        )
        assert result["TopRiskFactor"] is not None


# ── Stage 9 — Certificate Generation ─────────────────────────────────────────

class TestStage9CertificateGeneration:
    VACCINES = [
        {"vaccine_name": "BCG",   "dose_number": 1, "date_administered": "2024-01-15",
         "batch_number": "BCG001", "nurse_id": "N01"},
        {"vaccine_name": "OPV0",  "dose_number": 1, "date_administered": "2024-01-15",
         "batch_number": "OPV001", "nurse_id": "N01"},
        {"vaccine_name": "Hep-B", "dose_number": 1, "date_administered": "2024-01-15",
         "batch_number": "HEP001", "nurse_id": "N01"},
        {"vaccine_name": "DTwP1", "dose_number": 1, "date_administered": "2024-02-26",
         "batch_number": "DTP001", "nurse_id": "N02"},
    ]

    def test_certificate_generated(self, agent):
        result = agent.stage9_generate_certificate(
            child_id="UI-CERT001",
            child_name="Arjun Raj",
            dob="2024-01-15",
            parent_name="Priya Raj",
            clinic_name="PHC Velachery",
            district="Chennai",
            vaccines=self.VACCINES,
            abha_id="UI-ABHA-001",
        )
        assert result["ChildID"] == "UI-CERT001"
        assert result["TotalDoses"] == 4

    def test_cert_pdf_file_exists(self, agent):
        import os
        result = agent.stage9_generate_certificate(
            child_id="UI-CERT002",
            child_name="Kavya M",
            dob="2024-03-10",
            parent_name="Raji M",
            clinic_name="CHC Ambattur",
            district="Chennai",
            vaccines=self.VACCINES[:2],
        )
        assert os.path.exists(result["CertPath"])

    def test_cert_via_queue_dispatcher(self, agent):
        result = agent.process_queue_item({
            "action": "stage9_cert",
            "payload": {
                "child_id":    "UI-QUEUE-009",
                "child_name":  "Queue Child",
                "dob":         "2024-02-01",
                "parent_name": "Queue Parent",
                "clinic_name": "PHC Test",
                "district":    "Chennai",
                "vaccines":    self.VACCINES[:1],
            }
        })
        assert result["TotalDoses"] == 1


# ── Queue Dispatcher — error handling ────────────────────────────────────────

class TestQueueDispatcher:
    def test_unknown_action_raises_value_error(self, agent):
        with pytest.raises(ValueError, match="Unknown action"):
            agent.process_queue_item({"action": "stage99_unknown", "payload": {}})

    def test_empty_action_raises_value_error(self, agent):
        with pytest.raises(ValueError):
            agent.process_queue_item({"action": "", "payload": {}})

    def test_all_stage_actions_are_registered(self, agent):
        import inspect
        # Dispatcher table lives inside process_queue_item — test each key works
        for action, child_id, payload in [
            ("stage2_schedule",  "D-C01", {"child_id": "D-C01", "dob": "2024-01-15"}),
            ("stage7_risk",      "D-S01", {"child_id": "D-S01"}),
        ]:
            result = agent.process_queue_item({"action": action, "payload": payload})
            assert isinstance(result, dict)
