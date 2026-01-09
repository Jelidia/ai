# Local Face + Voice AI

A **fully offline** voice assistant for Windows with face detection. No API keys, no cloud, everything runs on your PC.

## Features

- 🎤 **Voice Recognition** - Bilingual (English + French) using Vosk
- 🗣️ **Text-to-Speech** - Natural voices using Windows SAPI
- 👤 **Face Detection** - Greets you when you appear, notices when you leave
- 🧠 **Local AI Brain** - Uses Ollama (qwen2.5:3b recommended for speed)
- ⚡ **Optimized for Speed** - Tuned for fast responses on CPU

---

## Quick Start

### 1. Prerequisites

- **Windows 10/11**
- **Python 3.10+** - [Download](https://www.python.org/downloads/) (check "Add to PATH")
- **Ollama** - [Download](https://ollama.com/download/windows)
- **Webcam + Microphone**

### 2. Install Ollama Model

Open PowerShell and run:

```powershell
# Fast model for CPU (recommended)
ollama pull qwen2.5:3b

# Or even smaller/faster
ollama pull phi3:mini
```

### 3. Setup Project

```powershell
# Navigate to project folder
cd path\to\local-voice-ai

# Allow script execution (one-time)
Set-ExecutionPolicy -Scope Process Bypass

# Run setup
.\scripts\setup_windows.ps1
```

### 4. Run

```powershell
# Start Ollama (if not running)
ollama serve

# In another terminal, run the app
.\scripts\run.bat
```

---

## Voice Commands

| Command | Action |
|---------|--------|
| `stop` / `arrête` | Stop speaking |
| `quit` / `quitte` | Exit app |
| `clear` / `efface` | Clear conversation history |
| `set speed 200` | Change speech rate (80-300) |
| `set banter 0.8` | Increase playfulness (0-1) |
| `set niceness 0.3` | Make it more blunt (0-1) |

---

## Configuration

Edit `config.py` to customize:

### Speed Settings (for faster responses)
```python
OLLAMA_MODEL = "qwen2.5:3b"   # Fast CPU-friendly model
HISTORY_TURNS = 5              # Less context = faster
MAX_TOKENS = 120               # Shorter responses
```

### Personality (0.0 to 1.0)
```python
NICENESS = 0.55      # 0=cold, 1=very kind
FORMALITY = 0.30     # 0=slangy, 1=formal
BANTER = 0.45        # 0=none, 1=very playful
INTELLIGENCE = 0.85  # 0=simple, 1=sharp
```

### Hardware
```python
CAMERA_INDEX = 0           # Change if wrong camera
MIC_DEVICE_INDEX = None    # None=default, or set number
SPEECH_RATE = 190          # TTS speed (140-220 typical)
```

---

## Troubleshooting

### "No module named..."
```powershell
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### Wrong microphone
1. Run this to list devices:
   ```powershell
   .\.venv\Scripts\python.exe -c "import sounddevice; print(sounddevice.query_devices())"
   ```
2. Set `MIC_DEVICE_INDEX` in config.py to the correct number

### Wrong camera
1. Change `CAMERA_INDEX` in config.py (try 0, 1, 2...)

### Slow responses (20+ seconds)
- Use a smaller model: `ollama pull phi3:mini`
- Reduce `HISTORY_TURNS` to 3-4
- Reduce `MAX_TOKENS` to 80-100

### Can't hear TTS / Wrong voice
1. Run this to list voices:
   ```powershell
   .\.venv\Scripts\python.exe assistant\tts.py
   ```
2. Update `VOICE_NAME_HINT_EN` / `VOICE_NAME_HINT_FR` in config.py

### Ollama not responding
```powershell
# Check if running
curl http://localhost:11434

# If not, start it
ollama serve

# Check available models
ollama list
```

---

## Project Structure

```
local-voice-ai/
├── main.py                 # Entry point
├── config.py               # All settings
├── requirements.txt        # Python dependencies
├── assistant/
│   ├── audio.py           # VAD + Speech recognition
│   ├── llm_ollama.py      # Ollama client
│   ├── persona.py         # System prompt builder
│   ├── tts.py             # Text-to-speech
│   └── vision.py          # Face detection
├── phrases/
│   ├── greetings_en.txt   # English greetings
│   ├── greetings_fr.txt   # French greetings
│   ├── goodbyes_en.txt    # English goodbyes
│   └── goodbyes_fr.txt    # French goodbyes
├── models/                 # Vosk models (auto-downloaded)
└── scripts/
    ├── setup_windows.ps1   # One-time setup
    ├── download_models.ps1 # Model downloader
    └── run.bat             # Launch script
```

---

## Model Comparison

| Model | Size | CPU Speed | Quality |
|-------|------|-----------|---------|
| `phi3:mini` | ~2.3 GB | ~2-5s | Basic |
| `qwen2.5:3b` | ~2 GB | ~3-6s | Good |
| `qwen2.5:7b` | ~4.4 GB | ~8-15s | Better |
| `llama3.1:8b` | ~4.6 GB | ~20-60s | Best |

**Recommendation:** Use `qwen2.5:3b` for the best speed/quality balance on CPU.

---

## License

MIT License - Use freely, modify as needed.
