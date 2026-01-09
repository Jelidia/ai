"""
Local Face + Voice AI - Configuration
Optimized for: qwen2.5:3b (CPU-friendly, fast responses)
"""

# ---------------------------
# Camera / face detection
# ---------------------------
CAMERA_INDEX = 0
VISION_SHOW_WINDOW = True
VISION_PROCESS_EVERY_N_FRAMES = 3
FACE_PRESENT_FRAMES_REQUIRED = 4
FACE_ABSENT_FRAMES_REQUIRED = 12
FACE_MIN_CONFIDENCE = 0.6

# ---------------------------
# Audio / speech recognition
# ---------------------------
SAMPLE_RATE = 16000

# VAD settings
VAD_AGGRESSIVENESS = 2
VAD_SILENCE_MS_TO_END = 1400
VAD_MAX_UTTERANCE_SEC = 15

# Microphone
MIC_DEVICE_INDEX = None

# Utterance filtering
MIN_UTTERANCE_SEC = 0.45
MICRO_GAP_MS = 200

# ---------------------------
# Vosk models
# ---------------------------
VOSK_MODEL_EN_PATH = "models/vosk-model-small-en-us-0.15"
VOSK_MODEL_FR_PATH = "models/vosk-model-small-fr-0.22"

# ---------------------------
# Wake words
# ---------------------------
WAKE_WORDS_ENABLED = False
WAKE_WORDS_EN = ["hey assistant", "assistant", "hey buddy", "hey pal", "computer"]
WAKE_WORDS_FR = ["hé assistant", "assistant", "hé poto", "salut assistant", "ordinateur"]

# ---------------------------
# TTS (Text-to-Speech)
# ---------------------------
SPEECH_RATE = 190
SPEAK_COOLDOWN_SEC = 0.3

VOICE_NAME_HINT_EN = "Zira"
VOICE_NAME_HINT_FR = "Caroline"
TTS_DEVICE_NAME_HINT = None

# ---------------------------
# Local LLM (Ollama) - OPTIMIZED FOR SPEED
# ---------------------------
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:3b"
OLLAMA_TIMEOUT_SEC = 60

# Conversation memory - REDUCED FOR SPEED
HISTORY_TURNS = 5
MAX_TOKENS = 120
TEMPERATURE = 0.6

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
