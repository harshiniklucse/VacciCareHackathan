"""
VacciCare Maestro — Twilio WhatsApp dispatcher
Reads credentials from Railway environment variables.
"""
import os
from twilio.rest import Client

TWILIO_SID   = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
DEMO_PHONE   = os.environ.get("DEMO_PHONE", "+919486502870")
SANDBOX_FROM = "whatsapp:+14155238886"   # Twilio WhatsApp sandbox number


def send_whatsapp(to_phone: str, body: str) -> dict:
    if not TWILIO_SID or not TWILIO_TOKEN:
        return {"status": "error", "detail": "Twilio env vars not set"}
    if not to_phone.startswith("+"):
        to_phone = "+91" + to_phone.lstrip("0")
    try:
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        msg = client.messages.create(
            from_=SANDBOX_FROM,
            body=body,
            to=f"whatsapp:{to_phone}",
        )
        return {"status": "sent", "sid": msg.sid, "to": to_phone}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
