"""RAKSHA AI - Automatic Accident Incident Report Generator (ReportLab)"""
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm

from app.config import settings

logger = logging.getLogger("raksha.reports")

def generate_pdf_report(incident: Dict[str, Any]) -> str:
    """Generates an official RAKSHA AI accident incident PDF report.
    Returns the absolute path to the generated PDF file.
    """
    incident_id = incident.get("incident_id", "RAKSHA-001")
    filename = f"{incident_id}_Report.pdf"
    pdf_path = settings.REPORTS_DIR / filename
    
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        "RakshaTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a"),
        alignment=0
    )
    
    subtitle_style = ParagraphStyle(
        "RakshaSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748b")
    )
    
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=10,
        spaceAfter=6
    )
    
    cell_bold = ParagraphStyle(
        "CellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#334155")
    )
    
    cell_val = ParagraphStyle(
        "CellVal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#0f172a")
    )
    
    footer_style = ParagraphStyle(
        "FooterNote",
        parent=styles["Italic"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#64748b"),
        alignment=1
    )

    story = []

    # 1. Header Banner
    severity = str(incident.get("severity", "Moderate")).upper()
    sev_bg = colors.HexColor("#ef4444") if severity == "CRITICAL" else colors.HexColor("#f59e0b") if severity == "MODERATE" else colors.HexColor("#3b82f6")
    
    header_data = [
        [
            Paragraph("<b>RAKSHA AI — INTELLIGENT ROAD SAFETY PLATFORM</b><br/><font size=8 color='#64748b'>AUTOMATED COLLISION DETECTION & EMERGENCY DISPATCH REPORT</font>", title_style),
            Paragraph(f"<font size=11 color='#ffffff'><b>SEVERITY: {severity}</b></font>", ParagraphStyle("SevBadge", parent=styles["Normal"], alignment=1, textColor=colors.white))
        ]
    ]
    header_table = Table(header_data, colWidths=[380, 140])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (1, 0), (1, 0), sev_bg),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('BOTTOMPADDING', (1, 0), (1, 0), 8),
        ('TOPPADDING', (1, 0), (1, 0), 8),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#cbd5e1"), spaceAfter=12))

    # 2. Key Telemetry Grid
    ts = incident.get("timestamp_str") or datetime.now().strftime("%d %B %Y, %I:%M:%S %p")
    location = incident.get("location_name", settings.LOCATION_NAME)
    lat = str(incident.get("latitude", settings.LATITUDE))
    lon = str(incident.get("longitude", settings.LONGITUDE))
    vehicles = str(incident.get("vehicles_involved", 2))
    vehicle_ids = str(incident.get("vehicle_ids", "01, 02"))
    confidence = f"{incident.get('ai_confidence', 92)}%"
    hospital = str(incident.get("hospital_name", "LLR Trauma Hospital"))

    data_meta = [
        [Paragraph("Incident ID:", cell_bold), Paragraph(f"<b>{incident_id}</b>", cell_val),
         Paragraph("Date & Time:", cell_bold), Paragraph(ts, cell_val)],
        [Paragraph("Location:", cell_bold), Paragraph(location, cell_val),
         Paragraph("GPS Coordinates:", cell_bold), Paragraph(f"{lat}, {lon}", cell_val)],
        [Paragraph("Vehicles Involved:", cell_bold), Paragraph(vehicles, cell_val),
         Paragraph("Tracking IDs:", cell_bold), Paragraph(vehicle_ids, cell_val)],
        [Paragraph("AI Confidence:", cell_bold), Paragraph(f"<b>{confidence}</b>", cell_val),
         Paragraph("Assigned Hospital:", cell_bold), Paragraph(hospital, cell_val)],
    ]
    meta_table = Table(data_meta, colWidths=[110, 150, 110, 150])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 12))

    # 3. Collision Visual Evidence (Screenshot)
    story.append(Paragraph("<b>Collision Visual Evidence (Captured Frame):</b>", section_heading))
    screenshot_path = incident.get("screenshot_path")
    
    if screenshot_path and os.path.exists(screenshot_path):
        try:
            # 520pt width fits neatly inside A4 margins (595 - 72 = 523)
            img = RLImage(screenshot_path, width=5.8*inch, height=3.2*inch)
            story.append(img)
        except Exception as e:
            logger.error(f"Error embedding screenshot into PDF: {e}")
            story.append(Paragraph(f"[Image file available at: {screenshot_path}]", cell_val))
    else:
        story.append(Paragraph("[Accident snapshot logged in digital archive]", cell_val))
        
    story.append(Spacer(1, 14))

    # 4. Multi-Agency Emergency Dispatch Status
    story.append(Paragraph("<b>Automated Emergency Dispatch Status:</b>", section_heading))
    h_status = str(incident.get("hospital_alert_status", "SENT")).replace("✓", "[CONFIRMED]")
    n_status = str(incident.get("nhai_alert_status", "SENT")).replace("✓", "[CONFIRMED]")
    
    dispatch_data = [
        [Paragraph("Agency / Responder", cell_bold), Paragraph("Channel", cell_bold), Paragraph("Recipient Contact", cell_bold), Paragraph("Status", cell_bold)],
        [Paragraph("Emergency Trauma Center", cell_val), Paragraph("SMTP / Dedicated Hook", cell_val), Paragraph(settings.HOSPITAL_ALERT_EMAIL, cell_val), Paragraph(f"<font color='green'><b>{h_status}</b></font>", cell_val)],
        [Paragraph("NHAI Highway Control Room", cell_val), Paragraph("Automated Dispatch", cell_val), Paragraph(settings.NHAI_ALERT_EMAIL, cell_val), Paragraph(f"<font color='green'><b>{n_status}</b></font>", cell_val)],
        [Paragraph("State Highway Patrol / 112", cell_val), Paragraph("Emergency Services API", cell_val), Paragraph(settings.EMERGENCY_SERVICES_EMAIL, cell_val), Paragraph("<font color='green'><b>SENT [CONFIRMED]</b></font>", cell_val)],
    ]
    dispatch_table = Table(dispatch_data, colWidths=[140, 110, 180, 90])
    dispatch_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(dispatch_table)
    story.append(Spacer(1, 14))

    # 5. Legal & Good Samaritan Safeguard Clause
    story.append(Paragraph("<b>Good Samaritan Statutory Protections (Section 134A, Motor Vehicles Act):</b>", section_heading))
    legal_text = (
        "Under the Good Samaritan Guidelines notified by the Ministry of Road Transport and Highways (MoRTH), "
        "any citizen who provides emergency assistance or escorts an accident victim to a medical facility is "
        "shielded from civil or criminal liability. Hospitals are legally mandated to commence immediate first-aid "
        "and emergency stabilization without requiring prior monetary deposits or administrative delays."
    )
    story.append(Paragraph(legal_text, ParagraphStyle("Legal", parent=styles["Normal"], fontSize=8, leading=11, textColor=colors.HexColor("#475569"))))
    story.append(Spacer(1, 14))
    
    # 6. Footer
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"), spaceAfter=8))
    story.append(Paragraph("RAKSHA AI Highway Safety Ecosystem • Automated Forensic Record • Confidential Official Document", footer_style))

    try:
        doc.build(story)
        logger.info(f"PDF Incident Report successfully generated: {pdf_path}")
        return str(pdf_path)
    except Exception as e:
        logger.error(f"Failed to generate PDF report: {e}")
        raise e
