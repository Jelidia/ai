"""
Web UI Server - FastAPI + WebSocket - FIXED VERSION
"""
from __future__ import annotations
import asyncio
import json
import threading
import time
import random
from collections import deque
from pathlib import Path
from queue import Queue, Empty

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

import config
from assistant.tts import get_speaker
from assistant.vision import FacePresence, FaceEvent
from assistant.audio import BilingualASR, Heard, is_stop_command, is_quit_command, parse_set_command
from assistant.llm_ollama import OllamaClient, fallback_reply
from assistant.persona import build_system_prompt


# Load phrases
def _load_lines(path: str) -> list[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]
    except Exception:
        return []

GREETINGS_EN = _load_lines("phrases/greetings_en.txt") or ["Hey! I see you.", "Hello!", "Hi there!"]
GREETINGS_FR = _load_lines("phrases/greetings_fr.txt") or ["Salut !", "Bonjour !", "Hey !"]
GOODBYES_EN = _load_lines("phrases/goodbyes_en.txt") or ["Where'd you go?", "Bye!", "See you!"]
GOODBYES_FR = _load_lines("phrases/goodbyes_fr.txt") or ["T'es où ?", "À plus !", "Salut !"]


# Thread-safe message queue
message_queue: Queue = Queue()


class AppState:
    def __init__(self):
        self.websockets: list[WebSocket] = []
        self.history = deque(maxlen=config.HISTORY_TURNS * 2)
        self.face_present = False
        self.last_lang = "en"
        self.ollama = OllamaClient()
        self.speaker = None
        self.vision = None
        self.asr = None
        self.asr_thread = None
        self.listening = False
        self._last_phrases: dict[str, str] = {}

    def get_random_phrase(self, phrases: list[str], key: str) -> str:
        if len(phrases) <= 1:
            return phrases[0] if phrases else ""
        last = self._last_phrases.get(key)
        available = [p for p in phrases if p != last] or phrases
        choice = random.choice(available)
        self._last_phrases[key] = choice
        return choice

state = AppState()


def queue_message(msg: dict):
    """Thread-safe: queue message for broadcast."""
    try:
        message_queue.put_nowait(msg)
    except:
        pass


def on_face_change(evt: FaceEvent):
    """Called when face appears/disappears (from vision thread)."""
    state.face_present = evt.present
    
    lang = state.last_lang
    if evt.present:
        phrases = GREETINGS_FR if lang == "fr" else GREETINGS_EN
        text = state.get_random_phrase(phrases, "greeting")
        event_type = "face_appeared"
    else:
        phrases = GOODBYES_FR if lang == "fr" else GOODBYES_EN
        text = state.get_random_phrase(phrases, "goodbye")
        event_type = "face_disappeared"
    
    # Speak
    if state.speaker:
        state.speaker.say(text, lang)
    
    # Queue for web
    queue_message({
        "type": event_type,
        "text": text,
        "face_present": evt.present
    })


def on_frame(frame_b64: str):
    """Called for each camera frame (from vision thread)."""
    queue_message({
        "type": "frame",
        "data": frame_b64
    })


def on_heard(heard: Heard):
    """Called when speech is recognized (from ASR thread)."""
    text = heard.text.strip()
    lang = heard.lang
    state.last_lang = lang
    
    print(f"[ASR] Heard: {text}")
    
    # Queue user message
    queue_message({
        "type": "user_message",
        "text": text,
        "lang": lang
    })
    
    # Handle commands
    if is_stop_command(text):
        if state.speaker:
            state.speaker.stop()
        return
    
    if is_quit_command(text):
        return
    
    # Process in separate thread to not block ASR
    threading.Thread(target=process_message_sync, args=(text, lang), daemon=True).start()


def process_message_sync(text: str, lang: str):
    """Process message and get AI response (runs in thread)."""
    state.history.append({"role": "user", "content": text})
    
    # Build messages
    sys_prompt = build_system_prompt(lang)
    presence_note = (
        "Visage présent : OUI." if state.face_present else "Visage présent : NON."
    ) if lang == "fr" else (
        "Face present: YES." if state.face_present else "Face present: NO."
    )
    
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "system", "content": presence_note},
    ]
    messages.extend(list(state.history))
    
    # Get response
    start = time.time()
    
    try:
        if state.ollama.is_up():
            reply = state.ollama.chat(
                model=config.OLLAMA_MODEL,
                messages=messages,
                max_tokens=config.MAX_TOKENS,
                temperature=config.TEMPERATURE,
            )
        else:
            reply = fallback_reply(text, lang)
    except Exception as e:
        print(f"[LLM] Error: {e}")
        reply = fallback_reply(text, lang)
    
    elapsed = time.time() - start
    reply = (reply or "").strip() or "..."
    
    state.history.append({"role": "assistant", "content": reply})
    
    print(f"[AI] ({elapsed:.1f}s) {reply}")
    
    # Speak
    if state.speaker:
        state.speaker.say(reply, lang)
    
    # Queue for web
    queue_message({
        "type": "ai_message",
        "text": reply,
        "lang": lang,
        "time": f"{elapsed:.1f}s"
    })


def start_asr():
    """Start ASR in background thread."""
    if state.listening:
        return
    
    # MODIF: On connecte les oreilles à la bouche (pour muter quand on parle)
    check_fn = state.speaker.is_speaking if state.speaker else None
    state.asr = BilingualASR(on_speech_check=check_fn)
    state.listening = True
    
    def run():
        try:
            state.asr.run(on_heard)
        except Exception as e:
            print(f"[ASR] Error: {e}")
        finally:
            state.listening = False
    
    state.asr_thread = threading.Thread(target=run, daemon=True)
    state.asr_thread.start()
    print("[ASR] Started")


def stop_asr():
    """Stop ASR."""
    if state.asr:
        state.asr.stop()
    state.listening = False
    print("[ASR] Stopped")


# FastAPI app
app = FastAPI(title="Local Voice AI")


async def broadcast_worker():
    """Background task to broadcast queued messages."""
    while True:
        try:
            while not message_queue.empty():
                msg = message_queue.get_nowait()
                if state.websockets:
                    data = json.dumps(msg)
                    dead = []
                    for ws in state.websockets:
                        try:
                            await ws.send_text(data)
                        except:
                            dead.append(ws)
                    for ws in dead:
                        if ws in state.websockets:
                            state.websockets.remove(ws)
        except Exception as e:
            pass
        await asyncio.sleep(0.02)  # 50 fps max


@app.on_event("startup")
async def startup():
    print("[WEB] Starting up...")
    
    # Start broadcast worker
    asyncio.create_task(broadcast_worker())
    
    # Initialize TTS
    state.speaker = get_speaker()
    
    # Initialize vision with callbacks
    state.vision = FacePresence(on_change=on_face_change, on_frame=on_frame)
    state.vision.start()
    
    # Check Ollama
    if state.ollama.is_up():
        print(f"[WEB] Ollama OK: {config.OLLAMA_MODEL}")
    else:
        print("[WEB] Ollama not running!")
    
    print(f"[WEB] Ready at http://{config.WEB_HOST}:{config.WEB_PORT}")


@app.on_event("shutdown")
async def shutdown():
    print("[WEB] Shutting down...")
    stop_asr()
    if state.vision:
        state.vision.stop()
    if state.speaker:
        state.speaker.close()


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = Path(__file__).parent / "static" / "index.html"
    if html_path.exists():
        return FileResponse(html_path)
    return HTMLResponse("<h1>static/index.html not found</h1>")


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    state.websockets.append(ws)
    print(f"[WEB] Client connected ({len(state.websockets)} total)")
    
    # Send initial state
    await ws.send_text(json.dumps({
        "type": "init",
        "face_present": state.face_present,
        "listening": state.listening,
        "ollama_ok": state.ollama.is_up(),
        "model": config.OLLAMA_MODEL
    }))
    
    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            
            if msg["type"] == "chat":
                text = msg.get("text", "").strip()
                lang = msg.get("lang", "en")
                if text:
                    state.last_lang = lang
                    # Show user message immediately
                    await ws.send_text(json.dumps({
                        "type": "user_message",
                        "text": text,
                        "lang": lang
                    }))
                    # Process in thread
                    threading.Thread(target=process_message_sync, args=(text, lang), daemon=True).start()
            
            elif msg["type"] == "start_listening":
                start_asr()
                await ws.send_text(json.dumps({"type": "listening_started"}))
            
            elif msg["type"] == "stop_listening":
                stop_asr()
                await ws.send_text(json.dumps({"type": "listening_stopped"}))
            
            elif msg["type"] == "stop_speaking":
                if state.speaker:
                    state.speaker.stop()
            
            elif msg["type"] == "clear_history":
                state.history.clear()
                await ws.send_text(json.dumps({"type": "history_cleared"}))
            
            elif msg["type"] == "set_lang":
                state.last_lang = msg.get("lang", "en")
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WEB] WebSocket error: {e}")
    finally:
        if ws in state.websockets:
            state.websockets.remove(ws)
        print(f"[WEB] Client disconnected ({len(state.websockets)} total)")


# Mount static files
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


if __name__ == "__main__":
    uvicorn.run(app, host=config.WEB_HOST, port=config.WEB_PORT, log_level="warning")