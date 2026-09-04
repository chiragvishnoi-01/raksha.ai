"""RAKSHA AI - Core Configuration Module"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    PROJECT_NAME: str = "RAKSHA AI — Intelligent Road Accident Detection & Response System"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
    
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Camera
    CAMERA_INDEX: int = int(os.getenv("CAMERA_INDEX", "0"))
    MOCK_CAMERA_FALLBACK: bool = os.getenv("MOCK_CAMERA_FALLBACK", "True").lower() in ("true", "1", "yes")
    
    # Location (Kanpur default)
    LOCATION_NAME: str = os.getenv("DEMO_LOCATION_NAME", "NH-27 Highway, Kanpur, Uttar Pradesh, India")
    LATITUDE: float = float(os.getenv("DEMO_LATITUDE", "26.4499"))
    LONGITUDE: float = float(os.getenv("DEMO_LONGITUDE", "80.3319"))
    
    # Google Maps
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
    
    # Email / SMTP
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    ALERT_SENDER: str = os.getenv("ALERT_SENDER", "raksha-alert@safety.gov.in")
    HOSPITAL_ALERT_EMAIL: str = os.getenv("HOSPITAL_ALERT_EMAIL", "emergency-trauma@llr-hospital.org")
    NHAI_ALERT_EMAIL: str = os.getenv("NHAI_ALERT_EMAIL", "control-room@nhai.gov.in")
    EMERGENCY_SERVICES_EMAIL: str = os.getenv("EMERGENCY_SERVICES_EMAIL", "police-control@up112.gov.in")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./raksha.db")
    
    # AI & Collision
    YOLO_MODEL: str = os.getenv("YOLO_MODEL", "yolov8n.pt")
    COLLISION_IOU_THRESHOLD: float = float(os.getenv("COLLISION_IOU_THRESHOLD", "0.08"))
    COLLISION_DISTANCE_THRESHOLD: float = float(os.getenv("COLLISION_DISTANCE_THRESHOLD", "180.0"))
    COLLISION_COOLDOWN_SECONDS: float = float(os.getenv("COLLISION_COOLDOWN_SECONDS", "10.0"))
    AI_CONFIDENCE_THRESHOLD: float = float(os.getenv("AI_CONFIDENCE_THRESHOLD", "0.35"))
    
    # Demo Mode — when True, ANY detected objects (not just vehicles) can trigger collisions
    DEMO_MODE: bool = os.getenv("DEMO_MODE", "True").lower() in ("true", "1", "yes")
    
    # Paths
    REPORTS_DIR: Path = BASE_DIR / "reports"
    SCREENSHOTS_DIR: Path = BASE_DIR / "screenshots"
    MODELS_DIR: Path = BASE_DIR / "models"

settings = Settings()

# Ensure target directories exist
settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
settings.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
settings.MODELS_DIR.mkdir(parents=True, exist_ok=True)
