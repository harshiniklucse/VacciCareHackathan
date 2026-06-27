"""
VacciCare Maestro — Combined FastAPI app
All 5 microservices on a single Railway instance.
Uses add_api_route so all POST endpoints appear correctly in /docs.
"""
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.responses import JSONResponse

app = FastAPI(
    title="VacciCare Maestro — All Services",
    description="AI-powered child vaccination follow-up. All 5 microservices on one URL.",
    version="1.0.0",
)

# ── Import each sub-app and copy its routes into this app ────────────────────

from scheduler.vaccine_scheduler import app as _sched
from migration.migration_agent   import app as _mig
from reminder.reminder_composer  import app as _rem
from risk.risk_scorer            import app as _risk
from cert.cert_generator         import app as _cert

def _copy_routes(source, tag):
    for route in source.routes:
        if isinstance(route, APIRoute):
            app.add_api_route(
                path=route.path,
                endpoint=route.endpoint,
                methods=list(route.methods),
                tags=[tag],
                summary=route.summary or route.name,
                response_model=route.response_model,
            )

_copy_routes(_sched, "Schedule Builder")
_copy_routes(_mig,   "Migration Agent")
_copy_routes(_rem,   "Reminder Composer")
_copy_routes(_risk,  "Risk Scorer")
_copy_routes(_cert,  "Certificate Generator")


# ── Root & combined health check ─────────────────────────────────────────────

@app.get("/health", tags=["Health"])
def health():
    return {
        "status":  "ok",
        "service": "vaccicare-combined",
        "routes": {
            "POST /schedule":         "IAP 2024 vaccine schedule builder",
            "POST /detect-migration": "Family relocation detection (Claude AI)",
            "POST /compose":          "Multilingual DLT reminder composer",
            "POST /score":            "Dropout risk scorer",
            "POST /generate":         "Bilingual PDF certificate generator",
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
