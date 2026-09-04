# RAKSHA AI — Intelligent Road Accident Detection & Response System

**RAKSHA AI** is a modular, high-performance road safety and automated emergency response platform. Designed for highway surveillance and connected traffic ecosystems, this prototype demonstrates real-time vehicle detection, ByteTrack trajectory tracking, kinematic collision detection, rule-based severity analysis, location identification, automated multi-agency alerts (Hospital & NHAI), and ReportLab forensic PDF incident reports.

---

## 🌟 Prototype Architecture

```text
Laptop Webcam / Highway Video Feed
              ↓
    OpenCV Frame Ingestion
              ↓
  YOLOv8 Multi-Vehicle Detection
              ↓
  ByteTrack Trajectory & Kinematics
              ↓
 Rule-Based Spatial Collision Engine
              ↓
     🚨 ACCIDENT DETECTED
              ↓
   Rule-Based Severity Assessor
  (Minor / Moderate / Critical)
              ↓
 Location & Hospital GPS Resolver
 (Google Maps / Kanpur Emergency Hub)
              ↓
 ┌──────────────┬──────────────┬──────────────┐
 ↓              ↓              ↓
Hospital       NHAI          Police
Email Alert    Email Alert   Control (112)
      ↓
 Automatic PDF Dossier Generation (ReportLab)
      ↓
 SQLite / PostgreSQL Forensic Database
      ↓
 Live Command Center Telemetry Dashboard
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Built-in laptop webcam or USB camera

### 2. Setup & Environment
The required dependencies are listed in `requirements.txt`.
```bash
pip install -r requirements.txt
```

Verify or configure your `.env` file (a ready-to-use template is provided with default demo coordinates for the **NH-27 Highway Corridor, Kanpur, Uttar Pradesh**):
```ini
CAMERA_INDEX=0
DEMO_LOCATION_NAME="NH-27 Highway, Kanpur, Uttar Pradesh, India"
DEMO_LATITUDE=26.4499
DEMO_LONGITUDE=80.3319
```

### 3. Launch RAKSHA AI
Run the application with Uvicorn:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open your browser and navigate to:
```text
http://localhost:8000
```

---

## 🎯 How to Demonstrate the Prototype

### Method A: Live Physical Demonstration with Toy / Fake Vehicles
1. Open the dashboard at `http://localhost:8000`.
2. Position your laptop webcam facing a flat surface or tabletop.
3. Place **2 toy vehicles** (e.g. toy cars, die-cast models, or toy trucks) in front of the camera.
4. **YOLOv8** will detect both vehicles, and **ByteTrack** will assign persistent identification numbers (e.g. `CAR #01`, `CAR #02`) with trajectory motion trails.
5. Move the two vehicles toward each other and make them collide or overlap strongly.
6. The system instantly detects the collision:
   - Live stream flashes `🚨 ACCIDENT DETECTED` with red impact telemetry.
   - Emergency audio siren alerts the room.
   - Severity is computed (`Critical` / `Moderate`).
   - Closest trauma center is selected with ambulance travel time (e.g. *Regency Hospital* / *LLR Hospital*).
   - Automated dispatch emails are generated and sent to Hospital and NHAI control rooms.
   - A high-resolution forensic snapshot frame is saved to `screenshots/`.
   - An official PDF accident dossier is generated in `reports/`.
   - The incident appears immediately in the **Incident History & Dispatch Archive** table.

### Method B: One-Click Digital Simulation
If you are presenting without toy cars or in an environment without camera access:
1. Click the **"💥 Trigger Simulated Collision"** button on the dashboard.
2. The system triggers the full automated pipeline end-to-end, logs the collision snapshot, dispatches alerts, builds the PDF, and adds it to the archive in real time.

---

## 📁 Project Structure

```text
raksha.ai/
├── app/
│   ├── main.py                  # Master FastAPI app & MJPEG telemetry server
│   ├── config.py                # Environment configuration & directories
│   ├── camera/
│   │   └── webcam.py            # OpenCV threaded capture with synthetic fallback
│   ├── ai/
│   │   ├── detector.py          # YOLOv8 vehicle & pedestrian detector
│   │   ├── tracker.py           # ByteTrack trajectory & kinematic tracking
│   │   ├── collision.py         # Spatial overlap & sudden velocity change detection
│   │   └── severity.py          # Rule-based severity rating (Minor/Moderate/Critical)
│   ├── location/
│   │   └── maps.py              # Google Maps API & Kanpur emergency hospital directory
│   ├── alerts/
│   │   └── email.py             # Hospital & NHAI multi-agency email dispatcher
│   ├── reports/
│   │   └── pdf.py               # ReportLab forensic PDF incident report generator
│   ├── database/
│   │   ├── database.py          # SQLAlchemy engine (PostgreSQL + SQLite fallback)
│   │   └── models.py            # Incident database model
│   └── dashboard/
│       ├── templates/
│       │   └── index.html       # Futuristic cyber emergency command center UI
│       └── static/
│           ├── css/style.css    # Dark glassmorphic HUD styling & animations
│           └── js/app.js        # Real-time polling, Web Audio siren, modal controller
├── models/                      # YOLOv8 weights cache
├── reports/                     # Generated PDF accident reports
├── screenshots/                 # Captured collision evidence snapshots
├── test_pipeline.py             # Automated end-to-end verification test suite
├── requirements.txt
├── .env
└── README.md
```

---

## 🛡️ Good Samaritan Legal Safeguards (Section 134A)
In compliance with the **Motor Vehicles (Amendment) Act** and Ministry of Road Transport and Highways (MoRTH) guidelines, RAKSHA AI embeds statutory Good Samaritan protections into every generated accident report, reaffirming that bystanders and first-responders who assist victims are free from civil or criminal liability, and emergency trauma admissions cannot be delayed.

---

## 🔮 Future Scalability
- **Connected Dashcams**: Community hazard detection and multi-view accident verification.
- **Good Samaritan Captive Portal**: Educational awareness videos delivered at highway rest stops and petrol pumps.
- **Safety Reward Points**: Citizen rewards for verified pothole and hazard reporting.
- **Road Safety Intelligence Heatmap**: Identification of blackspots and high-risk road corridors for NHAI engineers.
