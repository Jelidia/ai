"""
Audio module - VAD + Bilingual ASR - OPTIMIZED FOR SPEED
"""
from __future__ import annotations
import json
import queue
import re
import time
from dataclasses import dataclass
from typing import Callable

import sounddevice as sd
import webrtcvad
from vosk import Model, KaldiRecognizer
import config


@dataclass
class Heard:
    text: str
    lang: str
    confidence: float


def _clean(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[^\w\sàâäçéèêëîïôöùûüÿ''-]", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip()
    return s


class BilingualASR:
    """Bilingual ASR - OPTIMIZED FOR SPEED."""
    
    # MODIF: Ajout du paramètre on_speech_check pour vérifier si le robot parle
    def __init__(self, on_speech_check: Callable[[], bool] | None = None):
        self.vad = webrtcvad.Vad(int(config.VAD_AGGRESSIVENESS))
        self.frame_ms = 20
        self.frame_samples = int(config.SAMPLE_RATE * self.frame_ms / 1000)
        self.frame_bytes = self.frame_samples * 2

        self._audio_q: "queue.Queue[bytes]" = queue.Queue(maxsize=200)
        self._running = False
        self._stream = None
        
        # Le callback pour savoir si on parle
        self.on_speech_check = on_speech_check

        self._model_en: Model | None = None
        self._model_fr: Model | None = None
        self._recognizer_en = None
        self._recognizer_fr = None
        self._load_models()

    def _load_models(self):
        """Load Vosk models and create persistent recognizers."""
        try:
            self._model_en = Model(config.VOSK_MODEL_EN_PATH)
            self._recognizer_en = KaldiRecognizer(self._model_en, config.SAMPLE_RATE)
            self._recognizer_en.SetWords(True)
            print(f"[ASR] Loaded EN model")
        except Exception as e:
            print(f"[ASR] Could not load EN model: {e}")

        try:
            self._model_fr = Model(config.VOSK_MODEL_FR_PATH)
            self._recognizer_fr = KaldiRecognizer(self._model_fr, config.SAMPLE_RATE)
            self._recognizer_fr.SetWords(True)
            print(f"[ASR] Loaded FR model")
        except Exception as e:
            print(f"[ASR] Could not load FR model: {e}")

        if not self._model_en and not self._model_fr:
            print("[ASR] No models loaded!")

    def _asr_one(self, pcm: bytes, lang: str) -> Heard | None:
        """Run ASR - uses persistent recognizer for speed."""
        if lang == "en":
            if not self._recognizer_en:
                return None
            rec = self._recognizer_en
        else:
            if not self._recognizer_fr:
                return None
            rec = self._recognizer_fr

        # Reset recognizer state
        rec.Reset()
        rec.AcceptWaveform(pcm)
        out = rec.FinalResult()

        try:
            data = json.loads(out)
        except Exception:
            return None

        text = (data.get("text") or "").strip()
        words = data.get("result") or []

        if words:
            confs = [float(w.get("conf", 0.0)) for w in words if "conf" in w]
            conf = float(sum(confs) / max(1, len(confs))) if confs else 0.0
        else:
            conf = 0.0

        if not text:
            return None

        return Heard(text=text, lang=lang, confidence=conf)

    def _audio_callback(self, indata, frames, time_info, status):
        b = indata.tobytes()
        try:
            self._audio_q.put_nowait(b)
        except queue.Full:
            pass

    def _open_stream(self):
        return sd.InputStream(
            samplerate=config.SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=self.frame_samples,
            device=config.MIC_DEVICE_INDEX,
            callback=self._audio_callback,
        )

    def listen_utterance(self) -> tuple[bytes, float] | None:
        """Capture one utterance - OPTIMIZED for speed."""
        triggered = False
        voiced_frames: list[bytes] = []
        ring: list[tuple[bytes, bool]] = []

        ring_max = int(400 / self.frame_ms)  # Reduced pre-roll
        voiced_needed = max(2, int(0.25 * ring_max))  # More permissive trigger

        silence_ms = 0
        utter_start: float | None = None
        non_speech_streak = 0

        while self._running:
            try:
                frame = self._audio_q.get(timeout=0.1)
            except queue.Empty:
                continue

            # --- CORRECTIF : ON IGNORE L'AUDIO SI LE ROBOT PARLE ---
            if self.on_speech_check and self.on_speech_check():
                # On vide la mémoire tampon et on reset la détection
                triggered = False
                ring.clear()
                voiced_frames.clear()
                continue
            # -------------------------------------------------------

            if len(frame) != self.frame_bytes:
                if len(frame) > self.frame_bytes:
                    frame = frame[:self.frame_bytes]
                else:
                    frame = frame + b"\x00" * (self.frame_bytes - len(frame))

            is_speech = self.vad.is_speech(frame, config.SAMPLE_RATE)

            if not triggered:
                ring.append((frame, is_speech))
                if len(ring) > ring_max:
                    ring.pop(0)

                num_voiced = sum(1 for _, s in ring if s)
                if num_voiced >= voiced_needed:
                    triggered = True
                    utter_start = time.time()
                    voiced_frames.extend([f for f, _ in ring])
                    ring.clear()
                    silence_ms = 0
                    non_speech_streak = 0
            else:
                voiced_frames.append(frame)

                if utter_start and (time.time() - utter_start) >= float(config.VAD_MAX_UTTERANCE_SEC):
                    break

                if is_speech:
                    non_speech_streak = 0
                    silence_ms = 0
                else:
                    non_speech_streak += 1

                    if (non_speech_streak * self.frame_ms) <= config.MICRO_GAP_MS:
                        continue

                    silence_ms += self.frame_ms
                    if silence_ms >= int(config.VAD_SILENCE_MS_TO_END):
                        break

        if not voiced_frames:
            return None

        dur = len(voiced_frames) * self.frame_ms / 1000.0
        if dur < config.MIN_UTTERANCE_SEC:
            return None
            
        return b"".join(voiced_frames), float(dur)

    def transcribe(self, pcm: bytes) -> Heard | None:
        """Transcribe - try both languages in parallel for speed."""
        # Try both and pick best confidence
        start = time.time()
        
        fr = self._asr_one(pcm, "fr")
        en = self._asr_one(pcm, "en")
        
        elapsed = time.time() - start
        print(f"[ASR] Transcription took {elapsed:.2f}s")
        
        # Pick best result
        if fr and en:
            return fr if fr.confidence >= en.confidence else en
        return fr or en

    def passes_wake_word(self, heard: Heard) -> bool:
        if not config.WAKE_WORDS_ENABLED:
            return True
        t = _clean(heard.text)
        wake = config.WAKE_WORDS_EN if heard.lang == "en" else config.WAKE_WORDS_FR
        wake = [_clean(w) for w in wake]
        return any(w in t for w in wake)

    def strip_wake_word(self, heard: Heard) -> Heard:
        if not config.WAKE_WORDS_ENABLED:
            return heard
        t = _clean(heard.text)
        wake = config.WAKE_WORDS_EN if heard.lang == "en" else config.WAKE_WORDS_FR
        for w in sorted([_clean(x) for x in wake], key=len, reverse=True):
            t = t.replace(w, "").strip()
        heard.text = t
        return heard

    def start(self):
        """Start audio capture."""
        if not self._running:
            self._running = True
            self._stream = self._open_stream()
            self._stream.start()
            print("[ASR] Started listening")

    def stop(self):
        """Stop audio capture."""
        self._running = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        print("[ASR] Stopped listening")

    def run(self, on_heard: Callable[[Heard], None]):
        """Main blocking loop."""
        self.start()
        try:
            while self._running:
                seg = self.listen_utterance()
                if not seg:
                    continue

                pcm, dur = seg
                print(f"[ASR] Got utterance: {dur:.2f}s")

                heard = self.transcribe(pcm)
                if not heard:
                    continue

                if not self.passes_wake_word(heard):
                    continue

                heard = self.strip_wake_word(heard)
                if not heard.text.strip():
                    continue

                on_heard(heard)
        finally:
            self.stop()


# --- Voice command helpers ---

def is_stop_command(text: str) -> bool:
    t = _clean(text)
    stop_words = {"stop", "arrête", "arrete", "ta gueule", "silence", "shut up", "tais-toi", "tais toi"}
    return t in stop_words or any(t.startswith(w + " ") for w in ["stop", "arrête", "arrete"])


def is_quit_command(text: str) -> bool:
    t = _clean(text)
    quit_words = {"quit", "exit", "quitte", "bye app", "au revoir app", "ferme", "close", "goodbye app"}
    return t in quit_words or any(t.startswith(w + " ") for w in ["quit", "exit", "quitte"])


def parse_set_command(text: str) -> tuple[str, float] | None:
    t = _clean(text)
    
    m = re.match(r"set\s+(niceness|formality|banter|intelligence|speed|temperature)\s+([0-9]*\.?[0-9]+)", t)
    if m:
        return m.group(1), float(m.group(2))

    m = re.match(r"(mets|met)\s+(gentillesse|politesse|taquinerie|intelligence|vitesse|temperature)\s+([0-9]*\.?[0-9]+)", t)
    if m:
        fr_key = m.group(2)
        val = float(m.group(3))
        mapping = {
            "gentillesse": "niceness",
            "politesse": "formality",
            "taquinerie": "banter",
            "intelligence": "intelligence",
            "vitesse": "speed",
            "temperature": "temperature",
        }
        return mapping.get(fr_key), val

    return None