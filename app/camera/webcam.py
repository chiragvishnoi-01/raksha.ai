"""RAKSHA AI - Webcam & Video Feed Ingestion"""
import cv2
import time
import threading
import numpy as np
import logging
from typing import Optional, Tuple
from app.config import settings

logger = logging.getLogger("raksha.camera")

class CameraStream:
    """Threaded camera capture to maintain high frame rate and zero latency."""
    
    def __init__(self, camera_index: int = None):
        self.camera_index = camera_index if camera_index is not None else settings.CAMERA_INDEX
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running = False
        self.lock = threading.Lock()
        self.current_frame: Optional[np.ndarray] = None
        self.thread: Optional[threading.Thread] = None
        self.is_synthetic = False
        self.synthetic_tick = 0
        self.synthetic_collided = False
        self.fps = 0.0
        self._last_fps_time = time.time()
        self._frame_count = 0
        
        self.start()

    def _init_capture(self) -> bool:
        """Initializes OpenCV video capture device."""
        try:
            # On Windows, cv2.CAP_DSHOW often gives fast startup without delay
            self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                # Fallback to default backend
                self.cap = cv2.VideoCapture(self.camera_index)
                
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                ret, test_frame = self.cap.read()
                if ret and test_frame is not None:
                    logger.info(f"Connected successfully to physical webcam index {self.camera_index} ({test_frame.shape[1]}x{test_frame.shape[0]})")
                    self.is_synthetic = False
                    return True
                else:
                    logger.warning("Webcam opened but failed to read initial frame.")
        except Exception as e:
            logger.warning(f"Error initializing hardware camera index {self.camera_index}: {e}")

        if settings.MOCK_CAMERA_FALLBACK:
            logger.info("Enabling synthetic simulation camera mode.")
            self.is_synthetic = True
            return True
            
        return False

    def start(self):
        """Starts the capture background thread."""
        if self.is_running:
            return
            
        success = self._init_capture()
        if not success:
            logger.error("Could not start camera stream.")
            return

        self.is_running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def _create_synthetic_frame(self) -> np.ndarray:
        """Generates a dynamic highway road scene with moving vehicles for demo/testing."""
        width, height = 960, 540
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Draw asphalt roadway
        frame[100:440, :] = (40, 44, 52) # Dark asphalt
        # Lane divider stripes
        self.synthetic_tick += 1
        offset = (self.synthetic_tick * 10) % 80
        for x in range(-offset, width + 80, 80):
            cv2.line(frame, (x, 270), (x + 40, 270), (255, 255, 255), 4)
            
        # Top and bottom road boundary lines
        cv2.line(frame, (0, 100), (width, 100), (200, 200, 200), 3)
        cv2.line(frame, (0, 440), (width, 440), (200, 200, 200), 3)

        # Draw vehicle A (approaching from left)
        # In simulation mode, vehicles approach each other and collide periodically
        cycle = (self.synthetic_tick // 4) % 180
        
        if cycle < 80:
            # Vehicles approaching each other
            pos_a_x = 120 + cycle * 4
            pos_b_x = 840 - cycle * 4
            self.synthetic_collided = False
        elif cycle < 130:
            # Vehicles in collision state
            pos_a_x = 440
            pos_b_x = 480
            self.synthetic_collided = True
        else:
            # Reset
            pos_a_x = 120
            pos_b_x = 840
            self.synthetic_collided = False

        # Draw Car 1 (Red Sedan)
        car1_box = (int(pos_a_x), 210, 110, 55)
        cv2.rectangle(frame, (car1_box[0], car1_box[1]), (car1_box[0] + car1_box[2], car1_box[1] + car1_box[3]), (30, 30, 220), -1)
        cv2.rectangle(frame, (car1_box[0], car1_box[1]), (car1_box[0] + car1_box[2], car1_box[1] + car1_box[3]), (255, 255, 255), 2)
        cv2.putText(frame, "SIM-VEHICLE 01", (car1_box[0], car1_box[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (50, 150, 255), 1)

        # Draw Car 2 (Blue SUV)
        car2_box = (int(pos_b_x), 225, 115, 60)
        cv2.rectangle(frame, (car2_box[0], car2_box[1]), (car2_box[0] + car2_box[2], car2_box[1] + car2_box[3]), (220, 140, 30), -1)
        cv2.rectangle(frame, (car2_box[0], car2_box[1]), (car2_box[0] + car2_box[2], car2_box[1] + car2_box[3]), (255, 255, 255), 2)
        cv2.putText(frame, "SIM-VEHICLE 02", (car2_box[0], car2_box[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 150, 50), 1)

        # Add simulation watermark banner
        cv2.putText(frame, "RAKSHA AI CAMERA FEED [HARDWARE TEST / SIMULATION]", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 220, 255), 2)
        return frame

    def _capture_loop(self):
        """Continuous frame reading loop."""
        while self.is_running:
            if not self.is_synthetic and self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    with self.lock:
                        self.current_frame = frame
                else:
                    time.sleep(0.01)
            else:
                # Synthetic generator at ~30 FPS
                frame = self._create_synthetic_frame()
                with self.lock:
                    self.current_frame = frame
                time.sleep(0.033)

            # Update FPS tracking
            self._frame_count += 1
            now = time.time()
            if now - self._last_fps_time >= 1.0:
                self.fps = round(self._frame_count / (now - self._last_fps_time), 1)
                self._frame_count = 0
                self._last_fps_time = now

    def get_frame(self) -> Optional[np.ndarray]:
        """Returns a copy of the latest captured frame."""
        with self.lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
        return None

    def switch_to_synthetic(self, enable: bool = True):
        """Forces synthetic simulation mode or switches back to physical webcam."""
        with self.lock:
            self.is_synthetic = enable
            logger.info(f"Camera synthetic mode set to: {enable}")

    def stop(self):
        """Stops capturing and releases video hardware."""
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.cap and self.cap.isOpened():
            self.cap.release()
        logger.info("Camera stream closed.")

# Global camera singleton instance
camera_stream = CameraStream()
