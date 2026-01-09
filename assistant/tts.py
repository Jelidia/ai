"""
Text-to-Speech module using pyttsx3 (Windows SAPI voices).
"""
from __future__ import annotations
import threading
import queue
import time
import pyttsx3
import config

_STOP = object()


class Speaker:
    """Thread-safe TTS speaker with queue-based processing."""
    
    def __init__(self):
        self._q: "queue.Queue[object]" = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._engine = None
        self._last_spoken_at = 0.0
        self._voices_cache = []
        self._is_speaking = False
        self._thread.start()

    def _pick_voice_id(self, lang: str) -> str | None:
        """Find a voice matching the language hint."""
        hint = config.VOICE_NAME_HINT_FR if lang == "fr" else config.VOICE_NAME_HINT_EN
        hint = (hint or "").lower().strip()
        if not hint:
            return None
            
        for v in self._voices_cache:
            name = (getattr(v, "name", "") or "").lower()
            if hint in name:
                return getattr(v, "id", None)
        
        # Fallback: try to find any voice for the language
        lang_codes = {"fr": ["french", "fr-"], "en": ["english", "en-"]}
        for v in self._voices_cache:
            name = (getattr(v, "name", "") or "").lower()
            langs = getattr(v, "languages", []) or []
            lang_str = " ".join(str(l) for l in langs).lower()
            
            for code in lang_codes.get(lang, []):
                if code in name or code in lang_str:
                    return getattr(v, "id", None)
        
        return None

    def _run(self):
        """Main TTS thread loop."""
        self._engine = pyttsx3.init()
        self._engine.setProperty("rate", int(config.SPEECH_RATE))
        
        try:
            self._voices_cache = self._engine.getProperty("voices") or []
            print(f"[TTS] Found {len(self._voices_cache)} voices")
        except Exception as e:
            print(f"[TTS] Could not list voices: {e}")
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
                self._is_speaking = False
                continue

            text, lang = item
            now = time.time()
            
            # Small delay to avoid rapid-fire speech
            if now - self._last_spoken_at < config.SPEAK_COOLDOWN_SEC:
                time.sleep(config.SPEAK_COOLDOWN_SEC - (now - self._last_spoken_at))

            try:
                self._is_speaking = True
                self._engine.setProperty("rate", int(config.SPEECH_RATE))
                
                vid = self._pick_voice_id(lang)
                if vid:
                    self._engine.setProperty("voice", vid)
                
                self._engine.say(text)
                self._engine.runAndWait()
                self._last_spoken_at = time.time()
            except Exception as e:
                print(f"[TTS] Error: {e}")
            finally:
                self._is_speaking = False

    def say(self, text: str, lang: str):
        """Queue text to be spoken."""
        if text and text.strip():
            self._q.put((text.strip(), lang))

    def stop(self):
        """Stop current speech immediately."""
        # Clear queue
        while not self._q.empty():
            try:
                self._q.get_nowait()
            except queue.Empty:
                break
        self._q.put(_STOP)

    def is_speaking(self) -> bool:
        """Check if currently speaking."""
        return self._is_speaking

    def close(self):
        """Shutdown TTS thread."""
        self.stop()
        self._q.put(None)
        self._thread.join(timeout=2)


def list_available_voices():
    """Utility to list all available TTS voices."""
    engine = pyttsx3.init()
    voices = engine.getProperty("voices") or []
    
    print(f"\nAvailable TTS Voices ({len(voices)}):")
    print("-" * 50)
    
    for i, v in enumerate(voices):
        name = getattr(v, "name", "Unknown")
        vid = getattr(v, "id", "")
        langs = getattr(v, "languages", [])
        print(f"{i+1}. {name}")
        print(f"   ID: {vid}")
        if langs:
            print(f"   Languages: {langs}")
        print()
    
    return voices


if __name__ == "__main__":
    # Run this file directly to see available voices
    list_available_voices()
