"""
Local Face + Voice AI - Configuration
Optimized for: qwen2.5:3b (CPU-friendly, fast responses)
"""

# ---------------------------
# Web UI
# ---------------------------
WEB_HOST = "127.0.0.1"
WEB_PORT = 8765

# ---------------------------
# Camera / face detection
# ---------------------------
CAMERA_INDEX = 0
VISION_SHOW_WINDOW = False  # Disabled - using web UI instead
VISION_PROCESS_EVERY_N_FRAMES = 2  # Faster processing
FACE_PRESENT_FRAMES_REQUIRED = 3   # Faster detection
FACE_ABSENT_FRAMES_REQUIRED = 8    # Faster goodbye
FACE_MIN_CONFIDENCE = 0.5

# ---------------------------
# Audio / speech recognition - OPTIMIZED FOR SPEED
# ---------------------------
SAMPLE_RATE = 16000

# VAD settings - MORE AGGRESSIVE for faster response
VAD_AGGRESSIVENESS = 2
VAD_SILENCE_MS_TO_END = 800   # Faster cutoff (was 1400)
VAD_MAX_UTTERANCE_SEC = 10    # Shorter max (was 15)

# Microphone
MIC_DEVICE_INDEX = None

# Utterance filtering
MIN_UTTERANCE_SEC = 0.3       # Shorter minimum (was 0.45)
MICRO_GAP_MS = 150            # Shorter gaps (was 200)

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
SPEECH_RATE = 200             # Faster speech
SPEAK_COOLDOWN_SEC = 0.1      # Faster cooldown

VOICE_NAME_HINT_EN = "Zira"
VOICE_NAME_HINT_FR = "Caroline"
TTS_DEVICE_NAME_HINT = None

# ---------------------------
# Local LLM (Ollama) - OPTIMIZED FOR SPEED
# ---------------------------
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:3b"
OLLAMA_TIMEOUT_SEC = 45       # Shorter timeout

# Conversation memory - REDUCED FOR SPEED
HISTORY_TURNS = 4             # Less history
MAX_TOKENS = 100              # Shorter responses
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