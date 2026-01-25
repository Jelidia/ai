"""
Text-to-Speech - Windows pyttsx3 - ROBUST VERSION
Creates fresh engine for each message to avoid Windows COM issues
"""
from __future__ import annotations
import threading
import queue
import time

import pyttsx3

_SHUTDOWN = "__SHUTDOWN__"


class Speaker:
    """Thread-safe TTS speaker - recreates engine per message for reliability."""
    
    def __init__(self):
        self._queue: queue.Queue = queue.Queue()
        self._stop_flag = threading.Event()
        self._ready = threading.Event()
        self._speaking_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=3)
    
    def is_speaking(self) -> bool:
        """Check if the speaker is currently outputting audio."""
        return self._speaking_event.is_set()

    def _create_engine(self):
        """Create and configure a fresh TTS engine."""
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        
        # Try to find a good voice
        for v in voices:
            name = v.name.lower()
            if 'zira' in name or 'david' in name:
                engine.setProperty('voice', v.id)
                break
        
        engine.setProperty('rate', 175)
        engine.setProperty('volume', 1.0)
        return engine, voices
    
    def _run(self):
        """TTS thread - creates fresh engine for each message."""
        # Initial test
        try:
            engine, voices = self._create_engine()
            print(f"[TTS] Initialized with {len(voices)} voices")
            engine.stop()
            del engine
        except Exception as e:
            print(f"[TTS] Init error: {e}")
        
        self._ready.set()
        
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
            
            # Create fresh engine for this message
            try:
                engine = pyttsx3.init()
                voices = engine.getProperty('voices')
                
                # Try to switch voice based on language
                for v in voices:
                    name = v.name.lower()
                    if lang == "fr" and ("french" in name or "paul" in name or "hortense" in name):
                        engine.setProperty('voice', v.id)
                        break
                    elif lang == "en" and ("zira" in name or "david" in name or "english" in name):
                        engine.setProperty('voice', v.id)
                        break
                
                engine.setProperty('rate', 175)
                engine.setProperty('volume', 1.0)
                
                preview = text[:50] + "..." if len(text) > 50 else text
                print(f"[TTS] Speaking: {preview}")
                
                self._speaking_event.set()
                
                try:
                    engine.say(text)
                    engine.runAndWait()
                finally:
                    self._speaking_event.clear()
                    time.sleep(0.2)
                
                # Cleanup
                engine.stop()
                del engine
                
                print("[TTS] Done speaking")
                
            except Exception as e:
                print(f"[TTS] Error: {e}")
                self._speaking_event.clear()
                try:
                    engine.stop()
                    del engine
                except:
                    pass
    
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