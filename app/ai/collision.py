"""RAKSHA AI - Rule-Based Road Collision Detection Engine"""
import cv2
import time
import math
import logging
from pathlib import Path
from datetime import datetime
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

from app.config import settings
from app.ai.tracker import TrackedVehicle
from app.ai.severity import SeverityAssessor

logger = logging.getLogger("raksha.collision")

def calculate_iou(boxA: List[int], boxB: List[int]) -> float:
    """Computes Intersection over Union (IoU) between two bounding boxes [x1, y1, x2, y2]."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    inter_width = max(0, xB - xA)
    inter_height = max(0, yB - yA)
    inter_area = inter_width * inter_height

    boxA_area = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxB_area = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

    union_area = float(boxA_area + boxB_area - inter_area)
    if union_area <= 0:
        return 0.0
    return inter_area / union_area

def calculate_distance(pt1: Tuple[int, int], pt2: Tuple[int, int]) -> float:
    """Computes Euclidean distance between two points."""
    return math.sqrt((pt1[0] - pt2[0])**2 + (pt1[1] - pt2[1])**2)

class CollisionDetector:
    """Evaluates spatial proximity, bounding box overlap, and kinematic changes to detect vehicle collisions."""

    # Vehicle classes that participate in collision detection
    VEHICLE_CLASSES = ("car", "truck", "bus", "motorcycle", "bicycle", "vehicle")

    def __init__(self):
        self.last_incident_time = 0.0
        # Per-pair overlap evidence tracker: {(id_a, id_b): {"frames": int, "last_seen": float}}
        self._pair_evidence: Dict[tuple, Dict[str, Any]] = {}
        self._evidence_window_sec = 2.0  # Max time window to accumulate evidence frames
        self._required_evidence_frames = 2  # Frames needed within the window to confirm collision
        self.active_collision = False
        self.incident_count = 0
        self.last_incident_data: Optional[Dict[str, Any]] = None

    def _get_pair_key(self, id_a: int, id_b: int) -> tuple:
        """Returns a canonical sorted pair key so (3,7) == (7,3)."""
        return (min(id_a, id_b), max(id_a, id_b))

    def _add_evidence(self, pair_key: tuple, now: float) -> int:
        """Adds one evidence frame for a pair. Returns accumulated frame count."""
        if pair_key in self._pair_evidence:
            entry = self._pair_evidence[pair_key]
            # If too much time has passed since last evidence, reset the counter
            if now - entry["last_seen"] > self._evidence_window_sec:
                entry["frames"] = 1
            else:
                entry["frames"] += 1
            entry["last_seen"] = now
        else:
            self._pair_evidence[pair_key] = {"frames": 1, "last_seen": now}
        return self._pair_evidence[pair_key]["frames"]

    def _cleanup_stale_evidence(self, now: float):
        """Removes pair evidence entries that are too old."""
        stale_keys = [k for k, v in self._pair_evidence.items() 
                      if now - v["last_seen"] > self._evidence_window_sec * 2]
        for k in stale_keys:
            del self._pair_evidence[k]

    def check_collisions(
        self,
        vehicles: List[TrackedVehicle],
        frame: np.ndarray,
        all_tracks: Optional[List[TrackedVehicle]] = None
    ) -> Optional[Dict[str, Any]]:
        """Analyzes all pairs of tracked vehicles for collision conditions."""
        now = time.time()
        
        # Cooldown guard — shorter in DEMO_MODE for faster re-testing
        cooldown = 5.0 if settings.DEMO_MODE else settings.COLLISION_COOLDOWN_SECONDS
        if now - self.last_incident_time < cooldown:
            return None

        # Periodic cleanup of stale per-pair evidence
        self._cleanup_stale_evidence(now)

        # In DEMO_MODE: ALL detected objects can collide (for testing with bottles, phones, etc.)
        # In production: only vehicle classes participate
        if settings.DEMO_MODE:
            veh_list = list(vehicles)  # Every detected object is a candidate
            pedestrians = []  # No special pedestrian handling in demo
            if veh_list:
                logger.debug(f"DEMO MODE: {len(veh_list)} objects eligible for collision check: "
                             f"{[f'{v.class_name}#{v.track_id}' for v in veh_list]}")
        else:
            veh_list = [v for v in vehicles if v.class_name in self.VEHICLE_CLASSES]
            pedestrians = [v for v in (all_tracks or vehicles) if v.class_name == "person"]

        detected_collision = None

        # In DEMO_MODE: only 1 evidence frame needed (instant detection)
        # In production: require 2 frames over 2 sec window for confirmation
        required_frames = 1 if settings.DEMO_MODE else self._required_evidence_frames

        for i in range(len(veh_list)):
            for j in range(i + 1, len(veh_list)):
                v1 = veh_list[i]
                v2 = veh_list[j]

                # 1. Spatial Overlap (IoU)
                iou = calculate_iou(v1.box, v2.box)
                
                # 2. Centroid Proximity Distance
                dist = calculate_distance(v1.center, v2.center)
                
                # 3. Kinematic delta: combined speed and sudden deceleration
                speed_delta = abs(v1.speed - v2.speed)
                v1_stopped = (v1.speed < 2.0)
                v2_stopped = (v2.speed < 2.0)
                both_stopped = (v1_stopped and v2_stopped)

                # Check Pedestrian proximity to either vehicle (< 90px)
                ped_involved = False
                for ped in pedestrians:
                    if calculate_distance(ped.center, v1.center) < 90 or calculate_distance(ped.center, v2.center) < 90:
                        ped_involved = True
                        break

                # Collision Condition:
                if settings.DEMO_MODE:
                    # DEMO: Any overlap OR objects within 250px of each other = collision
                    is_colliding = (iou > 0.01 or dist <= 250)
                else:
                    # PRODUCTION: Strong bounding box overlap OR close proximity with deceleration
                    is_colliding = (
                        iou >= settings.COLLISION_IOU_THRESHOLD or
                        (dist <= settings.COLLISION_DISTANCE_THRESHOLD and (iou > 0.05 or both_stopped))
                    )

                if is_colliding:
                    pair_key = self._get_pair_key(v1.track_id, v2.track_id)
                    evidence_count = self._add_evidence(pair_key, now)
                    
                    logger.debug(
                        f"Collision signal: pair=({v1.track_id},{v2.track_id}) "
                        f"IoU={iou:.3f} dist={dist:.1f} speed_delta={speed_delta:.1f} "
                        f"evidence={evidence_count}/{required_frames}"
                    )
                    
                    # Require enough evidence frames within the time window to confirm
                    if evidence_count >= required_frames:
                        self.incident_count += 1
                        self.last_incident_time = now
                        self.active_collision = True
                        
                        # Reset evidence for this pair after triggering
                        self._pair_evidence.pop(pair_key, None)
                        
                        # Calculate Severity & AI Confidence
                        mean_conf = (v1.confidence + v2.confidence) / 2.0
                        sev_info = SeverityAssessor.assess(
                            iou=iou,
                            speed_delta=speed_delta,
                            vehicles_stopped=both_stopped,
                            pedestrian_involved=ped_involved,
                            mean_conf=mean_conf
                        )

                        # Generate unique Incident ID: e.g. RAKSHA-2026-4821-001
                        year = datetime.now().year
                        ts_suffix = f"{int(time.time()) % 10000:04d}-{self.incident_count:03d}"
                        incident_id = f"RAKSHA-{year}-{ts_suffix}"
                        
                        # Save Screenshot evidence
                        annotated_frame = self._annotate_collision_frame(frame, v1, v2, sev_info["severity"], incident_id)
                        screenshot_path = self._save_screenshot(annotated_frame, incident_id)

                        detected_collision = {
                            "incident_id": incident_id,
                            "timestamp": datetime.utcnow().isoformat(),
                            "timestamp_str": datetime.now().strftime("%d %B %Y, %I:%M:%S %p"),
                            "location_name": settings.LOCATION_NAME,
                            "latitude": settings.LATITUDE,
                            "longitude": settings.LONGITUDE,
                            "severity": sev_info["severity"],
                            "severity_reason": sev_info["reason"],
                            "emergency_priority": sev_info["emergency_priority"],
                            "ai_confidence": int(sev_info["ai_confidence"] * 100),
                            "vehicles_involved": 2,
                            "vehicle_ids": f"{v1.track_id:02d}, {v2.track_id:02d}",
                            "iou": round(iou, 3),
                            "distance": round(dist, 1),
                            "screenshot_path": screenshot_path,
                            "pedestrian_involved": ped_involved
                        }
                        
                        self.last_incident_data = detected_collision
                        logger.warning(f"🚨 COLLISION DETECTED: {incident_id} | Severity: {sev_info['severity']} | IoU: {iou:.3f} | Dist: {dist:.1f}px")
                        return detected_collision

        return detected_collision

    def _annotate_collision_frame(
        self,
        frame: np.ndarray,
        v1: TrackedVehicle,
        v2: TrackedVehicle,
        severity: str,
        incident_id: str
    ) -> np.ndarray:
        """Annotates high-visibility collision warning on captured snapshot."""
        out = frame.copy()
        h, w = out.shape[:2]

        # Draw red collision bounding boxes
        for v in (v1, v2):
            b = v.box
            cv2.rectangle(out, (b[0], b[1]), (b[2], b[3]), (0, 0, 255), 3)
            cv2.putText(out, f"{v.class_name.upper()} #{v.track_id:02d}", (b[0], b[1] - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        # Draw impact line connecting centroids
        cv2.line(out, v1.center, v2.center, (0, 0, 255), 3)
        mid_x = int((v1.center[0] + v2.center[0]) / 2)
        mid_y = int((v1.center[1] + v2.center[1]) / 2)
        cv2.circle(out, (mid_x, mid_y), 15, (0, 0, 255), -1)

        # Top alert banner
        cv2.rectangle(out, (0, 0), (w, 65), (0, 0, 180), -1)
        alert_txt = f"🚨 RAKSHA AI — ACCIDENT DETECTED [{incident_id}]"
        cv2.putText(out, alert_txt, (20, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)

        # Bottom telemetry bar
        cv2.rectangle(out, (0, h - 45), (w, h), (15, 23, 42), -1)
        telemetry_txt = f"SEVERITY: {severity.upper()} | VEHICLES: {v1.track_id:02d} & {v2.track_id:02d} | LOC: {settings.LOCATION_NAME[:45]}"
        cv2.putText(out, telemetry_txt, (20, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 230, 255), 1)

        return out

    def _save_screenshot(self, frame: np.ndarray, incident_id: str) -> str:
        """Saves annotated collision frame to disk."""
        filename = f"{incident_id}_collision.jpg"
        filepath = settings.SCREENSHOTS_DIR / filename
        cv2.imwrite(str(filepath), frame)
        logger.info(f"Collision evidence snapshot saved: {filepath}")
        return str(filepath)
