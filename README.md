# Local Face + Voice AI (Windows 11, no API keys)

This project runs **fully on your PC**:
- Webcam: detects *any human face* and greets / says goodbye
- Offline speech recognition: **English + French** (Vosk)
- Offline TTS: talks back using Windows voices (pyttsx3 / SAPI)
- “Brain” runs locally via **Ollama** (no API keys). The app talks to your local model at `http://localhost:11434`.

> You still need to **download** local models (speech models + LLM weights). They’re too big to bundle in a zip.

---

## 1) Install prerequisites

### A) Install Python
Install **Python 3.10+** (3.11 recommended). Make sure **“Add Python to PATH”** is checked.

### B) Install Ollama (local LLM engine)
Download and install Ollama for Windows:
- https://ollama.com/download/windows

After install, open PowerShell and run one of these (pick based on your GPU/RAM):
```powershell
ollama pull llama3.1:8b
# or (often faster/smaller)
ollama pull qwen2.5:7b
# or (very small, less smart)
ollama pull phi3:mini
```

---

## 2) Setup the project (one-time)

Open PowerShell **inside this folder** and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
./scripts/setup_windows.ps1
```

What it does:
- creates a venv
- installs Python deps
- downloads offline speech models (EN + FR) from https://alphacephei.com/vosk/models
- prints “next steps”

---

## 3) Run

```powershell
./scripts/run.bat
```

Voice controls (built-in):
- Say **"stop" / "arrête"** to interrupt speech
- Say **"quit" / "quitte"** to exit

---

## 4) Tune the personality (the fun part)

Open `config.py` and tweak these:

- `NICENESS` (0.0 = mean, 1.0 = super nice)
- `FORMALITY` (0.0 = casual, 1.0 = formal)
- `BANTER` (0.0 = no teasing, 1.0 = playful rhetorical “attack”)
- `INTELLIGENCE` (0.0 = dumb/simple, 1.0 = sharp/insightful)
- `SPEECH_RATE` (pyttsx3 speed; ~140–220 is normal)
- `WAKE_WORDS_ENABLED` (avoid it answering background noise)
- `WAKE_WORDS_EN / WAKE_WORDS_FR`

**Safety note:** “mean / banter” is kept *playful* by a guardrail so it doesn’t turn into real abuse.

---

## Troubleshooting

### “No module named …”
You didn’t activate the venv. Use:
```powershell
./.venv/Scripts/activate
pip install -r requirements.txt
```

### “Could not open microphone / camera”
- Close other apps using the mic/cam (Discord, Teams, etc.)
- In Windows Settings → Privacy → allow mic/cam access for desktop apps.

### It’s slow / laggy
- Use a smaller Ollama model (`phi3:mini`)
- Reduce `MAX_TOKENS` and `HISTORY_TURNS` in `config.py`
- Set `VISION_PROCESS_EVERY_N_FRAMES` higher

---

## Files

- `main.py` : app entry point
- `assistant/vision.py` : face detection + presence state machine
- `assistant/audio.py` : mic streaming + VAD + bilingual ASR
- `assistant/llm_ollama.py` : local chat via Ollama
- `assistant/tts.py` : speaking + voice selection
- `config.py` : all tuning knobs
