"""RAKSHA AI - YOLO Vehicle & Pedestrian Detector"""
import os
import logging
import numpy as np
from typing import List, Dict, Any, Optional
from pathlib import Path
from app.config import settings

logger = logging.getLogger("raksha.detector")

# Extended COCO Class mapping (Vehicles, Pedestrians, and Handheld/Everyday Objects)
# If None, detector will automatically detect all classes known to the model
COMMON_CLASSES = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
    24: "backpack",
    26: "handbag",
    39: "bottle",
    41: "cup",
    63: "laptop",
    64: "mouse",
    65: "remote",
    66: "keyboard",
    67: "cell phone",
    73: "book"
}

class VehicleDetector:
    """Ultralytics YOLOv8 Vehicle Detector."""

    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.YOLO_MODEL
        self.model = None
        self._is_loaded = False
        self._load_model()

    def _load_model(self):
        """Loads YOLO model with weights saved to models directory."""
        try:
            from ultralytics import YOLO
            # Keep weights in models directory
            model_path = settings.MODELS_DIR / self.model_name
            if not model_path.exists():
                logger.info(f"Downloading/loading YOLO model: {self.model_name}")
                self.model = YOLO(self.model_name)
                # Save into models dir if downloaded
            else:
                self.model = YOLO(str(model_path))
                
            self._is_loaded = True
            logger.info("YOLO Vehicle Detector loaded successfully.")
        except Exception as e:
            logger.warning(f"Could not load YOLO model ({e}). Detector will run in fallback simulation mode.")
            self._is_loaded = False

    @property
    def is_active(self) -> bool:
        return self._is_loaded

    def detect(self, frame: np.ndarray, conf_threshold: float = None) -> List[Dict[str, Any]]:
        """Performs vehicle detection on a single frame.
        Returns list of detections with bounding box and class labels.
        """
        conf_thr = conf_threshold or settings.AI_CONFIDENCE_THRESHOLD
        detections = []

        if self._is_loaded and self.model is not None:
            try:
                results = self.model(frame, verbose=False, conf=conf_thr)
                if results and len(results) > 0:
                    r = results[0]
                    boxes = r.boxes
                    if boxes is not None:
                        for box in boxes:
                            cls_id = int(box.cls[0].item())
                            conf = float(box.conf[0].item())
                            
                            # Get class name dynamically from YOLO model or fallback
                            cls_name = "object"
                            if hasattr(self.model, "names") and cls_id in self.model.names:
                                cls_name = self.model.names[cls_id]
                            elif cls_id in COMMON_CLASSES:
                                cls_name = COMMON_CLASSES[cls_id]
                            
                            x1, y1, x2, y2 = box.xyxy[0].tolist()
                            cx = int((x1 + x2) / 2)
                            cy = int((y1 + y2) / 2)
                            detections.append({
                                "class_id": cls_id,
                                "class_name": cls_name,
                                "confidence": round(conf, 2),
                                "box": [int(x1), int(y1), int(x2), int(y2)],
                                "center": (cx, cy)
                            })
                return detections
            except Exception as e:
                logger.error(f"Error during YOLO inference: {e}")

        return detections
