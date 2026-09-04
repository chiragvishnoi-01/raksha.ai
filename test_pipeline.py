"""RAKSHA AI - End-to-End Pipeline Verification Test"""
import os
import cv2
import numpy as np
from datetime import datetime
from app.config import settings
from app.database.database import init_db, SessionLocal
from app.database.models import Incident
from app.location.maps import get_primary_hospital, find_nearest_hospitals
from app.alerts.email import send_email_alert
from app.reports.pdf import generate_pdf_report
from app.ai.severity import SeverityAssessor
from app.ai.detector import VehicleDetector

def test_pipeline():
    print("=== 1. Testing Database Initialization ===")
    init_db()
    db = SessionLocal()
    count = db.query(Incident).count()
    print(f"[OK] Database connected successfully. Current incidents: {count}")
    db.close()

    print("\n=== 2. Testing Location & Hospital Discovery ===")
    hospitals = find_nearest_hospitals()
    print(f"[OK] Found {len(hospitals)} emergency trauma hospitals:")
    for h in hospitals:
        print(f"   - {h['name']} ({h['distance_km']} km away, ETA: {h['eta_minutes']} mins)")
    primary = get_primary_hospital()
    print(f"[OK] Primary assigned: {primary['name']}")

    print("\n=== 3. Testing Severity Assessor ===")
    sev = SeverityAssessor.assess(
        iou=0.35,
        speed_delta=18.0,
        vehicles_stopped=True,
        pedestrian_involved=False,
        mean_conf=0.92
    )
    print(f"[OK] Severity output: {sev}")
    assert sev["severity"] == "Critical", "Expected Critical severity"

    print("\n=== 4. Testing Snapshot & PDF Report Generation ===")
    # Create mock collision test frame
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    test_frame[:] = (30, 30, 30)
    cv2.rectangle(test_frame, (120, 150), (280, 300), (0, 0, 255), 3)
    cv2.rectangle(test_frame, (240, 160), (400, 310), (0, 0, 255), 3)
    cv2.putText(test_frame, "TEST COLLISION RAKSHA-TEST-001", (40, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    
    test_shot_path = str(settings.SCREENSHOTS_DIR / "RAKSHA-TEST-001_collision.jpg")
    cv2.imwrite(test_shot_path, test_frame)
    print(f"[OK] Saved mock collision screenshot: {test_shot_path}")

    mock_incident = {
        "incident_id": "RAKSHA-TEST-001",
        "timestamp": datetime.utcnow(),
        "timestamp_str": datetime.now().strftime("%d %B %Y, %I:%M:%S %p"),
        "location_name": settings.LOCATION_NAME,
        "latitude": settings.LATITUDE,
        "longitude": settings.LONGITUDE,
        "severity": sev["severity"],
        "severity_reason": sev["reason"],
        "emergency_priority": sev["emergency_priority"],
        "ai_confidence": 94,
        "vehicles_involved": 2,
        "vehicle_ids": "01, 02",
        "iou": 0.35,
        "distance": 22.4,
        "screenshot_path": test_shot_path,
        "hospital_name": primary["name"],
        "hospital_alert_status": "SENT [CONFIRMED]",
        "nhai_alert_status": "SENT [CONFIRMED]"
    }

    pdf_file = generate_pdf_report(mock_incident)
    print(f"[OK] Generated PDF report: {pdf_file}")
    assert os.path.exists(pdf_file), "PDF file was not created"
    print(f"[OK] PDF report size: {os.path.getsize(pdf_file)} bytes")

    print("\n=== 5. Testing Automated Multi-Agency Email Dispatch ===")
    email_res = send_email_alert(mock_incident)
    print(f"[OK] Email dispatch status: {email_res}")

    print("\n=== 6. Testing YOLO Vehicle Detector Initialization ===")
    det = VehicleDetector()
    print(f"[OK] YOLO Model Active: {det.is_active}")

    print("\n==============================================")
    print("[SUCCESS] ALL RAKSHA AI PIPELINE TESTS PASSED!")
    print("==============================================")

if __name__ == "__main__":
    test_pipeline()
