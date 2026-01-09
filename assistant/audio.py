from __future__ import annotations
import json
import queue
import re
import time
from dataclasses import dataclass

import sounddevice as sd
import webrtcvad
from vosk import Model, KaldiRecognizer
import config


@dataclass
class Heard:
    text: str
    lang: str  # "en" or "fr"
    confidence: float


def _clean(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[^\w\sàâäçéèêëîïôöùûüÿ'’-]", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip()
    return s


class BilingualASR:
    def __init__(self):
        self.vad = webrtcvad.Vad(int(config.VAD_AGGRESSIVENESS))
        self.frame_ms = 20
        self.frame_samples = int(config.SAMPLE_RATE * self.frame_ms / 1000)
        self.frame_bytes = self.frame_samples * 2  # int16 mono

        self._audio_q: "queue.Queue[bytes]" = queue.Queue(maxsize=400)

        self._model_en: Model | None = None
        self._model_fr: Model | None = None
        self._load_models()

    def _load_models(self):
        try:
            self._model_en = Model(config.VOSK_MODEL_EN_PATH)
        except Exception as e:
            print(f"[ASR] Could not load EN model at {config.VOSK_MODEL_EN_PATH}: {e}")
            self._model_en = None

        try:
            self._model_fr = Model(config.VOSK_MODEL_FR_PATH)
        except Exception as e:
            print(f"[ASR] Could not load FR model at {config.VOSK_MODEL_FR_PATH}: {e}")
            self._model_fr = None

        if not self._model_en and not self._model_fr:
            print("[ASR] No models loaded. Run scripts/setup_windows.ps1 to download them.")

    def _make_recognizer(self, model: Model):
        rec = KaldiRecognizer(model, config.SAMPLE_RATE)
        rec.SetWords(True)
        return rec

    def _asr_one(self, pcm: bytes, lang: str) -> Heard | None:
        model = self._model_en if lang == "en" else self._model_fr
        if not model:
            return None

        rec = self._make_recognizer(model)
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
        # indata is int16 mono
        b = indata.tobytes()
        try:
            self._audio_q.put_nowait(b)
        except queue.Full:
            # drop frames if overwhelmed
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
        """
        Returns (pcm_bytes, duration_sec) for one utterance, using VAD.
        - waits until speech triggers
        - keeps some pre-roll
        - ends on trailing silence OR max duration
        - ignores tiny gaps (<= 200ms) inside a phrase so it doesn't cut you mid-sentence
        """
        triggered = False
        voiced_frames: list[bytes] = []
        ring: list[tuple[bytes, bool]] = []

        # Pre-roll: keep last 800ms audio before trigger
        ring_max = int(800 / self.frame_ms)
        # Trigger threshold: require ~20% of ring frames as voiced (more permissive)
        voiced_needed = max(3, int(0.2 * ring_max))

        silence_ms = 0
        utter_start: float | None = None

        # NEW: tolerate micro gaps
        non_speech_streak = 0
        MICRO_GAP_MS = 200  # allow up to 200ms "not speech" inside a phrase

        while True:
            frame = self._audio_q.get()

            # Ensure frame is correct size
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

                # Hard cap after trigger
                if utter_start and (time.time() - utter_start) >= float(config.VAD_MAX_UTTERANCE_SEC):
                    break

                if is_speech:
                    non_speech_streak = 0
                    silence_ms = 0
                else:
                    non_speech_streak += 1

                    # Ignore tiny gaps so it doesn't cut the sentence
                    if (non_speech_streak * self.frame_ms) <= MICRO_GAP_MS:
                        continue

                    silence_ms += self.frame_ms
                    if silence_ms >= int(config.VAD_SILENCE_MS_TO_END):
                        break

        if not voiced_frames:
            return None

        dur = len(voiced_frames) * self.frame_ms / 1000.0
        return b"".join(voiced_frames), float(dur)

    def transcribe(self, pcm: bytes) -> Heard | None:
        """
        Fast(er) mode:
        - try FR first (since you're in Montreal you likely speak FR a lot)
        - fallback EN
        This avoids doing EN+FR every time which can add latency.
        """
        fr = self._asr_one(pcm, "fr")
        if fr:
            return fr
        en = self._asr_one(pcm, "en")
        return en

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

    def run(self, on_heard):
        """
        Blocking loop:
        - capture utterances
        - ASR
        - call on_heard(Heard)
        """
        with self._open_stream():
            while True:
                seg = self.listen_utterance()
                if not seg:
                    continue

                pcm, _dur = seg

                heard = self.transcribe(pcm)
                if not heard:
                    continue

                if not self.passes_wake_word(heard):
                    continue

                heard = self.strip_wake_word(heard)
                if not heard.text.strip():
                    continue

                on_heard(heard)


def is_stop_command(text: str) -> bool:
    t = _clean(text)
    return (
        t in {"stop", "arrête", "arrete", "ta gueule", "silence"}
        or t.startswith("stop ")
        or t.startswith("arrête ")
        or t.startswith("arrete ")
    )


def is_quit_command(text: str) -> bool:
    t = _clean(text)
    return (
        t in {"quit", "exit", "quitte", "bye app", "au revoir app"}
        or t.startswith("quit ")
        or t.startswith("exit ")
        or t.startswith("quitte ")
    )


def parse_set_command(text: str) -> tuple[str, float] | None:
    """
    Voice command to tweak config live (basic):
      - "set niceness 0.8"
      - "set banter 0.2"
      - "mets gentillesse 0.9"
      - "mets politesse 0.7"
      - "set intelligence 1"
      - "set speed 200"
    Returns (key, value) or None
    """
    t = _clean(text)
    # English
    m = re.match(r"set\s+(niceness|formality|banter|intelligence|speed|temperature)\s+([0-9]*\.?[0-9]+)", t)
    if m:
        return m.group(1), float(m.group(2))

    # French
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