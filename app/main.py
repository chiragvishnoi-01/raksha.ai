"""RAKSHA AI — Intelligent Road Accident Detection & Response System
Master FastAPI Application & Video Telemetry Server
"""
import os
import cv2
import time
import logging
import math
import threading
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional, Dict, Any, List

from fastapi import FastAPI, Depends, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.database.database import init_db, get_db
from app.database.models import Incident
from app.camera.webcam import camera_stream
from app.ai.detector import VehicleDetector
from app.ai.tracker import VehicleTracker, TrackedVehicle
from app.ai.collision import CollisionDetector
from app.location.maps import get_primary_hospital, find_nearest_hospitals, get_google_maps_link
from app.alerts.email import send_email_alert
from app.reports.pdf import generate_pdf_report

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("raksha.main")

# Initialize database schema on module load
init_db()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Intelligent road accident detection, tracking, severity analysis and multi-agency emergency response system."
)

# Directories
STATIC_DIR = Path(__file__).resolve().parent / "dashboard" / "static"
TEMPLATES_DIR = Path(__file__).resolve().parent / "dashboard" / "templates"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# AI Engine Components
detector = VehicleDetector()
tracker = VehicleTracker(detector=detector)
collision_detector = CollisionDetector()

# Global state for dashboard telemetry
telemetry_state = {
    "fps": 30.0,
    "active_vehicles": 0,
    "active_collision": False,
    "last_incident": None,
    "camera_online": True,
    "is_synthetic": False
}

def process_accident_incident(incident_data: Dict[str, Any]):
    """Orchestrates location identification, hospital alerts, PDF report generation, and database logging.
    Each step is wrapped individually so a single failure doesn't kill the entire pipeline.
    """
    from app.database.database import SessionLocal
    db = None
    incident_id = incident_data.get("incident_id", "UNKNOWN")
    logger.info(f"⚡ Processing automated emergency dispatch for {incident_id}...")

    h_status = "PENDING"
    n_status = "PENDING"
    pdf_path = None

    # 1. Identify primary hospital & ETA
    try:
        hospital = get_primary_hospital(incident_data.get("latitude"), incident_data.get("longitude"))
        incident_data["hospital_name"] = hospital["name"]
        incident_data["hospital_phone"] = hospital.get("phone", "+91-512-2535483")
        incident_data["hospital_eta"] = hospital.get("eta_minutes", 8)
    except Exception as e:
        logger.error(f"Step 1 (Hospital lookup) failed for {incident_id}: {e}", exc_info=True)
        incident_data.setdefault("hospital_name", "LLR Trauma Hospital (Default)")

    # 2. Dispatch multi-agency email alerts
    try:
        alert_result = send_email_alert(incident_data)
        h_status = alert_result.get("hospital_alert_status", "SENT ✓")
        n_status = alert_result.get("nhai_alert_status", "SENT ✓")
    except Exception as e:
        logger.error(f"Step 2 (Email dispatch) failed for {incident_id}: {e}", exc_info=True)
        h_status = "FAILED"
        n_status = "FAILED"
    incident_data["hospital_alert_status"] = h_status
    incident_data["nhai_alert_status"] = n_status

    # 3. Generate official PDF accident incident report
    try:
        pdf_path = generate_pdf_report(incident_data)
        incident_data["pdf_path"] = pdf_path
    except Exception as e:
        logger.error(f"Step 3 (PDF generation) failed for {incident_id}: {e}", exc_info=True)

    # 4. Commit to database
    try:
        db = SessionLocal()
        raw_ts = incident_data.get("timestamp")
        if isinstance(raw_ts, str):
            try:
                incident_ts = datetime.fromisoformat(raw_ts)
            except Exception:
                incident_ts = datetime.utcnow()
        else:
            incident_ts = raw_ts or datetime.utcnow()

        db_incident = Incident(
            incident_id=incident_id,
            timestamp=incident_ts,
            location_name=incident_data.get("location_name", settings.LOCATION_NAME),
            latitude=incident_data.get("latitude", settings.LATITUDE),
            longitude=incident_data.get("longitude", settings.LONGITUDE),
            severity=incident_data.get("severity", "Moderate"),
            ai_confidence=incident_data.get("ai_confidence", 90) / 100.0,
            vehicles_involved=incident_data.get("vehicles_involved", 2),
            vehicle_ids=incident_data.get("vehicle_ids", "01, 02"),
            screenshot_path=incident_data.get("screenshot_path"),
            pdf_path=pdf_path,
            hospital_name=incident_data.get("hospital_name"),
            hospital_alert_status=h_status,
            nhai_alert_status=n_status,
            details=incident_data.get("severity_reason", "Automated collision detection via RAKSHA AI")
        )
        db.add(db_incident)
        db.commit()
        logger.info(f"✅ Incident {incident_id} successfully recorded, dispatched, and archived.")
    except Exception as e:
        logger.error(f"Step 4 (Database commit) failed for {incident_id}: {e}", exc_info=True)
    finally:
        if db:
            try:
                db.close()
            except Exception:
                pass


def get_class_color(class_name: str, is_colliding: bool) -> tuple:
    """Returns color coding based on detected object category."""
    if is_colliding:
        return (0, 0, 255)  # Red alert
    c = class_name.lower()
    if c == "person":
        return (255, 50, 180)  # Neon violet/pink
    elif c in ("cell phone", "mouse", "laptop", "keyboard", "remote", "bottle", "cup", "book"):
        return (0, 255, 128)  # Bright neon green/mint for handheld gadgets
    elif c in ("car", "truck", "bus", "motorcycle", "bicycle", "vehicle"):
        return (0, 215, 255)  # Amber / electric gold for road vehicles
    else:
        return (255, 180, 50)  # Cyan/Blue for other objects

def draw_hud_overlays(frame: cv2.Mat, tracks: List[TrackedVehicle], is_colliding: bool) -> cv2.Mat:
    """Renders cybernetic tracking bounding boxes, trajectories, and collision indicators."""
    h, w = frame.shape[:2]

    # Draw tracked vehicle trajectories and bounding boxes
    for v in tracks:
        b = v.box
        color = get_class_color(v.class_name, is_colliding)

        # Draw trajectory motion trail ONLY for vehicles moving on road (never across people or handheld items)
        if v.class_name in ("car", "truck", "bus", "motorcycle", "bicycle") and v.speed > 8.0 and len(v.history) > 3:
            pts = list(v.history)[-8:]
            for idx in range(1, len(pts)):
                cv2.line(frame, pts[idx - 1], pts[idx], (0, 200, 255), 2, cv2.LINE_AA)

        # Corner bracket bounding box styling
        x1, y1, x2, y2 = b
        box_w = x2 - x1
        box_h = y2 - y1
        corner_len = max(6, min(20, box_w // 4, box_h // 4))

        # Thin outer bounding box
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1)

        # High-tech corner brackets
        thick = 2
        # Top-left
        cv2.line(frame, (x1, y1), (x1 + corner_len, y1), color, thick)
        cv2.line(frame, (x1, y1), (x1, y1 + corner_len), color, thick)
        # Top-right
        cv2.line(frame, (x2, y1), (x2 - corner_len, y1), color, thick)
        cv2.line(frame, (x2, y1), (x2, y1 + corner_len), color, thick)
        # Bottom-left
        cv2.line(frame, (x1, y2), (x1 + corner_len, y2), color, thick)
        cv2.line(frame, (x1, y2), (x1, y2 - corner_len), color, thick)
        # Bottom-right
        cv2.line(frame, (x2, y2), (x2 - corner_len, y2), color, thick)
        cv2.line(frame, (x2, y2), (x2, y2 - corner_len), color, thick)

        # Clean label tag with solid background
        label = f"{v.class_name.upper()} #{v.track_id:02d} ({int(v.confidence * 100)}%)"
        (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        tag_y1 = max(0, y1 - lh - 8)
        tag_y2 = y1
        cv2.rectangle(frame, (x1, tag_y1), (x1 + lw + 6, tag_y2), color, -1)
        cv2.putText(frame, label, (x1 + 3, tag_y2 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)

    # Collision warning alert overlay banner
    if is_colliding:
        cv2.rectangle(frame, (0, 0), (w, 50), (0, 0, 200), -1)
        cv2.putText(frame, "🚨 ACCIDENT DETECTED — EMERGENCY PROTOCOL ACTIVE", (20, 34),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)

    return frame

def generate_video_stream() -> Generator[bytes, None, None]:
    """Generates MJPEG video stream with real-time YOLO tracking and collision evaluation."""
    global telemetry_state
    
    while True:
        frame = camera_stream.get_frame()
        if frame is None:
            time.sleep(0.02)
            continue

        # Run ByteTrack Tracking & Detection
        tracks = tracker.track(frame)
        
        # Check Collisions
        incident = collision_detector.check_collisions(tracks, frame)
        if incident:
            telemetry_state["active_collision"] = True
            telemetry_state["last_incident"] = incident
            # Process alert and PDF in a background thread (non-blocking for video stream)
            threading.Thread(
                target=process_accident_incident,
                args=(incident,),
                daemon=True,
                name=f"incident-{incident['incident_id']}"
            ).start()

        # Update telemetry
        telemetry_state["fps"] = camera_stream.fps or 30.0
        telemetry_state["active_vehicles"] = len(tracks)
        telemetry_state["is_synthetic"] = camera_stream.is_synthetic

        # Render HUD annotations
        is_colliding = telemetry_state["active_collision"]
        annotated_frame = draw_hud_overlays(frame, tracks, is_colliding)

        # Encode JPEG
        ret, buffer = cv2.imencode(".jpg", annotated_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        if not ret:
            continue

        frame_bytes = buffer.tobytes()
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
        
        time.sleep(0.015)


# Routes
@app.get("/", response_class=HTMLResponse)
def get_dashboard(request: Request, db: Session = Depends(get_db)):
    """Renders main operations dashboard."""
    hospitals = find_nearest_hospitals()
    primary_hospital = hospitals[0] if hospitals else {}
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "location_name": settings.LOCATION_NAME,
            "latitude": settings.LATITUDE,
            "longitude": settings.LONGITUDE,
            "hospitals": hospitals,
            "primary_hospital": primary_hospital,
        }
    )

@app.get("/api/stream")
def video_feed():
    """MJPEG Live video feed streaming endpoint."""
    return StreamingResponse(
        generate_video_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/api/telemetry")
def get_telemetry():
    """Returns real-time system metrics, FPS, and collision status."""
    return JSONResponse(telemetry_state)

@app.get("/api/incidents")
def list_incidents(db: Session = Depends(get_db)):
    """Returns historical list of logged accident incidents."""
    incidents = db.query(Incident).order_by(Incident.timestamp.desc()).limit(50).all()
    return JSONResponse([inc.to_dict() for inc in incidents])

@app.get("/api/reports/{incident_id}/pdf")
def download_pdf_report(incident_id: str, db: Session = Depends(get_db)):
    """Downloads or views the official PDF accident incident report."""
    incident = db.query(Incident).filter(Incident.incident_id == incident_id).first()
    if not incident or not incident.pdf_path or not os.path.exists(incident.pdf_path):
        # Check standard filename in reports directory
        fallback_pdf = settings.REPORTS_DIR / f"{incident_id}_Report.pdf"
        if fallback_pdf.exists():
            return FileResponse(str(fallback_pdf), media_type="application/pdf", filename=f"{incident_id}_Report.pdf")
        raise HTTPException(status_code=404, detail="Incident PDF report not found.")
    
    return FileResponse(incident.pdf_path, media_type="application/pdf", filename=f"{incident_id}_Report.pdf")

@app.get("/api/screenshots/{incident_id}")
def get_incident_screenshot(incident_id: str, db: Session = Depends(get_db)):
    """Serves the captured collision frame image."""
    incident = db.query(Incident).filter(Incident.incident_id == incident_id).first()
    if incident and incident.screenshot_path and os.path.exists(incident.screenshot_path):
        return FileResponse(incident.screenshot_path, media_type="image/jpeg")
    
    fallback_shot = settings.SCREENSHOTS_DIR / f"{incident_id}_collision.jpg"
    if fallback_shot.exists():
        return FileResponse(str(fallback_shot), media_type="image/jpeg")
        
    raise HTTPException(status_code=404, detail="Screenshot not found.")

@app.post("/api/simulate-collision")
def simulate_collision(background_tasks: BackgroundTasks):
    """Triggers an instantaneous simulated collision for demo and testing verification."""
    global telemetry_state
    
    incident_count = collision_detector.incident_count + 1
    collision_detector.incident_count = incident_count
    year = datetime.now().year
    incident_id = f"RAKSHA-{year}-{incident_count:03d}"

    # Capture current or dummy frame
    frame = camera_stream.get_frame()
    if frame is None:
        frame = 40 * np.ones((540, 960, 3), dtype=np.uint8)

    # Annotate test frame
    cv2.putText(frame, f"COLLISION SIMULATION: {incident_id}", (30, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    screenshot_path = str(settings.SCREENSHOTS_DIR / f"{incident_id}_collision.jpg")
    cv2.imwrite(screenshot_path, frame)

    sim_incident = {
        "incident_id": incident_id,
        "timestamp": datetime.utcnow().isoformat(),
        "timestamp_str": datetime.now().strftime("%d %B %Y, %I:%M:%S %p"),
        "location_name": settings.LOCATION_NAME,
        "latitude": settings.LATITUDE,
        "longitude": settings.LONGITUDE,
        "severity": "Critical",
        "severity_reason": "High-velocity simulated impact with abrupt vehicular halt.",
        "emergency_priority": "P1 - IMMEDIATE",
        "ai_confidence": 95,
        "vehicles_involved": 2,
        "vehicle_ids": "01, 02",
        "iou": 0.38,
        "distance": 18.5,
        "screenshot_path": screenshot_path
    }

    telemetry_state["active_collision"] = True
    telemetry_state["last_incident"] = sim_incident

    # Process notification & DB record
    background_tasks.add_task(process_accident_incident, sim_incident)
    return JSONResponse({"status": "success", "incident": sim_incident})

@app.post("/api/toggle-camera")
def toggle_camera():
    """Toggles between physical laptop webcam and synthetic simulation feed."""
    new_mode = not camera_stream.is_synthetic
    camera_stream.switch_to_synthetic(new_mode)
    telemetry_state["is_synthetic"] = new_mode
    return JSONResponse({"status": "success", "synthetic_mode": new_mode})

@app.post("/api/reset-alert")
def reset_alert():
    """Resets the active collision alert state."""
    telemetry_state["active_collision"] = False
    return JSONResponse({"status": "success", "active_collision": False})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
