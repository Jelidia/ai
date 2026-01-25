"""
Vision module - Face detection - OPTIMIZED FOR SPEED
"""
from __future__ import annotations
import threading
import time
import base64
from dataclasses import dataclass
from typing import Callable
import cv2
import mediapipe as mp
import config


@dataclass
class FaceEvent:
    present: bool
    timestamp: float
    frame_b64: str | None = None  # Base64 encoded frame for web UI


class FacePresence:
    """Face detection - OPTIMIZED for speed and web streaming."""
    
    def __init__(self, on_change: Callable[[FaceEvent], None] | None = None, 
                 on_frame: Callable[[str], None] | None = None):
        self.on_change = on_change
        self.on_frame = on_frame  # Callback for each frame (base64)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._present = False
        self._present_streak = 0
        self._absent_streak = 0
        self._last_event_time = 0.0
        self._cap = None
        self._frame_count = 0

    def start(self):
        self._stop.clear()
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=2)
        if self._cap:
            self._cap.release()

    def is_present(self) -> bool:
        return self._present

    def _emit(self, present: bool, frame_b64: str | None = None):
        now = time.time()
        self._last_event_time = now
        
        if self.on_change:
            try:
                self.on_change(FaceEvent(present=present, timestamp=now, frame_b64=frame_b64))
            except Exception as e:
                print(f"[VISION] on_change error: {e}")

    def _run(self):
        self._cap = cv2.VideoCapture(config.CAMERA_INDEX)
        if not self._cap.isOpened():
            print("[VISION] Could not open camera!")
            return

        # Optimize camera settings
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 480)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
        self._cap.set(cv2.CAP_PROP_FPS, 15)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        print(f"[VISION] Camera ready")

        mp_face = mp.solutions.face_detection
        face_detector = mp_face.FaceDetection(
            model_selection=0,
            min_detection_confidence=float(config.FACE_MIN_CONFIDENCE)
        )

        try:
            while not self._stop.is_set():
                ok, frame = self._cap.read()
                if not ok:
                    time.sleep(0.02)
                    continue

                self._frame_count += 1
                
                # Process every N frames
                do_process = (self._frame_count % config.VISION_PROCESS_EVERY_N_FRAMES == 0)

                detections = None
                if do_process:
                    small = cv2.resize(frame, (240, 180))
                    rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
                    result = face_detector.process(rgb)
                    detections = result.detections if result else None
                    face_seen = bool(detections)

                    if face_seen:
                        self._present_streak += 1
                        self._absent_streak = 0
                    else:
                        self._absent_streak += 1
                        self._present_streak = 0

                    # State transitions
                    if (not self._present) and (self._present_streak >= config.FACE_PRESENT_FRAMES_REQUIRED):
                        self._present = True
                        self._emit(True)

                    if self._present and (self._absent_streak >= config.FACE_ABSENT_FRAMES_REQUIRED):
                        self._present = False
                        self._emit(False)

                # Send frame to web UI (every 3rd frame for bandwidth)
                if self.on_frame and self._frame_count % 3 == 0:
                    # Draw face box
                    disp = frame.copy()
                    if detections:
                        h, w = disp.shape[:2]
                        for d in detections:
                            box = d.location_data.relative_bounding_box
                            x1 = int(box.xmin * w)
                            y1 = int(box.ymin * h)
                            x2 = int((box.xmin + box.width) * w)
                            y2 = int((box.ymin + box.height) * h)
                            color = (0, 255, 0) if self._present else (0, 165, 255)
                            cv2.rectangle(disp, (x1, y1), (x2, y2), color, 2)

                    # Status text
                    status = "FACE: YES" if self._present else "FACE: NO"
                    color = (0, 255, 0) if self._present else (0, 0, 255)
                    cv2.putText(disp, status, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

                    # Encode to base64
                    _, buffer = cv2.imencode('.jpg', disp, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    frame_b64 = base64.b64encode(buffer).decode('utf-8')
                    
                    try:
                        self.on_frame(frame_b64)
                    except Exception:
                        pass

        finally:
            self._cap.release()