"""
Vision module - Face detection and presence tracking.
Uses MediaPipe for fast, accurate face detection.
"""
from __future__ import annotations
import threading
import time
from dataclasses import dataclass
import cv2
import mediapipe as mp
import config


@dataclass
class FaceEvent:
    """Event emitted when face presence changes."""
    present: bool
    timestamp: float


class FacePresence:
    """
    Tracks face presence using webcam.
    Emits events when face appears/disappears.
    """
    
    def __init__(self, on_change=None):
        self.on_change = on_change
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._present = False
        self._present_streak = 0
        self._absent_streak = 0
        self._last_event_time = 0.0

    def start(self):
        """Start face detection thread."""
        self._thread.start()

    def stop(self):
        """Stop face detection thread."""
        self._stop.set()
        self._thread.join(timeout=2)

    def is_present(self) -> bool:
        """Check if face is currently present."""
        return self._present

    def _emit(self, present: bool):
        """Emit face change event."""
        now = time.time()
        self._last_event_time = now
        
        if self.on_change:
            try:
                self.on_change(FaceEvent(present=present, timestamp=now))
            except Exception as e:
                print(f"[VISION] on_change error: {e}")

    def _run(self):
        """Main vision thread loop."""
        cap = cv2.VideoCapture(config.CAMERA_INDEX)
        if not cap.isOpened():
            print("[VISION] Could not open camera.")
            print("[VISION] Try changing CAMERA_INDEX in config.py")
            return

        # Set camera properties for better performance
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)

        print(f"[VISION] Camera opened: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")

        mp_face = mp.solutions.face_detection
        face_detector = mp_face.FaceDetection(
            model_selection=0,  # 0 = short-range (< 2m), 1 = full-range
            min_detection_confidence=float(config.FACE_MIN_CONFIDENCE)
        )

        frame_i = 0
        fps_start = time.time()
        fps_count = 0
        current_fps = 0.0

        try:
            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.05)
                    continue

                frame_i += 1
                fps_count += 1
                
                # Calculate FPS every second
                if time.time() - fps_start >= 1.0:
                    current_fps = fps_count
                    fps_count = 0
                    fps_start = time.time()

                # Process every N frames for performance
                do_process = (frame_i % max(1, int(config.VISION_PROCESS_EVERY_N_FRAMES)) == 0)

                face_seen = False
                detections = None
                
                if do_process:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
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

                # Draw preview window
                if config.VISION_SHOW_WINDOW:
                    disp = frame.copy()
                    
                    # Draw face boxes
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
                            
                            # Confidence score
                            conf = d.score[0] if d.score else 0
                            cv2.putText(disp, f"{conf:.0%}", (x1, y1-10), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

                    # Status overlay
                    status = "FACE: YES" if self._present else "FACE: NO"
                    color = (0, 255, 0) if self._present else (0, 0, 255)
                    cv2.putText(disp, status, (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                    
                    # FPS counter
                    cv2.putText(disp, f"FPS: {current_fps:.0f}", (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                    cv2.imshow("Local Face + Voice AI", disp)
                    
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        break

        finally:
            cap.release()
            try:
                cv2.destroyAllWindows()
            except Exception:
                pass


def list_cameras():
    """Utility to list available cameras."""
    print("\nSearching for cameras...")
    available = []
    
    for i in range(10):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            available.append((i, w, h))
            print(f"  Camera {i}: {w}x{h}")
            cap.release()
    
    if not available:
        print("  No cameras found!")
    
    return available


if __name__ == "__main__":
    # Run this file directly to test camera
    list_cameras()
