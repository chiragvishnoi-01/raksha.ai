"""RAKSHA AI - Database Models"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    incident_id = Column(String(64), unique=True, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Location
    location_name = Column(String(255), default="Kanpur, Uttar Pradesh, India")
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # AI Incident telemetry
    severity = Column(String(32), default="Moderate", nullable=False) # Minor, Moderate, Critical
    ai_confidence = Column(Float, default=0.85)
    vehicles_involved = Column(Integer, default=2)
    vehicle_ids = Column(String(128), default="") # e.g. "01, 02"
    
    # Media artifacts
    screenshot_path = Column(String(512), nullable=True)
    pdf_path = Column(String(512), nullable=True)
    
    # External responders notification status
    hospital_name = Column(String(255), default="LLR / Hallet Hospital Emergency Trauma Unit")
    hospital_alert_status = Column(String(64), default="SENT")
    nhai_alert_status = Column(String(64), default="SENT")
    
    # Details & description
    details = Column(Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "location_name": self.location_name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "severity": self.severity,
            "ai_confidence": round(self.ai_confidence * 100, 1) if self.ai_confidence else 0.0,
            "vehicles_involved": self.vehicles_involved,
            "vehicle_ids": self.vehicle_ids,
            "screenshot_path": self.screenshot_path,
            "pdf_path": self.pdf_path,
            "hospital_name": self.hospital_name,
            "hospital_alert_status": self.hospital_alert_status,
            "nhai_alert_status": self.nhai_alert_status,
            "details": self.details,
        }
