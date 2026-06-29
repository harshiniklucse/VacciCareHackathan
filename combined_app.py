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

# ── Maestro Human Task Forms ─────────────────────────────────────────────────
from forms_routes import router as forms_router
app.include_router(forms_router)

# ── WhatsApp Reminder Sender + Live Demo Page ────────────────────────────────
import httpx as _httpx, os as _os
from fastapi.responses import HTMLResponse as _HTMLResponse
from twilio_sender import send_whatsapp, DEMO_PHONE

SELF_BASE = "http://localhost:" + _os.environ.get("PORT", "8000")

@app.post("/send-reminder", tags=["Demo"], summary="Compose reminder via Claude AI and send via WhatsApp")
async def send_reminder(
    child_name:    str = "Dhian Hasan",
    parent_name:   str = "Swarna Harshini",
    parent_mobile: str = DEMO_PHONE,
    vaccine_name:  str = "DPT-2",
    due_date:      str = "2026-07-20",
    clinic_name:   str = "PHC Velachery",
    clinic_address:str = "Velachery Main Road, Chennai - 600042",
    language:      str = "ta",
    child_id:      str = "DEMO-2026-SH01",
    reminder_number: int = 1,
):
    payload = {
        "child_id": child_id, "child_name": child_name,
        "parent_name": parent_name, "parent_mobile": parent_mobile,
        "vaccine_name": vaccine_name, "due_date": due_date,
        "clinic_name": clinic_name, "clinic_address": clinic_address,
        "language": language, "reminder_number": reminder_number,
    }
    async with _httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{SELF_BASE}/compose", json=payload)
        r.raise_for_status()
        composed = r.json()

    message_body = composed.get("MessageBody", composed.get("message_body", ""))
    twilio_result = send_whatsapp(parent_mobile, message_body)

    return {
        "composed_message": message_body,
        "language": language,
        "char_count": len(message_body),
        "whatsapp": twilio_result,
    }


_DEMO_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>VacciCare Maestro — Live Demo</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:#0a1a0a;font-family:'Segoe UI',system-ui,sans-serif;color:#fff;min-height:100vh}
  .header{background:linear-gradient(135deg,#1B5E20,#2E7D32);padding:1.5rem 2rem;display:flex;align-items:center;gap:1rem;border-bottom:3px solid #4CAF50}
  .header h1{font-size:1.8rem;font-weight:700}
  .header .badge{background:rgba(255,255,255,.15);padding:4px 14px;border-radius:20px;font-size:.8rem}
  .container{max-width:900px;margin:0 auto;padding:2rem 1rem}
  .case-card{background:#111e11;border:1px solid #2E7D32;border-radius:14px;padding:1.5rem;margin-bottom:1.5rem}
  .case-card h3{color:#4CAF50;margin-bottom:1rem;font-size:1.1rem;display:flex;align-items:center;gap:.5rem}
  .case-grid{display:grid;grid-template-columns:1fr 1fr;gap:.6rem}
  .field{background:#0d150d;border-radius:8px;padding:.6rem .9rem}
  .field .lbl{font-size:.72rem;color:#81C784;text-transform:uppercase;letter-spacing:.05em;margin-bottom:2px}
  .field .val{font-size:.95rem;font-weight:600;color:#fff}
  .lang-row{display:flex;gap:.7rem;margin-bottom:1.5rem}
  .lang-btn{flex:1;padding:.7rem;border:2px solid #2E7D32;background:transparent;color:#81C784;border-radius:8px;cursor:pointer;font-size:.95rem;font-weight:600;transition:.2s}
  .lang-btn.active{background:#2E7D32;color:#fff;border-color:#4CAF50}
  .lang-btn:hover{background:#1B5E20;color:#fff}
  .fire-btn{width:100%;padding:1.2rem;background:linear-gradient(135deg,#2E7D32,#1B5E20);border:none;border-radius:12px;color:#fff;font-size:1.3rem;font-weight:700;cursor:pointer;letter-spacing:.05em;transition:.2s;position:relative;overflow:hidden}
  .fire-btn:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(76,175,80,.3)}
  .fire-btn:active{transform:translateY(0)}
  .fire-btn:disabled{opacity:.6;cursor:not-allowed;transform:none}
  .status-box{margin-top:1.5rem;border-radius:12px;overflow:hidden;display:none}
  .status-box.show{display:block}
  .status-header{padding:.8rem 1.2rem;font-weight:700;font-size:.95rem;display:flex;align-items:center;gap:.6rem}
  .status-body{padding:1.2rem;background:#0d150d;white-space:pre-wrap;font-size:.93rem;line-height:1.7;color:#E8F5E9;font-family:inherit}
  .sent .status-header{background:#1B5E20;color:#fff}
  .error .status-header{background:#7f1c1c;color:#fff}
  .loading .status-header{background:#1a3a5c;color:#fff}
  .phone-anim{display:inline-block;animation:buzz .15s ease infinite alternate}
  @keyframes buzz{from{transform:rotate(-3deg)}to{transform:rotate(3deg)}}
  .meta-row{display:flex;gap:1rem;margin-top:1rem;flex-wrap:wrap}
  .meta-pill{background:#0d150d;border:1px solid #2E7D32;border-radius:20px;padding:4px 14px;font-size:.82rem;color:#81C784}
  .whatsapp-preview{background:#075e54;border-radius:12px;padding:1rem;margin-top:1rem}
  .wa-bubble{background:#128c7e;border-radius:0 10px 10px 10px;padding:.8rem 1rem;max-width:80%;font-size:.9rem;line-height:1.6;color:#fff;white-space:pre-wrap}
  .wa-label{font-size:.78rem;color:#25d366;margin-bottom:.5rem;font-weight:600}
  .links{display:flex;gap:1rem;margin-top:2rem;flex-wrap:wrap}
  .link-btn{padding:.6rem 1.4rem;background:#0d150d;border:1px solid #2E7D32;border-radius:8px;color:#4CAF50;text-decoration:none;font-size:.9rem;transition:.2s}
  .link-btn:hover{background:#1B5E20;color:#fff}
</style>
</head>
<body>
<div class="header">
  <span style="font-size:2rem">&#128137;</span>
  <div>
    <h1>VacciCare Maestro</h1>
    <div style="font-size:.85rem;color:#A5D6A7;margin-top:2px">Live Demo Control Panel &mdash; UiPath Maestro Hackathon 2026</div>
  </div>
  <span class="badge" style="margin-left:auto">&#128312; LIVE</span>
</div>

<div class="container">

  <!-- Case Card -->
  <div class="case-card">
    <h3>&#128100; Active Demo Case</h3>
    <div class="case-grid">
      <div class="field"><div class="lbl">Case ID</div><div class="val">DEMO-2026-SH01</div></div>
      <div class="field"><div class="lbl">Child Name</div><div class="val">Dhian Hasan</div></div>
      <div class="field"><div class="lbl">Parent Name</div><div class="val">Swarna Harshini</div></div>
      <div class="field"><div class="lbl">Mobile</div><div class="val">+91 9486502870</div></div>
      <div class="field"><div class="lbl">Vaccine Due</div><div class="val">DPT-2</div></div>
      <div class="field"><div class="lbl">Due Date</div><div class="val">20 July 2026</div></div>
      <div class="field"><div class="lbl">Clinic</div><div class="val">PHC Velachery, Chennai</div></div>
      <div class="field"><div class="lbl">Risk Score</div><div class="val" style="color:#FF9800">MEDIUM &mdash; 0.52</div></div>
    </div>
  </div>

  <!-- Language selector -->
  <p style="color:#81C784;font-size:.9rem;margin-bottom:.6rem;font-weight:600">&#127757; Select Reminder Language</p>
  <div class="lang-row">
    <button class="lang-btn active" onclick="setLang('ta', this)">&#127470;&#127475; Tamil (&#2980;&#2990;&#3007;&#2996;&#3021;)</button>
    <button class="lang-btn" onclick="setLang('hi', this)">&#127470;&#127475; Hindi (&#2361;&#2367;&#2344;&#2381;&#2342;&#2368;)</button>
    <button class="lang-btn" onclick="setLang('en', this)">&#127468;&#127463; English</button>
  </div>

  <!-- Fire button -->
  <button class="fire-btn" id="fireBtn" onclick="sendReminder()">
    &#128242; SEND WHATSAPP REMINDER NOW
  </button>

  <!-- Status box -->
  <div class="status-box" id="statusBox">
    <div class="status-header" id="statusHeader"></div>
    <div class="status-body" id="statusBody"></div>
  </div>

  <!-- Quick links -->
  <div class="links">
    <a class="link-btn" href="/forms">&#128203; All Forms</a>
    <a class="link-btn" href="/forms/intake">Stage 1: Case Intake</a>
    <a class="link-btn" href="/docs#/Demo/send_reminder_send_reminder_post">API: /send-reminder</a>
    <a class="link-btn" href="/docs">Swagger Docs</a>
    <a class="link-btn" href="/health">Health Check</a>
  </div>

</div>

<script>
let selectedLang = 'ta';

function setLang(lang, btn) {
  selectedLang = lang;
  document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
}

async function sendReminder() {
  const btn = document.getElementById('fireBtn');
  const box = document.getElementById('statusBox');
  const hdr = document.getElementById('statusHeader');
  const bdy = document.getElementById('statusBody');

  btn.disabled = true;
  btn.textContent = '⏳ Composing with Claude AI...';
  box.className = 'status-box show loading';
  hdr.innerHTML = '&#9203; Claude AI is composing the reminder...';
  bdy.textContent = 'Calling /compose endpoint...';

  try {
    const params = new URLSearchParams({
      child_name: 'Dhian Hasan',
      parent_name: 'Swarna Harshini',
      parent_mobile: '+919486502870',
      vaccine_name: 'DPT-2',
      due_date: '2026-07-20',
      clinic_name: 'PHC Velachery',
      clinic_address: 'Velachery Main Road, Chennai - 600042',
      language: selectedLang,
      child_id: 'DEMO-2026-SH01',
      reminder_number: 1
    });

    btn.textContent = '📲 Sending via Twilio WhatsApp...';

    const res = await fetch('/send-reminder?' + params.toString(), { method: 'POST' });
    const data = await res.json();

    if (data.whatsapp && data.whatsapp.status === 'sent') {
      box.className = 'status-box show sent';
      hdr.innerHTML = '&#9989; WhatsApp Sent Successfully! Check +91 9486502870';
      const langLabel = {ta:'Tamil', hi:'Hindi', en:'English'}[selectedLang] || selectedLang;
      bdy.innerHTML =
        '<div class="wa-label">&#128242; WhatsApp message delivered in ' + langLabel + '</div>' +
        '<div class="wa-bubble">' + escHtml(data.composed_message) + '</div>' +
        '<div class="meta-row">' +
          '<span class="meta-pill">&#128203; ' + data.char_count + ' characters</span>' +
          '<span class="meta-pill">&#128222; SID: ' + data.whatsapp.sid + '</span>' +
          '<span class="meta-pill">&#127757; Language: ' + langLabel + '</span>' +
        '</div>';
      btn.textContent = '✅ Reminder Sent! Send Another?';
    } else {
      const errMsg = (data.whatsapp && data.whatsapp.detail) || JSON.stringify(data);
      box.className = 'status-box show error';
      hdr.innerHTML = '&#10060; Twilio Error';
      bdy.textContent = errMsg + '\\n\\nComposed message:\\n' + (data.composed_message || '');
      btn.textContent = '&#128242; SEND WHATSAPP REMINDER NOW';
    }
  } catch (e) {
    box.className = 'status-box show error';
    hdr.innerHTML = '&#10060; Network Error';
    bdy.textContent = e.message;
    btn.textContent = '&#128242; SEND WHATSAPP REMINDER NOW';
  }

  btn.disabled = false;
}

function escHtml(t) {
  return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\\n/g,'<br>');
}
</script>
</body>
</html>"""


@app.get("/demo", response_class=_HTMLResponse, tags=["Demo"], summary="Live demo control panel")
def demo_page():
    return _DEMO_HTML


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
        "forms":   "/forms",
    })
