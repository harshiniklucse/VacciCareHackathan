"""
VacciCare Maestro — Combined FastAPI app
Directly imports all endpoint functions and registers them.
More reliable than copying route objects between apps.
"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(
    title="VacciCare Maestro — All Services",
    description="AI-powered child vaccination follow-up. All 5 microservices on one URL.",
    version="1.0.0",
)

# ── Schedule Builder (port 8001 logic) ───────────────────────────────────────
from scheduler.vaccine_scheduler import generate_schedule, health as sched_health, ScheduleRequest

app.add_api_route("/health/schedule",   sched_health,      methods=["GET"],  tags=["Schedule Builder"], summary="Schedule Builder health")
app.add_api_route("/schedule",          generate_schedule,  methods=["POST"], tags=["Schedule Builder"], summary="Generate IAP 2024 vaccine schedule")

# ── Migration Agent (port 8002 logic) ────────────────────────────────────────
from migration.migration_agent import detect_migration, health as mig_health, MigrationRequest

app.add_api_route("/health/migration",  mig_health,        methods=["GET"],  tags=["Migration Agent"],   summary="Migration Agent health")
app.add_api_route("/detect-migration",  detect_migration,   methods=["POST"], tags=["Migration Agent"],   summary="Detect family relocation from WhatsApp message")

# ── Reminder Composer (port 8003 logic) ──────────────────────────────────────
from reminder.reminder_composer import compose_reminder, health as rem_health, ReminderRequest

app.add_api_route("/health/reminder",   rem_health,        methods=["GET"],  tags=["Reminder Composer"], summary="Reminder Composer health")
app.add_api_route("/compose",           compose_reminder,   methods=["POST"], tags=["Reminder Composer"], summary="Compose multilingual DLT-compliant reminder")

# ── Risk Scorer (port 8004 logic) ────────────────────────────────────────────
from risk.risk_scorer import score_risk, health as risk_health, RiskRequest

app.add_api_route("/health/risk",       risk_health,       methods=["GET"],  tags=["Risk Scorer"],       summary="Risk Scorer health")
app.add_api_route("/score",             score_risk,         methods=["POST"], tags=["Risk Scorer"],       summary="Score dropout risk (0-1)")

# ── Certificate Generator (port 8005 logic) ───────────────────────────────────
from cert.cert_generator import generate_certificate, download_cert, health as cert_health, CertRequest

app.add_api_route("/health/cert",       cert_health,       methods=["GET"],  tags=["Certificate Generator"], summary="Certificate Generator health")
app.add_api_route("/generate",          generate_certificate, methods=["POST"], tags=["Certificate Generator"], summary="Generate bilingual PDF certificate")
app.add_api_route("/download/{child_id}", download_cert,   methods=["GET"],  tags=["Certificate Generator"], summary="Download generated certificate")

# ── Root health ───────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"], summary="Overall health check")
def health():
    return {
        "status":  "ok",
        "service": "vaccicare-combined",
        "endpoints": {
            "POST /schedule":           "IAP 2024 vaccine schedule builder",
            "POST /detect-migration":   "Family relocation detection (Claude AI)",
            "POST /compose":            "Multilingual DLT reminder composer",
            "POST /score":              "Dropout risk scorer",
            "POST /generate":           "Bilingual PDF certificate generator",
        }
    }

@app.get("/", tags=["Health"])
def root():
    return JSONResponse({
        "project": "VacciCare Maestro",
        "status":  "running",
        "docs":    "/docs",
        "health":  "/health",
    })
