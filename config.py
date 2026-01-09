"""
All tweakable knobs live here.

Goal presets (Windows + Vosk + webrtcvad):
- Avoid cutting sentences (longer trailing silence, tolerate micro-pauses)
- Reduce false triggers (slightly higher VAD aggressiveness)
- Keep latency reasonable
"""

# ---------------------------
# Camera / face detection
# ---------------------------
CAMERA_INDEX = 0
VISION_SHOW_WINDOW = True
VISION_PROCESS_EVERY_N_FRAMES = 2   # higher = faster, less accurate
FACE_PRESENT_FRAMES_REQUIRED = 4    # consecutive frames with a face before "present"
FACE_ABSENT_FRAMES_REQUIRED = 12    # a bit higher = fewer "false goodbyes"
FACE_MIN_CONFIDENCE = 0.6

# ---------------------------
# Audio / speech recognition
# ---------------------------
# 16k is required by webrtcvad + common Vosk configs
SAMPLE_RATE = 16000

# VAD:
# 0 = permissive (hears noise as speech sometimes)
# 3 = very aggressive (cuts speech more often)
# For real mics + background noise, 2 is aREALLY usually best.
VAD_AGGRESSIVENESS = 2              # 0..3

# Trailing silence to end an utterance:
# 650ms is usually TOO SHORT => cuts your phrases.
# 1300-2200ms is the sweet spot for human speech.
VAD_SILENCE_MS_TO_END = 1600        # recommended: 1300..2200

# Hard cap so it doesn't run forever if VAD gets stuck
VAD_MAX_UTTERANCE_SEC = 18          # recommended: 12..25

# If your mic is wrong, set an int (see script below)
MIC_DEVICE_INDEX = None             # None = default mic

# Optional: ignore very short utterances (helps reduce random blips)
MIN_UTTERANCE_SEC = 0.45            # ignore segments shorter than this (0.3..0.7)

# NEW (used by the patched audio.py I gave you):
# allow brief non-speech gaps inside a phrase, so it doesn't cut mid-sentence
MICRO_GAP_MS = 220                  # 150..300

# ---------------------------
# Vosk models (downloaded by scripts/setup_windows.ps1)
# ---------------------------
VOSK_MODEL_EN_PATH = "models/vosk-model-small-en-us-0.15"
VOSK_MODEL_FR_PATH = "models/vosk-model-small-fr-0.22"

# ---------------------------
# Wake words (enable if background noise triggers it)
# ---------------------------
WAKE_WORDS_ENABLED = False          # set True if it responds to noise
WAKE_WORDS_EN = ["hey assistant", "assistant", "hey buddy"]
WAKE_WORDS_FR = ["hé assistant", "assistant", "hé poto", "salut assistant"]

# ---------------------------
# Talking (TTS)
# ---------------------------
SPEECH_RATE = 185                   # 140-220 typical
SPEAK_COOLDOWN_SEC = 0.4            # lower = responds faster (0.3..0.9)

# Voice selection by substring match
VOICE_NAME_HINT_EN = "Zira"
VOICE_NAME_HINT_FR = "Caroline"

# Force TTS output device? (pyttsx3 doesn't always support device routing cleanly)
# Leave None unless you patch tts.py for explicit device routing.
TTS_DEVICE_NAME_HINT = None

# ---------------------------
# Local LLM (Ollama)
# ---------------------------
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.1:8b"
OLLAMA_TIMEOUT_SEC = 120

# Conversation memory
HISTORY_TURNS = 10                  # how many back-and-forth turns to keep
MAX_TOKENS = 220                    # response length cap (Ollama: num_predict)
TEMPERATURE = 0.65                  # slightly less random -> more "assistant" and less rambling

# ---------------------------
# Personality controls (0.0 .. 1.0)
# ---------------------------
NICENESS = 0.55
FORMALITY = 0.30
BANTER = 0.45
INTELLIGENCE = 0.85

ALLOW_REAL_INSULTS = False

# ---------------------------
# Helper
# ---------------------------
def clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))
