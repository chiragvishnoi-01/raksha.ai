"""RAKSHA AI - Emergency Alert Dispatcher (Hospital & NHAI Email Alert System)"""
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Any
from app.config import settings
from app.location.maps import get_google_maps_link

logger = logging.getLogger("raksha.alerts")

def generate_alert_html(incident: Dict[str, Any]) -> str:
    """Renders a high-impact HTML emergency notification template."""
    incident_id = incident.get("incident_id", "RAKSHA-DEV")
    time_str = incident.get("timestamp_str", "Just now")
    location = incident.get("location_name", settings.LOCATION_NAME)
    lat = incident.get("latitude", settings.LATITUDE)
    lon = incident.get("longitude", settings.LONGITUDE)
    severity = incident.get("severity", "CRITICAL").upper()
    vehicles = incident.get("vehicles_involved", 2)
    vehicle_ids = incident.get("vehicle_ids", "01, 02")
    hospital = incident.get("hospital_name", "Nearest Trauma Center")
    maps_url = get_google_maps_link(lat, lon)
    confidence = incident.get("ai_confidence", 92)

    color_theme = "#DC2626" if severity == "CRITICAL" else "#D97706" if severity == "MODERATE" else "#2563EB"

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>🚨 RAKSHA AI Emergency Alert</title>
</head>
<body style="font-family: Arial, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 24px;">
    <div style="max-width: 620px; margin: 0 auto; background: #1e293b; border-radius: 12px; border: 1px solid #334155; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
        <!-- Header Banner -->
        <div style="background: {color_theme}; padding: 20px; text-align: center;">
            <h1 style="margin: 0; font-size: 24px; color: #ffffff; text-transform: uppercase; letter-spacing: 1px;">
                🚨 AUTOMATED ACCIDENT ALERT
            </h1>
            <p style="margin: 6px 0 0 0; color: #fee2e2; font-size: 14px; font-weight: bold;">
                RAKSHA AI — Intelligent Road Accident Detection System
            </p>
        </div>

        <!-- Body Content -->
        <div style="padding: 24px;">
            <div style="background: #0f172a; padding: 16px; border-radius: 8px; border-left: 4px solid {color_theme}; margin-bottom: 20px;">
                <p style="margin: 0; font-size: 16px; line-height: 1.5;">
                    A high-confidence road collision has been detected. Immediate emergency response, trauma standby, and highway safety protocol execution are requested.
                </p>
            </div>

            <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px; font-size: 14px;">
                <tr style="border-bottom: 1px solid #334155;">
                    <td style="padding: 10px 0; color: #94a3b8; font-weight: bold;">Incident ID:</td>
                    <td style="padding: 10px 0; color: #38bdf8; font-family: monospace; font-size: 16px; font-weight: bold;">{incident_id}</td>
                </tr>
                <tr style="border-bottom: 1px solid #334155;">
                    <td style="padding: 10px 0; color: #94a3b8; font-weight: bold;">Detection Timestamp:</td>
                    <td style="padding: 10px 0; color: #f8fafc;">{time_str}</td>
                </tr>
                <tr style="border-bottom: 1px solid #334155;">
                    <td style="padding: 10px 0; color: #94a3b8; font-weight: bold;">Assessed Severity:</td>
                    <td style="padding: 10px 0;"><span style="background: {color_theme}; color: #fff; padding: 4px 10px; border-radius: 4px; font-weight: bold;">{severity}</span></td>
                </tr>
                <tr style="border-bottom: 1px solid #334155;">
                    <td style="padding: 10px 0; color: #94a3b8; font-weight: bold;">AI Detection Confidence:</td>
                    <td style="padding: 10px 0; color: #10b981; font-weight: bold;">{confidence}%</td>
                </tr>
                <tr style="border-bottom: 1px solid #334155;">
                    <td style="padding: 10px 0; color: #94a3b8; font-weight: bold;">Vehicles Involved:</td>
                    <td style="padding: 10px 0; color: #f8fafc;">{vehicles} (Tracking IDs: {vehicle_ids})</td>
                </tr>
                <tr style="border-bottom: 1px solid #334155;">
                    <td style="padding: 10px 0; color: #94a3b8; font-weight: bold;">Location:</td>
                    <td style="padding: 10px 0; color: #f8fafc;">{location}</td>
                </tr>
                <tr style="border-bottom: 1px solid #334155;">
                    <td style="padding: 10px 0; color: #94a3b8; font-weight: bold;">GPS Coordinates:</td>
                    <td style="padding: 10px 0; color: #cbd5e1; font-family: monospace;">{lat}, {lon}</td>
                </tr>
                <tr>
                    <td style="padding: 10px 0; color: #94a3b8; font-weight: bold;">Assigned Medical Center:</td>
                    <td style="padding: 10px 0; color: #fbbf24; font-weight: bold;">{hospital}</td>
                </tr>
            </table>

            <!-- Call to Action Button -->
            <div style="text-align: center; margin: 30px 0 20px 0;">
                <a href="{maps_url}" target="_blank" style="background: #2563eb; color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 15px; display: inline-block; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);">
                    📍 Open Incident Location in Google Maps
                </a>
            </div>

            <div style="background: #0f172a; padding: 14px; border-radius: 6px; margin-top: 20px; font-size: 12px; color: #94a3b8;">
                <p style="margin: 0 0 6px 0;"><strong>Action Protocol:</strong></p>
                <ul style="margin: 0; padding-left: 20px;">
                    <li>Hospital Trauma Team: Stand by Level-1 emergency triage bay.</li>
                    <li>NHAI Control Room: Dispatch nearest highway patrol unit and alert variable message signs (VMS).</li>
                    <li>Local Police & 112: Coordinate quick lane clearance.</li>
                </ul>
            </div>
        </div>

        <!-- Footer -->
        <div style="background: #0f172a; padding: 14px; text-align: center; border-top: 1px solid #334155; font-size: 11px; color: #64748b;">
            This is an automated emergency transmission generated by RAKSHA AI Highway Safety Platform.
        </div>
    </div>
</body>
</html>"""

def send_email_alert(incident_data: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatches emergency email alerts to configured hospital and NHAI recipients."""
    incident_id = incident_data.get("incident_id", "RAKSHA-001")
    severity = incident_data.get("severity", "CRITICAL")
    subject = f"🚨 RAKSHA AI — Accident Alert — {incident_id} [{severity}]"
    html_content = generate_alert_html(incident_data)
    
    recipients = [
        settings.HOSPITAL_ALERT_EMAIL,
        settings.NHAI_ALERT_EMAIL,
        settings.EMERGENCY_SERVICES_EMAIL
    ]
    # Filter out empty entries
    recipients = [r for r in recipients if r and "@" in r]

    # Check if live SMTP credentials exist
    if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.ALERT_SENDER
            msg["To"] = ", ".join(recipients)
            
            part = MIMEText(html_content, "html")
            msg.attach(part)
            
            with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=10) as server:
                server.starttls()
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.sendmail(settings.ALERT_SENDER, recipients, msg.as_string())
            
            logger.info(f"Live emergency email sent to: {recipients}")
            return {
                "hospital_alert_status": "SENT",
                "nhai_alert_status": "SENT",
                "delivery_mode": "LIVE_SMTP",
                "recipients": recipients
            }
        except Exception as e:
            logger.error(f"Live SMTP delivery failed: {e}. Logging alert in simulation mode.")
            return {
                "hospital_alert_status": "SENT (Simulated)",
                "nhai_alert_status": "SENT (Simulated)",
                "delivery_mode": "FALLBACK_LOG",
                "error": str(e),
                "recipients": recipients
            }
    else:
        # Graceful prototype simulation mode: Logs detailed dispatch without failing
        logger.info(f"[SIMULATED EMAIL DISPATCH] To: {recipients} | Subject: {subject}")
        return {
            "hospital_alert_status": "SENT (Simulated)",
            "nhai_alert_status": "SENT (Simulated)",
            "delivery_mode": "SIMULATION_MODE",
            "recipients": recipients
        }
