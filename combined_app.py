"""
VacciCare Maestro — Combined FastAPI app
All 5 microservices on a single Railway instance.
Endpoints:
  POST /schedule          → Schedule Builder
  POST /detect-migration  → Migration Agent
  POST /compose           → Reminder Composer
  POST /score             → Risk Scorer
  POST /generate          → Certificate Generator
  GET  /health            → Overall health check
  GET  /docs              → Swagger UI (all endpoints)
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

# Import all route handlers from each service
from scheduler.vaccine_scheduler  import app as sched_app
from migration.migration_agent    import app as mig_app
from reminder.reminder_composer   import app as rem_app
from risk.risk_scorer             import app as risk_app
from cert.cert_generator          import app as cert_app

app = FastAPI(
    title="VacciCare Maestro — All Services",
    description="AI-powered child vaccination follow-up system. All 5 microservices combined.",
    version="1.0.0",
)

# ── Mount all routes from each sub-app ───────────────────────────────────────

for route in sched_app.routes:
    app.routes.append(route)

for route in mig_app.routes:
    app.routes.append(route)

for route in rem_app.routes:
    app.routes.append(route)

for route in risk_app.routes:
    app.routes.append(route)

for route in cert_app.routes:
    app.routes.append(route)


# ── Root health check ────────────────────────────────────────────────────────

@app.get("/health", tags=["health"])
def health():
    return {
        "status": "ok",
        "service": "vaccicare-combined",
        "endpoints": {
            "schedule_builder":  "POST /schedule",
            "migration_agent":   "POST /detect-migration",
            "reminder_composer": "POST /compose",
            "risk_scorer":       "POST /score",
            "cert_generator":    "POST /generate",
        }
    }


@app.get("/", tags=["health"])
def root():
    return JSONResponse({
        "project": "VacciCare Maestro",
        "status":  "running",
        "docs":    "/docs",
        "health":  "/health",
    })
