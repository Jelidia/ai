"""
Text-to-Speech - Windows pyttsx3 - FIXED THREADING
"""
from __future__ import annotations
import threading
import queue
import time

import pyttsx3

_SHUTDOWN = "__SHUTDOWN__"


class Speaker:
    """Thread-safe TTS speaker."""
    
    def __init__(self):
        self._queue: queue.Queue = queue.Queue()
        self._stop_flag = threading.Event()
        self._engine_ready = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        # Wait for engine init
        self._engine_ready.wait(timeout=5)
    
    def _run(self):
        """TTS thread - creates and owns the engine."""
        try:
            engine = pyttsx3.init()
            
            # Configure
            voices = engine.getProperty('voices')
            print(f"[TTS] Initialized with {len(voices)} voices")
            
            # Try to set a good voice
            for v in voices:
                if 'zira' in v.name.lower() or 'david' in v.name.lower():
                    engine.setProperty('voice', v.id)
                    break
            
            engine.setProperty('rate', 175)
            engine.setProperty('volume', 1.0)
            
            self._engine_ready.set()
            
            while True:
                try:
                    item = self._queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                
                if item == _SHUTDOWN:
                    break
                
                if self._stop_flag.is_set():
                    self._stop_flag.clear()
                    continue
                
                text, lang = item
                
                # Try to switch voice based on language
                for v in voices:
                    v_name = v.name.lower()
                    if lang == "fr" and ("french" in v_name or "paul" in v_name):
                        engine.setProperty('voice', v.id)
                        break
                    elif lang == "en" and ("english" in v_name or "zira" in v_name or "david" in v_name):
                        engine.setProperty('voice', v.id)
                        break
                
                preview = text[:50] + "..." if len(text) > 50 else text
                print(f"[TTS] Speaking: {preview}")
                
                try:
                    engine.say(text)
                    engine.runAndWait()
                except Exception as e:
                    print(f"[TTS] Error speaking: {e}")
                    # Reinit engine on error
                    try:
                        engine = pyttsx3.init()
                        engine.setProperty('rate', 175)
                        engine.setProperty('volume', 1.0)
                    except:
                        pass
                
                print("[TTS] Done speaking")
                
        except Exception as e:
            print(f"[TTS] Init error: {e}")
        finally:
            self._engine_ready.set()
    
    def say(self, text: str, lang: str = "en"):
        """Queue text to speak."""
        if not text or not text.strip():
            return
        text = text.strip()
        preview = text[:50] + "..." if len(text) > 50 else text
        print(f"[TTS] Queuing: {preview}")
        self._queue.put((text, lang))
    
    def stop(self):
        """Stop current speech."""
        self._stop_flag.set()
        # Clear queue
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        print("[TTS] Stopped")
    
    def close(self):
        """Shutdown TTS."""
        print("[TTS] Shutting down")
        self._queue.put(_SHUTDOWN)
        self._thread.join(timeout=2)


# Global instance
_speaker: Speaker | None = None
_lock = threading.Lock()


def get_speaker() -> Speaker:
    """Get or create global speaker."""
    global _speaker
    with _lock:
        if _speaker is None:
            _speaker = Speaker()
        return _speaker