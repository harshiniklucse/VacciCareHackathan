"""
Railway entry point — reads SERVICE_NAME env var to decide which
VacciCare microservice to start. Set SERVICE_NAME on each Railway
service's Variables tab.
"""
import os
import uvicorn

SERVICE = os.environ.get("SERVICE_NAME", "scheduler")

_APPS = {
    "scheduler": "scheduler.vaccine_scheduler:app",
    "migration": "migration.migration_agent:app",
    "reminder":  "reminder.reminder_composer:app",
    "risk":      "risk.risk_scorer:app",
    "cert":      "cert.cert_generator:app",
}

if __name__ == "__main__":
    app_path = _APPS.get(SERVICE)
    if not app_path:
        raise ValueError(f"Unknown SERVICE_NAME='{SERVICE}'. Choose: {list(_APPS)}")
    port = int(os.environ.get("PORT", 8000))
    print(f"[VacciCare] Starting service='{SERVICE}' on port {port}")
    uvicorn.run(app_path, host="0.0.0.0", port=port)
