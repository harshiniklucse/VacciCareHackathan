from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
import qrcode
import os
import tempfile
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

app = FastAPI(title="VacciCare Certificate Generator", version="1.0")

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "certs_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


class VaccineRecord(BaseModel):
    vaccine_name: str
    dose_number: int
    date_administered: str
    batch_number: str
    nurse_id: str


class CertRequest(BaseModel):
    child_id: str
    child_name: str
    dob: str
    parent_name: str
    clinic_name: str
    district: str
    abha_id: Optional[str] = None
    vaccines: List[VaccineRecord]


def build_qr(data: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=4, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    safe = data[:20].replace('/', '_').replace('|', '_')
    path = os.path.join(OUTPUT_DIR, f"qr_{safe}.png")
    img.save(path)
    return path


@app.get("/health")
def health():
    return {"status": "ok", "service": "cert-generator"}


@app.post("/generate")
def generate_certificate(req: CertRequest):
    cert_path = os.path.join(OUTPUT_DIR, f"cert_{req.child_id}.pdf")
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", parent=styles["Title"], fontSize=16, spaceAfter=6, alignment=TA_CENTER)
    sub_style  = ParagraphStyle("sub",   parent=styles["Normal"], fontSize=10, spaceAfter=4, alignment=TA_CENTER)
    body_style = ParagraphStyle("body",  parent=styles["Normal"], fontSize=9)

    doc = SimpleDocTemplate(cert_path, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    elements = []

    # Header
    elements.append(Paragraph("VACCINATION COMPLETION CERTIFICATE", title_style))
    elements.append(Paragraph("தடுப்பூசி நிறைவு சான்றிதழ்  |  टीकाकरण पूर्णता प्रमाण पत्र", sub_style))
    elements.append(Spacer(1, 0.4*cm))

    # Child info table
    info_data = [
        ["Child Name / குழந்தையின் பெயர்:", req.child_name, "Date of Birth:", req.dob],
        ["Parent Name / பெற்றோர் பெயர்:", req.parent_name, "Child ID:", req.child_id],
        ["Clinic / மருத்துவமனை:", req.clinic_name, "District:", req.district],
        ["ABHA ID:", req.abha_id or "Not Registered", "", ""],
    ]
    info_table = Table(info_data, colWidths=[4.5*cm, 5.5*cm, 3.5*cm, 3.5*cm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8F5E9")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.4*cm))

    # Vaccine records table
    elements.append(Paragraph("Vaccines Administered / வழங்கப்பட்ட தடுப்பூசிகள்:", body_style))
    elements.append(Spacer(1, 0.2*cm))

    vax_headers = ["#", "Vaccine", "Dose", "Date Given", "Batch No.", "Nurse ID"]
    vax_rows = [vax_headers]
    for i, v in enumerate(req.vaccines, 1):
        vax_rows.append([str(i), v.vaccine_name, str(v.dose_number), v.date_administered, v.batch_number, v.nurse_id])

    vax_table = Table(vax_rows, colWidths=[1*cm, 4*cm, 1.5*cm, 3*cm, 3.5*cm, 4*cm])
    vax_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1565C0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F8E9")]),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("PADDING", (0, 0), (-1, -1), 4),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    elements.append(vax_table)
    elements.append(Spacer(1, 0.6*cm))

    # QR code
    qr_data = f"VACCICARE|{req.child_id}|{req.child_name}|{req.dob}|DOSES:{len(req.vaccines)}"
    qr_path = build_qr(qr_data)
    qr_img = Image(qr_path, width=2.5*cm, height=2.5*cm)

    qr_data_table = Table(
        [["", qr_img, "Scan to verify this certificate\nइस प्रमाण पत्र को सत्यापित करने के लिए स्कैन करें\nசான்றிதழை சரிபார்க்க ஸ்கேன் செய்யுங்கள்"]],
        colWidths=[8*cm, 3*cm, 6*cm]
    )
    elements.append(qr_data_table)
    elements.append(Spacer(1, 0.4*cm))
    elements.append(Paragraph(
        f"This certificate was generated by VacciCare Maestro. "
        f"Total doses recorded: {len(req.vaccines)}.",
        ParagraphStyle("footer", parent=styles["Normal"], fontSize=7, textColor=colors.grey, alignment=TA_CENTER)
    ))

    doc.build(elements)
    return {"ChildID": req.child_id, "CertPath": cert_path, "TotalDoses": len(req.vaccines)}


@app.get("/download/{child_id}")
def download_cert(child_id: str):
    path = os.path.join(OUTPUT_DIR, f"cert_{child_id}.pdf")
    if not os.path.exists(path):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Certificate not found. Generate it first via POST /generate.")
    return FileResponse(path, media_type="application/pdf", filename=f"VacciCare_Cert_{child_id}.pdf")
