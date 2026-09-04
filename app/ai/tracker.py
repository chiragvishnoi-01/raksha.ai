"""RAKSHA AI - ByteTrack Vehicle Tracking & Trajectory Telemetry"""
import math
import logging
import numpy as np
from collections import deque
from typing import List, Dict, Any, Optional
from app.config import settings

logger = logging.getLogger("raksha.tracker")

TARGET_CLASSES = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}

class TrackedVehicle:
    """Represents an actively tracked vehicle with trajectory kinematics."""
    def __init__(self, track_id: int, class_name: str, box: List[int], confidence: float):
        self.track_id = track_id
        self.class_name = class_name
        self.box = box
        self.confidence = confidence
        self.center = (int((box[0] + box[2]) / 2), int((box[1] + box[3]) / 2))
        self.history = deque(maxlen=30)
        self.history.append(self.center)
        self.velocity = (0.0, 0.0)
        self.speed = 0.0
        self.disappeared_frames = 0

    def update(self, box: List[int], confidence: float):
        self.box = box
        self.confidence = confidence
        new_center = (int((box[0] + box[2]) / 2), int((box[1] + box[3]) / 2))
        
        # Calculate velocity vector
        if len(self.history) > 0:
            prev_cx, prev_cy = self.history[-1]
            vx = new_center[0] - prev_cx
            vy = new_center[1] - prev_cy
            self.velocity = (vx, vy)
            self.speed = round(math.sqrt(vx**2 + vy**2), 1)
            
        self.center = new_center
        self.history.append(new_center)
        self.disappeared_frames = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "class_name": self.class_name,
            "box": self.box,
            "center": self.center,
            "confidence": self.confidence,
            "velocity": self.velocity,
            "speed": self.speed,
            "history": list(self.history)
        }

class VehicleTracker:
    """Multi-object tracker with ByteTrack integration and internal fallback tracking."""

    def __init__(self, detector=None):
        self.detector = detector
        self.tracked_objects: Dict[int, TrackedVehicle] = {}
        self._next_fallback_id = 1
        self._use_bytetrack = True

    def track(self, frame: np.ndarray) -> List[TrackedVehicle]:
        """Tracks vehicles across consecutive video frames using ByteTrack."""
        current_tracks: List[TrackedVehicle] = []

        # 1. Attempt ByteTrack tracking via Ultralytics model if available
        if self._use_bytetrack and self.detector and self.detector.model is not None:
            try:
                results = self.detector.model.track(
                    frame,
                    persist=True,
                    tracker="bytetrack.yaml",
                    verbose=False,
                    conf=(0.22 if settings.DEMO_MODE else settings.AI_CONFIDENCE_THRESHOLD)
                )
                
                if results and len(results) > 0:
                    r = results[0]
                    boxes = r.boxes
                    if boxes is not None and len(boxes) > 0:
                        active_ids = set()
                        for i, box in enumerate(boxes):
                            cls_id = int(box.cls[0].item())
                            conf = float(box.conf[0].item())
                            
                            # Use ByteTrack ID if available, otherwise fallback to object index + 1
                            if box.id is not None:
                                track_id = int(box.id[0].item())
                            else:
                                track_id = i + 1
                                
                            active_ids.add(track_id)
                            
                            x1, y1, x2, y2 = box.xyxy[0].tolist()
                            box_coords = [int(x1), int(y1), int(x2), int(y2)]
                            
                            # Resolve class name dynamically from model names
                            cls_name = "vehicle"
                            if hasattr(self.detector.model, "names") and cls_id in self.detector.model.names:
                                cls_name = self.detector.model.names[cls_id]
                            elif cls_id in TARGET_CLASSES:
                                cls_name = TARGET_CLASSES[cls_id]

                            if track_id in self.tracked_objects:
                                self.tracked_objects[track_id].update(box_coords, conf)
                            else:
                                self.tracked_objects[track_id] = TrackedVehicle(track_id, cls_name, box_coords, conf)

                            current_tracks.append(self.tracked_objects[track_id])

                        # Cleanup expired tracks
                        to_delete = [tid for tid in self.tracked_objects if tid not in active_ids]
                        for tid in to_delete:
                            del self.tracked_objects[tid]

                        return current_tracks
            except Exception as e:
                logger.debug(f"ByteTrack API fallback: {e}")
                self._use_bytetrack = False

        # 2. Fallback Centroid/IoU Tracker
        # Runs if ByteTrack tracker yaml is loading or when using raw detections
        raw_detections = self.detector.detect(frame) if self.detector else []
        return self._centroid_track_fallback(raw_detections)

    def _centroid_track_fallback(self, detections: List[Dict[str, Any]]) -> List[TrackedVehicle]:
        """Simple, robust distance-based fallback tracker."""
        if not detections:
            # Mark disappearance
            for tid in list(self.tracked_objects.keys()):
                self.tracked_objects[tid].disappeared_frames += 1
                if self.tracked_objects[tid].disappeared_frames > 15:
                    del self.tracked_objects[tid]
            return []

        matched_tracks = []
        unmatched_dets = list(detections)

        # Match with existing tracks by Euclidean centroid proximity
        for tid, obj in list(self.tracked_objects.items()):
            best_idx = -1
            min_dist = float("inf")
            for i, det in enumerate(unmatched_dets):
                dx = obj.center[0] - det["center"][0]
                dy = obj.center[1] - det["center"][1]
                dist = math.sqrt(dx**2 + dy**2)
                if dist < 120 and dist < min_dist:
                    min_dist = dist
                    best_idx = i

            if best_idx >= 0:
                det = unmatched_dets.pop(best_idx)
                obj.update(det["box"], det["confidence"])
                matched_tracks.append(obj)
            else:
                obj.disappeared_frames += 1
                if obj.disappeared_frames > 15:
                    del self.tracked_objects[tid]

        # Register new objects for remaining detections
        for det in unmatched_dets:
            new_id = self._next_fallback_id
            self._next_fallback_id += 1
            new_obj = TrackedVehicle(new_id, det["class_name"], det["box"], det["confidence"])
            self.tracked_objects[new_id] = new_obj
            matched_tracks.append(new_obj)

        return matched_tracks
