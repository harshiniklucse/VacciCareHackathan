import pytest
from httpx import AsyncClient, ASGITransport
from datetime import date, timedelta


# ─── Schedule Builder ──────────────────────────────────────────────────────────

@pytest.fixture
def schedule_app():
    from scheduler.vaccine_scheduler import app
    return app


@pytest.mark.asyncio
async def test_health_schedule(schedule_app):
    async with AsyncClient(transport=ASGITransport(app=schedule_app), base_url="http://test") as client:
        r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_normal_baby_has_all_iap_vaccines(schedule_app):
    async with AsyncClient(transport=ASGITransport(app=schedule_app), base_url="http://test") as client:
        r = await client.post("/schedule", json={"child_id": "C001", "dob": "2024-06-01"})
    data = r.json()
    assert r.status_code == 200
    assert data["TotalDoses"] == 28
    assert data["Premature"] is False


@pytest.mark.asyncio
async def test_premature_baby_corrected_age(schedule_app):
    async with AsyncClient(transport=ASGITransport(app=schedule_app), base_url="http://test") as client:
        r = await client.post("/schedule", json={
            "child_id": "C002", "dob": "2024-01-15",
            "gestation_weeks": 32, "birth_weight_grams": 1800
        })
    data = r.json()
    assert data["Premature"] is True
    assert data["CorrectedDOB"] != data["DOB"]


@pytest.mark.asyncio
async def test_next_vaccine_is_upcoming(schedule_app):
    future_dob = (date.today() - timedelta(weeks=4)).isoformat()
    async with AsyncClient(transport=ASGITransport(app=schedule_app), base_url="http://test") as client:
        r = await client.post("/schedule", json={"child_id": "C003", "dob": future_dob})
    data = r.json()
    assert data["NextDueVaccine"] is not None
    assert data["NextDueDate"] is not None


@pytest.mark.asyncio
async def test_newborn_first_vaccines_at_birth(schedule_app):
    today = date.today().isoformat()
    async with AsyncClient(transport=ASGITransport(app=schedule_app), base_url="http://test") as client:
        r = await client.post("/schedule", json={"child_id": "C004", "dob": today})
    data = r.json()
    birth_vaccines = [v for v in data["Schedule"] if v["DueDate"] == today]
    names = [v["Vaccine"] for v in birth_vaccines]
    assert "BCG" in names
    assert "OPV0" in names
    assert "Hep-B" in names


# ─── Risk Scorer ───────────────────────────────────────────────────────────────

@pytest.fixture
def risk_app():
    from risk.risk_scorer import app
    return app


@pytest.mark.asyncio
async def test_health_risk(risk_app):
    async with AsyncClient(transport=ASGITransport(app=risk_app), base_url="http://test") as client:
        r = await client.get("/health")
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_zero_risk_for_compliant_child(risk_app):
    async with AsyncClient(transport=ASGITransport(app=risk_app), base_url="http://test") as client:
        r = await client.post("/score", json={"child_id": "R001"})
    data = r.json()
    assert data["RiskScore"] < 0.40
    assert data["RiskLabel"] == "LOW"
    assert data["EscalateImmediately"] is False


@pytest.mark.asyncio
async def test_critical_risk_escalates_immediately(risk_app):
    async with AsyncClient(transport=ASGITransport(app=risk_app), base_url="http://test") as client:
        r = await client.post("/score", json={
            "child_id": "R002",
            "no_show_count": 3,
            "reminders_sent": 3,
            "distance_km": 25.0,
            "prev_missed_doses": 4,
            "is_migrated": True,
            "mother_age_under_20": True,
            "rural_flag": True,
        })
    data = r.json()
    assert data["EscalateImmediately"] is True
    assert data["RiskLabel"] == "HIGH"


@pytest.mark.asyncio
async def test_medium_risk_not_escalated(risk_app):
    async with AsyncClient(transport=ASGITransport(app=risk_app), base_url="http://test") as client:
        r = await client.post("/score", json={
            "child_id": "R003",
            "no_show_count": 1,
            "distance_km": 8.0,
            "rural_flag": True,
        })
    data = r.json()
    assert data["EscalateImmediately"] is False


@pytest.mark.asyncio
async def test_migration_adds_risk(risk_app):
    async with AsyncClient(transport=ASGITransport(app=risk_app), base_url="http://test") as client:
        base = await client.post("/score", json={"child_id": "R004"})
        migrated = await client.post("/score", json={"child_id": "R004b", "is_migrated": True})
    assert migrated.json()["RiskScore"] > base.json()["RiskScore"]


# ─── Reminder Composer (offline — no API key needed for structure test) ────────

@pytest.fixture
def reminder_app():
    from reminder.reminder_composer import app
    return app


@pytest.mark.asyncio
async def test_health_reminder(reminder_app):
    async with AsyncClient(transport=ASGITransport(app=reminder_app), base_url="http://test") as client:
        r = await client.get("/health")
    assert r.json()["status"] == "ok"


# ─── Certificate Generator ─────────────────────────────────────────────────────

@pytest.fixture
def cert_app():
    from cert.cert_generator import app
    return app


@pytest.mark.asyncio
async def test_health_cert(cert_app):
    async with AsyncClient(transport=ASGITransport(app=cert_app), base_url="http://test") as client:
        r = await client.get("/health")
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_generate_certificate(cert_app):
    payload = {
        "child_id": "CERT001",
        "child_name": "Arjun Test",
        "dob": "2024-01-15",
        "parent_name": "Priya Test",
        "clinic_name": "PHC Velachery",
        "district": "Chennai",
        "abha_id": "TEST-ABHA-001",
        "vaccines": [
            {"vaccine_name": "BCG",   "dose_number": 1, "date_administered": "2024-01-15", "batch_number": "BCG001", "nurse_id": "N01"},
            {"vaccine_name": "OPV0",  "dose_number": 1, "date_administered": "2024-01-15", "batch_number": "OPV001", "nurse_id": "N01"},
            {"vaccine_name": "Hep-B", "dose_number": 1, "date_administered": "2024-01-15", "batch_number": "HEP001", "nurse_id": "N01"},
        ],
    }
    async with AsyncClient(transport=ASGITransport(app=cert_app), base_url="http://test") as client:
        r = await client.post("/generate", json=payload)
    data = r.json()
    assert r.status_code == 200
    assert data["TotalDoses"] == 3
    import os
    assert os.path.exists(data["CertPath"])
