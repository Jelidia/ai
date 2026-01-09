from __future__ import annotations
import threading
import queue
import time
import pyttsx3
import config

_STOP = object()

class Speaker:
    def __init__(self):
        self._q: "queue.Queue[object]" = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._engine = None
        self._last_spoken_at = 0.0
        self._voices_cache = []
        self._thread.start()

    def _pick_voice_id(self, lang: str) -> str | None:
        # Called inside engine thread
        hint = config.VOICE_NAME_HINT_FR if lang == "fr" else config.VOICE_NAME_HINT_EN
        hint = (hint or "").lower().strip()
        if not hint:
            return None
        for v in self._voices_cache:
            name = (getattr(v, "name", "") or "").lower()
            if hint in name:
                return getattr(v, "id", None)
        return None

    def _run(self):
        self._engine = pyttsx3.init()
        self._engine.setProperty("rate", int(config.SPEECH_RATE))
        try:
            self._voices_cache = self._engine.getProperty("voices") or []
        except Exception:
            self._voices_cache = []

        while True:
            item = self._q.get()
            if item is None:
                return
            if item is _STOP:
                try:
                    self._engine.stop()
                except Exception:
                    pass
                continue

            text, lang = item
            now = time.time()
            if now - self._last_spoken_at < config.SPEAK_COOLDOWN_SEC:
                # still allow, but avoid rapid fire overlaps
                pass

            try:
                self._engine.setProperty("rate", int(config.SPEECH_RATE))
                vid = self._pick_voice_id(lang)
                if vid:
                    self._engine.setProperty("voice", vid)
                self._engine.say(text)
                self._engine.runAndWait()
                self._last_spoken_at = time.time()
            except Exception as e:
                print("[TTS] error:", e)

    def say(self, text: str, lang: str):
        self._q.put((text, lang))

    def stop(self):
        self._q.put(_STOP)

    def close(self):
        self._q.put(None)
