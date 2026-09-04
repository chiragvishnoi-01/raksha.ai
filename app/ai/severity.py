"""RAKSHA AI - Rule-Based Accident Severity Assessment"""
from typing import Dict, Any, List

class SeverityAssessor:
    """Evaluates accident telemetry to determine clinical/highway emergency severity.
    - Minor: Low collision overlap / low delta-v, vehicles continue moving.
    - Moderate: Strong collision / abnormal trajectory deflection or deceleration.
    - Critical: High impact / abrupt stop / pedestrian involvement.
    """

    @staticmethod
    def assess(
        iou: float,
        speed_delta: float,
        vehicles_stopped: bool,
        pedestrian_involved: bool,
        mean_conf: float
    ) -> Dict[str, Any]:
        """Calculates severity rating and overall AI confidence score."""
        if pedestrian_involved:
            severity = "Critical"
            reason = "Pedestrian/vulnerable road user involved in collision zone."
            confidence = min(0.98, max(0.85, mean_conf + 0.05))
        elif vehicles_stopped and (iou > 0.25 or speed_delta > 15):
            severity = "Critical"
            reason = "High impact collision with sudden complete vehicular halt."
            confidence = min(0.96, max(0.82, mean_conf + 0.04))
        elif iou > 0.15 or speed_delta > 8:
            severity = "Moderate"
            reason = "Significant collision overlap and abnormal kinematic deflection."
            confidence = min(0.92, max(0.78, mean_conf))
        else:
            severity = "Minor"
            reason = "Low velocity glance or proximity contact; vehicles maintained movement."
            confidence = min(0.88, max(0.70, mean_conf - 0.05))

        return {
            "severity": severity,
            "reason": reason,
            "ai_confidence": round(confidence, 2),
            "emergency_priority": "P1 - IMMEDIATE" if severity == "Critical" else "P2 - URGENT" if severity == "Moderate" else "P3 - ROUTINE"
        }
