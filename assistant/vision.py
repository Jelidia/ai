from __future__ import annotations
import threading
import time
from dataclasses import dataclass
import cv2
import mediapipe as mp
import config

@dataclass
class FaceEvent:
    present: bool
    timestamp: float

class FacePresence:
    def __init__(self, on_change=None):
        self.on_change = on_change
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._present = False
        self._present_streak = 0
        self._absent_streak = 0

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=2)

    def is_present(self) -> bool:
        return self._present

    def _emit(self, present: bool):
        if self.on_change:
            try:
                self.on_change(FaceEvent(present=present, timestamp=time.time()))
            except Exception as e:
                print("[VISION] on_change error:", e)

    def _run(self):
        cap = cv2.VideoCapture(config.CAMERA_INDEX)
        if not cap.isOpened():
            print("[VISION] Could not open camera.")
            return

        mp_face = mp.solutions.face_detection
        face_detector = mp_face.FaceDetection(model_selection=0, min_detection_confidence=float(config.FACE_MIN_CONFIDENCE))

        frame_i = 0
        try:
            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.05)
                    continue

                frame_i += 1
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

                    # absent -> present
                    if (not self._present) and (self._present_streak >= config.FACE_PRESENT_FRAMES_REQUIRED):
                        self._present = True
                        self._emit(True)

                    # present -> absent
                    if self._present and (self._absent_streak >= config.FACE_ABSENT_FRAMES_REQUIRED):
                        self._present = False
                        self._emit(False)

                # draw window
                if config.VISION_SHOW_WINDOW:
                    disp = frame.copy()
                    if detections:
                        h, w = disp.shape[:2]
                        for d in detections:
                            box = d.location_data.relative_bounding_box
                            x1 = int(box.xmin * w)
                            y1 = int(box.ymin * h)
                            x2 = int((box.xmin + box.width) * w)
                            y2 = int((box.ymin + box.height) * h)
                            cv2.rectangle(disp, (x1, y1), (x2, y2), (0, 255, 0), 2)

                    status = "FACE: YES" if self._present else "FACE: NO"
                    cv2.putText(disp, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255,255,255), 2)
                    cv2.imshow("Local Face + Voice AI", disp)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break

        finally:
            cap.release()
            try:
                cv2.destroyAllWindows()
            except Exception:
                pass
