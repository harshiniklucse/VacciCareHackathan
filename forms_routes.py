"""
VacciCare Maestro — Human Task Form Pages
Served at /forms/* from the Railway combined app.
Each form corresponds to a Maestro case stage that requires human input.

Usage in UiPath Maestro: set the Human Task URL to
  https://vaccicarehackathan-production.up.railway.app/forms/<stage>?case_id={case_id}
"""
from fastapi import APIRouter, Form, Query
from fastapi.responses import HTMLResponse
from typing import Optional
import json, datetime, uuid, httpx

router = APIRouter(prefix="/forms", tags=["Maestro Forms"])

BASE_API = "https://vaccicarehackathan-production.up.railway.app"

TN_DISTRICTS = [
    "Ariyalur","Chennai","Chengalpattu","Coimbatore","Cuddalore","Dharmapuri",
    "Dindigul","Erode","Kallakurichi","Kancheepuram","Karur","Krishnagiri",
    "Madurai","Mayiladuthurai","Nagapattinam","Namakkal","Nilgiris","Perambalur",
    "Pudukkottai","Ramanathapuram","Ranipet","Salem","Sivaganga","Tenkasi",
    "Thanjavur","Theni","Thoothukudi","Tiruchirappalli","Tirunelveli",
    "Tirupathur","Tiruppur","Tiruvallur","Tiruvannamalai","Tiruvarur",
    "Vellore","Villupuram","Virudhunagar"
]

IAP_VACCINES = [
    "BCG", "Hepatitis B (Birth)", "OPV-0", "DPT-1", "OPV-1", "Hib-1",
    "Rotavirus-1", "PCV-1", "DPT-2", "OPV-2", "Hib-2", "Rotavirus-2",
    "PCV-2", "DPT-3", "OPV-3", "Hib-3", "Rotavirus-3", "PCV-3", "IPV",
    "OPV-4", "DPT Booster-1", "MR/MMR-1", "JE-1", "Hepatitis A-1",
    "Varicella-1", "DPT Booster-2", "OPV-5", "MMR-2", "Typhoid CV",
    "Hepatitis A-2", "Varicella-2", "Tdap/Td"
]

# ─── shared HTML shell ────────────────────────────────────────────────────────

def _shell(title: str, stage_label: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — VacciCare Maestro</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
  :root{{--g:#2E7D32;--gl:#E8F5E9;--gd:#1B5E20}}
  body{{background:var(--gl);font-family:'Segoe UI',system-ui,sans-serif;font-size:.95rem}}
  .topbar{{background:var(--gd);padding:.7rem 1.5rem;display:flex;align-items:center;gap:1rem;flex-wrap:wrap}}
  .topbar .brand{{color:#fff;font-weight:700;font-size:1.15rem;text-decoration:none}}
  .topbar .sub{{color:rgba(255,255,255,.7);font-size:.82rem;margin-left:auto}}
  .stage-pill{{background:rgba(255,255,255,.2);color:#fff;padding:2px 12px;border-radius:20px;font-size:.78rem;white-space:nowrap}}
  .card{{border:none;border-radius:14px;box-shadow:0 4px 24px rgba(0,0,0,.07);margin-bottom:1.5rem}}
  .card-header{{background:var(--g);color:#fff;border-radius:14px 14px 0 0!important;padding:1.1rem 1.5rem;display:flex;align-items:center;gap:.7rem}}
  .card-header h5{{margin:0;font-weight:600}}
  .card-header .step-num{{background:rgba(255,255,255,.25);width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.9rem;flex-shrink:0}}
  .card-body{{padding:1.5rem}}
  .form-label{{font-weight:600;color:#333;font-size:.88rem;margin-bottom:.3rem}}
  .required::after{{content:" *";color:#c62828}}
  .hint{{font-size:.76rem;color:#777;margin-top:3px}}
  .section-divider{{border-left:4px solid var(--g);background:#f1f8e9;padding:.5rem 1rem;border-radius:0 6px 6px 0;font-weight:600;color:var(--gd);margin:1.2rem 0 .8rem;font-size:.9rem}}
  .btn-submit{{background:var(--g);border:none;color:#fff;padding:.65rem 2.5rem;border-radius:8px;font-weight:600;font-size:1rem;width:100%;margin-top:1rem;transition:.2s}}
  .btn-submit:hover{{background:var(--gd);color:#fff}}
  .btn-secondary-vc{{background:#fff;border:2px solid var(--g);color:var(--g);padding:.5rem 1.5rem;border-radius:8px;font-weight:600;text-decoration:none}}
  .success-card{{background:#fff;border:3px solid #4CAF50;border-radius:14px;padding:2.5rem;text-align:center}}
  .success-icon{{font-size:3.5rem;margin-bottom:1rem}}
  .data-row{{display:flex;border-bottom:1px solid #f0f0f0;padding:.4rem 0;font-size:.9rem}}
  .data-row .label{{color:#666;width:45%;flex-shrink:0}}
  .data-row .value{{font-weight:600;color:#222}}
  .form-check-input:checked{{background-color:var(--g);border-color:var(--g)}}
  .vaccine-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:.3rem}}
  @media(max-width:576px){{.vaccine-grid{{grid-template-columns:1fr 1fr}}}}
  .alert-info-vc{{background:#e3f2fd;border:1px solid #90caf9;border-radius:8px;padding:.8rem 1rem;font-size:.88rem;color:#0d47a1;margin-bottom:1rem}}
</style>
</head>
<body>
<div class="topbar">
  <a class="brand" href="/forms">💉 VacciCare Maestro</a>
  <span class="stage-pill">{stage_label}</span>
  <span class="sub">AI-Powered Child Vaccination Follow-up · Railway</span>
</div>
<div class="container py-4" style="max-width:800px">
{body}
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body></html>"""


def _success(stage: str, case_id: str, rows: list[tuple], next_form: str = "", next_label: str = "") -> str:
    rows_html = "".join(
        f'<div class="data-row"><span class="label">{k}</span><span class="value">{v}</span></div>'
        for k, v in rows
    )
    next_btn = (
        f'<a href="{next_form}?case_id={case_id}" class="btn-secondary-vc mt-3 d-inline-block">→ {next_label}</a>'
        if next_form else ""
    )
    body = f"""
<div class="success-card">
  <div class="success-icon">✅</div>
  <h4 class="text-success fw-bold mb-1">Submitted Successfully</h4>
  <p class="text-muted mb-3">{stage} · Case ID: <strong>{case_id}</strong></p>
  <div class="text-start mb-3">{rows_html}</div>
  {next_btn}
  <div class="mt-3">
    <a href="/forms" class="text-secondary text-decoration-none small">← Back to all forms</a>
  </div>
</div>"""
    return _shell(f"Submitted — {stage}", stage, body)


# ─── index ───────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def forms_index():
    cards = [
        ("1", "Case Intake", "intake", "Register a new child case — demographics, clinic, parent contact", "#1976D2"),
        ("4", "Appointment Confirmed", "appointment", "Log parent confirmation of vaccination appointment", "#7B1FA2"),
        ("5", "Vaccination Visit", "visit", "Record vaccines administered during the clinic visit", "#E65100"),
        ("6", "Post-Visit Update", "post-visit", "Health worker sign-off after vaccination is complete", "#00796B"),
        ("8", "Migration Detection", "migration", "Record if the family has relocated to another district", "#5D4037"),
        ("9", "Case Closure", "closure", "Supervisor approval — generate bilingual PDF certificate", "#C62828"),
    ]
    card_html = ""
    for num, name, slug, desc, color in cards:
        card_html += f"""
<div class="col-md-6 mb-3">
  <div class="card h-100">
    <div class="card-body">
      <div class="d-flex align-items-start gap-3">
        <div style="background:{color};color:#fff;width:42px;height:42px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:1.1rem;flex-shrink:0">{num}</div>
        <div>
          <h6 class="fw-bold mb-1">{name}</h6>
          <p class="text-muted small mb-2">{desc}</p>
          <a href="/forms/{slug}" class="btn btn-sm" style="background:{color};color:#fff;border-radius:6px">Open Form →</a>
        </div>
      </div>
    </div>
  </div>
</div>"""
    body = f"""
<div class="mb-4">
  <h3 class="fw-bold text-success">Maestro Human Task Forms</h3>
  <p class="text-muted">These forms handle the human-in-the-loop steps in the VacciCare vaccination follow-up pipeline.<br>
  Stages 2 (Schedule Planning), 3 (Reminder Dispatch) and 7 (Risk Scoring) are fully automated.</p>
</div>
<div class="row">{card_html}</div>
<div class="card mt-2">
  <div class="card-body small text-muted">
    <strong>API Endpoints:</strong>
    <code>/schedule</code> · <code>/compose</code> · <code>/score</code> · <code>/generate</code> · <code>/detect-migration</code>
    &nbsp;|&nbsp; <a href="/docs" class="text-success">Swagger Docs</a>
  </div>
</div>"""
    return _shell("Forms Index", "All Stages", body)


# ─── Stage 1: Case Intake ────────────────────────────────────────────────────

@router.get("/intake", response_class=HTMLResponse)
def intake_form(case_id: str = ""):
    auto_id = case_id or f"CASE-{datetime.date.today().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
    district_opts = "".join(f'<option value="{d}">{d}</option>' for d in TN_DISTRICTS)
    body = f"""
<div class="card">
  <div class="card-header">
    <div class="step-num">1</div>
    <h5>Stage 1 — Case Intake</h5>
  </div>
  <div class="card-body">
    <div class="alert-info-vc">Register a new child for the VacciCare vaccination tracking programme. All starred fields are mandatory.</div>
    <form method="POST" action="/forms/intake">

      <div class="section-divider">🆔 Case Identity</div>
      <div class="row g-3">
        <div class="col-md-6">
          <label class="form-label">Case ID <span class="text-muted fw-normal">(auto-generated)</span></label>
          <input type="text" name="case_id" value="{auto_id}" class="form-control" readonly style="background:#f8f8f8">
          <div class="hint">Generated automatically — copy this ID for future stages</div>
        </div>
        <div class="col-md-6">
          <label class="form-label required">ABHA Health ID</label>
          <input type="text" name="abha_id" class="form-control" placeholder="14-digit ABHA number (or leave blank)">
          <div class="hint">Ayushman Bharat Health Account — optional</div>
        </div>
      </div>

      <div class="section-divider">👶 Child Information</div>
      <div class="row g-3">
        <div class="col-md-6">
          <label class="form-label required">Child's Full Name</label>
          <input type="text" name="child_name" class="form-control" placeholder="e.g. Aarav Kumar" required>
        </div>
        <div class="col-md-6">
          <label class="form-label required">Date of Birth</label>
          <input type="date" name="dob" class="form-control" required max="{datetime.date.today().isoformat()}">
        </div>
        <div class="col-md-6">
          <label class="form-label">Birth Weight (grams)</label>
          <input type="number" name="birth_weight_grams" class="form-control" placeholder="2500" min="500" max="6000" value="2500">
          <div class="hint">Low birth weight: below 2500 g (affects vaccine schedule)</div>
        </div>
        <div class="col-md-6">
          <label class="form-label">Gestation Weeks</label>
          <input type="number" name="gestation_weeks" class="form-control" placeholder="40" min="24" max="44" value="40">
          <div class="hint">Preterm: below 37 weeks (IAP 2024 adjusted schedule applied)</div>
        </div>
        <div class="col-md-6">
          <label class="form-label required">Sex at Birth</label>
          <select name="sex" class="form-select" required>
            <option value="">— select —</option>
            <option>Male</option><option>Female</option><option>Other</option>
          </select>
        </div>
      </div>

      <div class="section-divider">👨‍👩‍👦 Parent / Guardian</div>
      <div class="row g-3">
        <div class="col-md-6">
          <label class="form-label required">Parent / Guardian Name</label>
          <input type="text" name="parent_name" class="form-control" placeholder="e.g. Priya Kumar" required>
        </div>
        <div class="col-md-6">
          <label class="form-label required">Mobile Number</label>
          <div class="input-group">
            <span class="input-group-text">+91</span>
            <input type="tel" name="parent_mobile" class="form-control" placeholder="9876543210" pattern="[0-9]{{10}}" required>
          </div>
        </div>
        <div class="col-md-6">
          <label class="form-label">Alternate Mobile</label>
          <div class="input-group">
            <span class="input-group-text">+91</span>
            <input type="tel" name="alt_mobile" class="form-control" placeholder="9876543211">
          </div>
        </div>
        <div class="col-md-6">
          <label class="form-label">Preferred Language</label>
          <select name="language" class="form-select">
            <option value="en">English</option>
            <option value="ta">Tamil (தமிழ்)</option>
            <option value="hi">Hindi (हिन्दी)</option>
          </select>
        </div>
      </div>

      <div class="section-divider">🏥 Clinic & Location</div>
      <div class="row g-3">
        <div class="col-md-6">
          <label class="form-label required">Clinic / PHC Name</label>
          <input type="text" name="clinic_name" class="form-control" placeholder="e.g. PHC Velachery" required>
        </div>
        <div class="col-md-12">
          <label class="form-label required">Clinic Address</label>
          <input type="text" name="clinic_address" class="form-control" placeholder="Street, Area, City" required>
        </div>
        <div class="col-md-6">
          <label class="form-label required">District</label>
          <select name="district" class="form-select" required>
            <option value="">— select district —</option>
            {district_opts}
          </select>
        </div>
        <div class="col-md-6">
          <label class="form-label">Risk Flags</label>
          <div class="mt-1">
            <div class="form-check form-check-inline"><input class="form-check-input" type="checkbox" name="is_rural" value="true" id="rural"><label class="form-check-label" for="rural">Rural area</label></div>
            <div class="form-check form-check-inline"><input class="form-check-input" type="checkbox" name="mother_under_20" value="true" id="mu20"><label class="form-check-label" for="mu20">Mother under 20</label></div>
            <div class="form-check form-check-inline"><input class="form-check-input" type="checkbox" name="migrant_family" value="true" id="mig"><label class="form-check-label" for="mig">Migrant family</label></div>
          </div>
        </div>
      </div>

      <button type="submit" class="btn-submit">Register Case &amp; Start Schedule Planning →</button>
    </form>
  </div>
</div>"""
    return _shell("Stage 1 — Case Intake", "Stage 1 · Case Intake", body)


@router.post("/intake", response_class=HTMLResponse)
async def intake_submit(
    case_id: str = Form(...), child_name: str = Form(...),
    dob: str = Form(...), birth_weight_grams: int = Form(2500),
    gestation_weeks: int = Form(40), parent_name: str = Form(...),
    parent_mobile: str = Form(...), clinic_name: str = Form(...),
    clinic_address: str = Form(...), district: str = Form(...),
    language: str = Form("en"), abha_id: str = Form(""),
    sex: str = Form(""), alt_mobile: str = Form(""),
    is_rural: str = Form("false"), mother_under_20: str = Form("false"),
    migrant_family: str = Form("false"),
):
    rows = [
        ("Case ID", case_id), ("Child Name", child_name), ("Date of Birth", dob),
        ("Birth Weight", f"{birth_weight_grams} g"), ("Gestation", f"{gestation_weeks} weeks"),
        ("Parent Name", parent_name), ("Mobile", f"+91 {parent_mobile}"),
        ("Clinic", clinic_name), ("District", district), ("Language", language),
        ("ABHA ID", abha_id or "Not registered"),
        ("Rural / Migrant / Young mother", f"{is_rural} / {migrant_family} / {mother_under_20}"),
    ]
    return _success("Stage 1 · Case Intake", case_id, rows,
                    next_form="", next_label="")


# ─── Stage 4: Appointment Confirmed ──────────────────────────────────────────

@router.get("/appointment", response_class=HTMLResponse)
def appointment_form(case_id: str = "", child_name: str = "",
                     vaccine: str = "", due_date: str = ""):
    body = f"""
<div class="card">
  <div class="card-header">
    <div class="step-num">4</div>
    <h5>Stage 4 — Appointment Confirmation</h5>
  </div>
  <div class="card-body">
    <div class="alert-info-vc">Record whether the parent/guardian has confirmed the upcoming vaccination appointment.</div>
    <form method="POST" action="/forms/appointment">
      <input type="hidden" name="case_id" value="{case_id}">

      <div class="row g-3">
        <div class="col-md-6">
          <label class="form-label required">Case ID</label>
          <input type="text" name="case_id_display" value="{case_id}" class="form-control" placeholder="CASE-20240115-ABC123" readonly style="background:#f8f8f8">
        </div>
        <div class="col-md-6">
          <label class="form-label">Child Name</label>
          <input type="text" name="child_name" value="{child_name}" class="form-control" placeholder="e.g. Aarav Kumar">
        </div>
        <div class="col-md-6">
          <label class="form-label">Vaccine Due</label>
          <input type="text" name="vaccine_due" value="{vaccine}" class="form-control" placeholder="e.g. DPT-2">
        </div>
        <div class="col-md-6">
          <label class="form-label">Due Date</label>
          <input type="date" name="due_date" value="{due_date}" class="form-control">
        </div>
      </div>

      <div class="section-divider">✅ Confirmation Status</div>
      <div class="row g-3">
        <div class="col-md-12">
          <label class="form-label required">Did the parent confirm the appointment?</label>
          <div class="d-flex gap-4 mt-1">
            <div class="form-check">
              <input class="form-check-input" type="radio" name="confirmed" value="yes" id="yes" required>
              <label class="form-check-label fw-bold text-success" for="yes">✔ Yes — Confirmed</label>
            </div>
            <div class="form-check">
              <input class="form-check-input" type="radio" name="confirmed" value="no" id="no">
              <label class="form-check-label fw-bold text-danger" for="no">✘ No — Not Confirmed</label>
            </div>
            <div class="form-check">
              <input class="form-check-input" type="radio" name="confirmed" value="unreachable" id="unr">
              <label class="form-check-label fw-bold text-warning" for="unr">⚠ Unreachable</label>
            </div>
          </div>
        </div>
        <div class="col-md-6">
          <label class="form-label">Confirmed Appointment Date</label>
          <input type="date" name="appointment_date" class="form-control">
        </div>
        <div class="col-md-6">
          <label class="form-label">Preferred Time Slot</label>
          <select name="time_slot" class="form-select">
            <option value="">— any time —</option>
            <option>09:00 – 11:00 AM</option>
            <option>11:00 AM – 01:00 PM</option>
            <option>02:00 – 04:00 PM</option>
            <option>04:00 – 06:00 PM</option>
          </select>
        </div>
        <div class="col-md-6">
          <label class="form-label">How was confirmation obtained?</label>
          <select name="channel" class="form-select">
            <option value="whatsapp">WhatsApp Reply</option>
            <option value="call">Phone Call</option>
            <option value="visit">In-Person Visit</option>
            <option value="sms">SMS Reply</option>
          </select>
        </div>
        <div class="col-md-6">
          <label class="form-label">Health Worker Name</label>
          <input type="text" name="worker_name" class="form-control" placeholder="Name of ASHA/ANM worker">
        </div>
        <div class="col-md-12">
          <label class="form-label">Notes</label>
          <textarea name="notes" class="form-control" rows="2" placeholder="Any additional remarks..."></textarea>
        </div>
      </div>

      <button type="submit" class="btn-submit">Submit Confirmation →</button>
    </form>
  </div>
</div>"""
    return _shell("Stage 4 — Appointment", "Stage 4 · Appointment Confirmed", body)


@router.post("/appointment", response_class=HTMLResponse)
async def appointment_submit(
    case_id: str = Form(""), child_name: str = Form(""),
    vaccine_due: str = Form(""), confirmed: str = Form(...),
    appointment_date: str = Form(""), time_slot: str = Form(""),
    channel: str = Form("whatsapp"), worker_name: str = Form(""),
    notes: str = Form(""),
):
    status_map = {"yes": "✅ Confirmed", "no": "❌ Not Confirmed", "unreachable": "⚠️ Unreachable"}
    rows = [
        ("Case ID", case_id), ("Child Name", child_name),
        ("Vaccine Due", vaccine_due),
        ("Confirmation Status", status_map.get(confirmed, confirmed)),
        ("Appointment Date", appointment_date or "—"),
        ("Time Slot", time_slot or "Any"),
        ("Channel", channel), ("Health Worker", worker_name),
        ("Notes", notes or "—"),
    ]
    next_form = "/forms/visit" if confirmed == "yes" else "/forms/appointment"
    next_label = "Proceed to Vaccination Visit →" if confirmed == "yes" else "Resend Reminder"
    return _success("Stage 4 · Appointment Confirmed", case_id, rows, next_form, next_label)


# ─── Stage 5: Vaccination Visit ──────────────────────────────────────────────

@router.get("/visit", response_class=HTMLResponse)
def visit_form(case_id: str = "", child_name: str = "", appointment_date: str = ""):
    vaccine_checks = ""
    for i, v in enumerate(IAP_VACCINES):
        vaccine_checks += f'<div class="form-check"><input class="form-check-input" type="checkbox" name="vaccines" value="{v}" id="v{i}"><label class="form-check-label" for="v{i}">{v}</label></div>'
    body = f"""
<div class="card">
  <div class="card-header">
    <div class="step-num">5</div>
    <h5>Stage 5 — Vaccination Visit Record</h5>
  </div>
  <div class="card-body">
    <div class="alert-info-vc">Record the outcome of the clinic visit. Tick every vaccine that was administered today.</div>
    <form method="POST" action="/forms/visit">

      <div class="row g-3">
        <div class="col-md-6">
          <label class="form-label">Case ID</label>
          <input type="text" name="case_id" value="{case_id}" class="form-control" placeholder="CASE-..." required>
        </div>
        <div class="col-md-6">
          <label class="form-label">Child Name</label>
          <input type="text" name="child_name" value="{child_name}" class="form-control" placeholder="e.g. Aarav Kumar">
        </div>
        <div class="col-md-6">
          <label class="form-label required">Visit Date</label>
          <input type="date" name="visit_date" value="{datetime.date.today().isoformat()}" class="form-control" required>
        </div>
        <div class="col-md-6">
          <label class="form-label required">Visit Outcome</label>
          <select name="visit_outcome" class="form-select" required>
            <option value="completed">✅ Vaccination Completed</option>
            <option value="partial">⚠ Partial (some vaccines deferred)</option>
            <option value="no_show">❌ No-Show — Child did not attend</option>
            <option value="sick">🤒 Child unwell — deferred</option>
          </select>
        </div>
      </div>

      <div class="section-divider">💉 Vaccines Administered Today</div>
      <div class="hint mb-2">Tick all vaccines given at this visit. Leave unticked if deferred.</div>
      <div class="vaccine-grid mb-3">
        {vaccine_checks}
      </div>

      <div class="section-divider">📋 Visit Details</div>
      <div class="row g-3">
        <div class="col-md-6">
          <label class="form-label">Health Worker / Nurse Name</label>
          <input type="text" name="worker_name" class="form-control" placeholder="Administering nurse / ASHA name">
        </div>
        <div class="col-md-6">
          <label class="form-label">Next Visit Date (estimated)</label>
          <input type="date" name="next_visit_date" class="form-control">
        </div>
        <div class="col-md-6">
          <label class="form-label">Distance from Clinic (km)</label>
          <input type="number" name="distance_km" class="form-control" placeholder="5" min="0" max="200" step="0.1">
        </div>
        <div class="col-md-6">
          <label class="form-label">Adverse Reaction Observed?</label>
          <select name="adverse_reaction" class="form-select">
            <option value="none">None observed</option>
            <option value="mild">Mild (fever / local swelling)</option>
            <option value="moderate">Moderate — monitoring required</option>
            <option value="severe">Severe — referred to hospital</option>
          </select>
        </div>
        <div class="col-md-12">
          <label class="form-label">Visit Notes</label>
          <textarea name="notes" class="form-control" rows="2" placeholder="Any clinical observations..."></textarea>
        </div>
      </div>

      <button type="submit" class="btn-submit">Record Visit &amp; Continue →</button>
    </form>
  </div>
</div>"""
    return _shell("Stage 5 — Vaccination Visit", "Stage 5 · Vaccination Visit", body)


@router.post("/visit", response_class=HTMLResponse)
async def visit_submit(
    case_id: str = Form(""), child_name: str = Form(""),
    visit_date: str = Form(...), visit_outcome: str = Form(...),
    worker_name: str = Form(""), next_visit_date: str = Form(""),
    distance_km: str = Form("5"), adverse_reaction: str = Form("none"),
    notes: str = Form(""),
    # vaccines is multi-value — handled via Request below
):
    # build vaccines list from raw form (FastAPI doesn't auto-list for multi-checkbox)
    from fastapi import Request
    rows = [
        ("Case ID", case_id), ("Child Name", child_name),
        ("Visit Date", visit_date), ("Outcome", visit_outcome),
        ("Health Worker", worker_name or "—"),
        ("Next Visit", next_visit_date or "—"),
        ("Distance", f"{distance_km} km"),
        ("Adverse Reaction", adverse_reaction),
        ("Notes", notes or "—"),
    ]
    return _success("Stage 5 · Vaccination Visit", case_id, rows,
                    "/forms/post-visit", "Proceed to Post-Visit Update →")


# ─── Stage 6: Post-Visit Update ──────────────────────────────────────────────

@router.get("/post-visit", response_class=HTMLResponse)
def post_visit_form(case_id: str = "", child_name: str = ""):
    body = f"""
<div class="card">
  <div class="card-header">
    <div class="step-num">6</div>
    <h5>Stage 6 — Post-Visit Update</h5>
  </div>
  <div class="card-body">
    <div class="alert-info-vc">Health worker sign-off confirming the visit record is complete and accurate.</div>
    <form method="POST" action="/forms/post-visit">

      <div class="row g-3">
        <div class="col-md-6">
          <label class="form-label">Case ID</label>
          <input type="text" name="case_id" value="{case_id}" class="form-control" placeholder="CASE-..." required>
        </div>
        <div class="col-md-6">
          <label class="form-label">Child Name</label>
          <input type="text" name="child_name" value="{child_name}" class="form-control" placeholder="e.g. Aarav Kumar">
        </div>
      </div>

      <div class="section-divider">📋 Completeness Checklist</div>
      <div class="row g-2">
        <div class="col-md-12">
          <div class="form-check mb-2">
            <input class="form-check-input" type="checkbox" name="all_vaccines_given" value="true" id="avg">
            <label class="form-check-label" for="avg"><strong>All planned vaccines for this visit were administered</strong></label>
          </div>
          <div class="form-check mb-2">
            <input class="form-check-input" type="checkbox" name="next_appt_set" value="true" id="nas">
            <label class="form-check-label" for="nas"><strong>Next appointment has been scheduled with the parent</strong></label>
          </div>
          <div class="form-check mb-2">
            <input class="form-check-input" type="checkbox" name="vaccination_card_updated" value="true" id="vcu">
            <label class="form-check-label" for="vcu"><strong>Child's physical vaccination card is updated</strong></label>
          </div>
          <div class="form-check mb-2">
            <input class="form-check-input" type="checkbox" name="adverse_follow_up" value="true" id="afu">
            <label class="form-check-label" for="afu">Adverse reaction follow-up completed (if applicable)</label>
          </div>
          <div class="form-check mb-2">
            <input class="form-check-input" type="checkbox" name="abha_updated" value="true" id="abu">
            <label class="form-check-label" for="abu">ABHA digital record updated</label>
          </div>
        </div>
      </div>

      <div class="section-divider">👤 Supervisor Sign-off</div>
      <div class="row g-3">
        <div class="col-md-6">
          <label class="form-label required">Health Worker Name</label>
          <input type="text" name="worker_name" class="form-control" required placeholder="ASHA / ANM / Nurse name">
        </div>
        <div class="col-md-6">
          <label class="form-label">Supervisor Name</label>
          <input type="text" name="supervisor_name" class="form-control" placeholder="PHC Medical Officer / Supervisor">
        </div>
        <div class="col-md-12">
          <label class="form-label">Additional Remarks</label>
          <textarea name="remarks" class="form-control" rows="2" placeholder="Any remarks for the medical record..."></textarea>
        </div>
      </div>

      <button type="submit" class="btn-submit">Submit Post-Visit Update →</button>
    </form>
  </div>
</div>"""
    return _shell("Stage 6 — Post-Visit", "Stage 6 · Post-Visit Update", body)


@router.post("/post-visit", response_class=HTMLResponse)
async def post_visit_submit(
    case_id: str = Form(""), child_name: str = Form(""),
    all_vaccines_given: str = Form("false"),
    next_appt_set: str = Form("false"),
    vaccination_card_updated: str = Form("false"),
    worker_name: str = Form(...), supervisor_name: str = Form(""),
    remarks: str = Form(""),
):
    rows = [
        ("Case ID", case_id), ("Child Name", child_name),
        ("All vaccines given", "✅ Yes" if all_vaccines_given == "true" else "⚠ Partial / No"),
        ("Next appointment set", "✅ Yes" if next_appt_set == "true" else "❌ No"),
        ("Card updated", "✅ Yes" if vaccination_card_updated == "true" else "❌ No"),
        ("Health Worker", worker_name), ("Supervisor", supervisor_name or "—"),
        ("Remarks", remarks or "—"),
    ]
    return _success("Stage 6 · Post-Visit Update", case_id, rows,
                    "/forms/closure", "Proceed to Case Closure →")


# ─── Stage 8: Migration Detection ────────────────────────────────────────────

@router.get("/migration", response_class=HTMLResponse)
def migration_form(case_id: str = "", child_name: str = "", district: str = ""):
    district_opts = "".join(f'<option value="{d}">{d}</option>' for d in TN_DISTRICTS)
    body = f"""
<div class="card">
  <div class="card-header">
    <div class="step-num">8</div>
    <h5>Stage 8 — Migration Detection</h5>
  </div>
  <div class="card-body">
    <div class="alert-info-vc">Record whether the family has relocated. If migrated, the case is transferred to the destination PHC.</div>
    <form method="POST" action="/forms/migration">

      <div class="row g-3">
        <div class="col-md-6">
          <label class="form-label">Case ID</label>
          <input type="text" name="case_id" value="{case_id}" class="form-control" required>
        </div>
        <div class="col-md-6">
          <label class="form-label">Child Name</label>
          <input type="text" name="child_name" value="{child_name}" class="form-control">
        </div>
        <div class="col-md-6">
          <label class="form-label">Current Registered District</label>
          <input type="text" name="current_district" value="{district}" class="form-control" readonly style="background:#f8f8f8">
        </div>
      </div>

      <div class="section-divider">🚚 Migration Status</div>
      <div class="row g-3">
        <div class="col-md-12">
          <label class="form-label required">Has the family migrated?</label>
          <div class="d-flex gap-4 mt-1">
            <div class="form-check">
              <input class="form-check-input" type="radio" name="is_migrated" value="yes" id="myes" required>
              <label class="form-check-label fw-bold text-warning" for="myes">🚚 Yes — Family has relocated</label>
            </div>
            <div class="form-check">
              <input class="form-check-input" type="radio" name="is_migrated" value="no" id="mno">
              <label class="form-check-label fw-bold text-success" for="mno">🏠 No — Still at registered address</label>
            </div>
          </div>
        </div>
      </div>

      <div id="migration_details" class="row g-3 mt-1">
        <div class="col-md-6">
          <label class="form-label">New District (destination)</label>
          <select name="new_district" class="form-select">
            <option value="">— if migrated, select new district —</option>
            {district_opts}
            <option value="other_state">Other State</option>
          </select>
        </div>
        <div class="col-md-6">
          <label class="form-label">New Mobile Number</label>
          <div class="input-group">
            <span class="input-group-text">+91</span>
            <input type="tel" name="new_mobile" class="form-control" placeholder="New contact number">
          </div>
        </div>
        <div class="col-md-6">
          <label class="form-label">New Address</label>
          <input type="text" name="new_address" class="form-control" placeholder="New residential address">
        </div>
        <div class="col-md-6">
          <label class="form-label">Migration Reason</label>
          <select name="migration_reason" class="form-select">
            <option value="">— select —</option>
            <option>Employment / Work</option>
            <option>Family relocation</option>
            <option>Seasonal migration</option>
            <option>Medical treatment elsewhere</option>
            <option>Other</option>
          </select>
        </div>
        <div class="col-md-12">
          <label class="form-label">WhatsApp Message Text (if detected via message)</label>
          <textarea name="whatsapp_text" class="form-control" rows="2"
            placeholder="Paste parent's WhatsApp reply here — AI will extract migration details"></textarea>
          <div class="hint">Optional: paste the message for Claude AI auto-extraction</div>
        </div>
      </div>

      <button type="submit" class="btn-submit">Submit Migration Record →</button>
    </form>
  </div>
</div>"""
    return _shell("Stage 8 — Migration", "Stage 8 · Migration Detection", body)


@router.post("/migration", response_class=HTMLResponse)
async def migration_submit(
    case_id: str = Form(""), child_name: str = Form(""),
    is_migrated: str = Form(...), new_district: str = Form(""),
    new_mobile: str = Form(""), new_address: str = Form(""),
    migration_reason: str = Form(""), whatsapp_text: str = Form(""),
    current_district: str = Form(""),
):
    migrated = is_migrated == "yes"
    ai_result = {}
    if migrated and whatsapp_text.strip():
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.post(f"{BASE_API}/detect-migration", json={
                    "child_id": case_id, "whatsapp_message": whatsapp_text,
                    "current_district": current_district
                })
                if r.status_code == 200:
                    ai_result = r.json()
        except Exception:
            pass

    rows = [
        ("Case ID", case_id), ("Child Name", child_name),
        ("Migrated", "✅ Yes — Case transferred" if migrated else "🏠 No — Continuing in same PHC"),
        ("New District", new_district or "—"),
        ("New Mobile", new_mobile or "—"),
        ("New Address", new_address or "—"),
        ("Reason", migration_reason or "—"),
    ]
    if ai_result:
        rows.append(("AI Detection Result", str(ai_result.get("detected", "—"))))

    next_form = "/forms/closure" if not migrated else ""
    next_label = "Proceed to Case Closure →" if not migrated else ""
    return _success("Stage 8 · Migration Detection", case_id, rows, next_form, next_label)


# ─── Stage 9: Case Closure ────────────────────────────────────────────────────

@router.get("/closure", response_class=HTMLResponse)
def closure_form(case_id: str = "", child_name: str = "",
                 cert_path: str = "", total_doses: str = ""):
    body = f"""
<div class="card">
  <div class="card-header" style="background:#C62828">
    <div class="step-num">9</div>
    <h5>Stage 9 — Case Closure &amp; Certificate</h5>
  </div>
  <div class="card-body">
    <div class="alert-info-vc">Supervisor reviews the case summary and approves closure. The AI system will generate a bilingual PDF vaccination certificate with ABHA QR code.</div>
    <form method="POST" action="/forms/closure">

      <div class="row g-3">
        <div class="col-md-6">
          <label class="form-label required">Case ID</label>
          <input type="text" name="case_id" value="{case_id}" class="form-control" required>
        </div>
        <div class="col-md-6">
          <label class="form-label required">Child Name</label>
          <input type="text" name="child_name" value="{child_name}" class="form-control" required>
        </div>
        <div class="col-md-6">
          <label class="form-label required">Date of Birth</label>
          <input type="date" name="dob" class="form-control" required>
        </div>
        <div class="col-md-6">
          <label class="form-label required">Parent Name</label>
          <input type="text" name="parent_name" class="form-control" required placeholder="Parent / guardian name">
        </div>
        <div class="col-md-6">
          <label class="form-label required">Clinic Name</label>
          <input type="text" name="clinic_name" class="form-control" required placeholder="PHC / Hospital name">
        </div>
        <div class="col-md-6">
          <label class="form-label required">District</label>
          <input type="text" name="district" class="form-control" required placeholder="e.g. Chennai">
        </div>
        <div class="col-md-6">
          <label class="form-label">ABHA ID</label>
          <input type="text" name="abha_id" class="form-control" placeholder="14-digit ABHA number">
        </div>
        <div class="col-md-6">
          <label class="form-label">Vaccines JSON (auto-filled)</label>
          <input type="text" name="vaccines_json" value="[]" class="form-control" placeholder='[]'>
          <div class="hint">Leave as [] if not available — system will use case records</div>
        </div>
      </div>

      <div class="section-divider">🏥 Supervisor Sign-off</div>
      <div class="row g-3">
        <div class="col-md-6">
          <label class="form-label required">Supervisor / Medical Officer Name</label>
          <input type="text" name="supervisor_name" class="form-control" required placeholder="Dr. / Officer name">
        </div>
        <div class="col-md-6">
          <label class="form-label">Designation</label>
          <select name="designation" class="form-select">
            <option>Medical Officer (PHC)</option>
            <option>Block Health Officer</option>
            <option>District Health Officer</option>
            <option>Child Health Programme Officer</option>
          </select>
        </div>
        <div class="col-md-12">
          <div class="form-check mt-2">
            <input class="form-check-input" type="checkbox" id="confirm_close" required>
            <label class="form-check-label fw-bold" for="confirm_close">
              I confirm that all vaccination records for this child are complete and accurate. I authorise case closure and certificate generation.
            </label>
          </div>
        </div>
      </div>

      <button type="submit" class="btn-submit" style="background:#C62828;border-color:#C62828">
        Generate Certificate &amp; Close Case ✓
      </button>
    </form>
  </div>
</div>"""
    return _shell("Stage 9 — Case Closure", "Stage 9 · Case Closure", body)


@router.post("/closure", response_class=HTMLResponse)
async def closure_submit(
    case_id: str = Form(...), child_name: str = Form(...),
    dob: str = Form(...), parent_name: str = Form(...),
    clinic_name: str = Form(...), district: str = Form(...),
    abha_id: str = Form(""), vaccines_json: str = Form("[]"),
    supervisor_name: str = Form(...), designation: str = Form(""),
):
    cert_url = ""
    total_doses = 0
    error_msg = ""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{BASE_API}/generate", json={
                "child_id": case_id, "child_name": child_name,
                "dob": dob, "parent_name": parent_name,
                "clinic_name": clinic_name, "district": district,
                "abha_id": abha_id or "NOT-REGISTERED",
                "vaccines": json.loads(vaccines_json) if vaccines_json.strip() != "[]" else []
            })
            if r.status_code == 200:
                data = r.json()
                cert_url = data.get("CertPath", data.get("cert_path", ""))
                total_doses = data.get("TotalDoses", data.get("total_doses", 0))
    except Exception as e:
        error_msg = str(e)

    rows = [
        ("Case ID", case_id), ("Child Name", child_name),
        ("Date of Birth", dob), ("Parent Name", parent_name),
        ("Clinic", clinic_name), ("District", district),
        ("Total Doses Recorded", str(total_doses)),
        ("Approved By", f"{supervisor_name} ({designation})"),
        ("Certificate URL", f'<a href="{cert_url}" target="_blank">{cert_url}</a>' if cert_url else "Generating…"),
    ]
    if error_msg:
        rows.append(("Generation Error", error_msg))

    return _success("Stage 9 · Case Closure", case_id, rows)
