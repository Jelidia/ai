#!/usr/bin/env python3
"""
Local Face + Voice AI - Main Entry Point
Optimized for qwen2.5:3b
"""
from __future__ import annotations
import threading
import sys
from collections import deque
import random
import time

import config
from assistant.tts import Speaker
from assistant.vision import FacePresence, FaceEvent
from assistant.audio import BilingualASR, is_stop_command, is_quit_command, parse_set_command
from assistant.llm_ollama import OllamaClient, fallback_reply
from assistant.persona import build_system_prompt


def _load_lines(path: str) -> list[str]:
    """Load non-empty, non-comment lines from a text file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]
            return lines
    except Exception:
        return []


# Load phrase files with fallbacks
GREETINGS_EN = _load_lines("phrases/greetings_en.txt") or [
    "Hey! I see you.",
    "Hi — you're back.",
    "Hello there.",
    "Oh, a human. Nice.",
    "Hi. I'm listening.",
]

GREETINGS_FR = _load_lines("phrases/greetings_fr.txt") or [
    "Salut, je te vois.",
    "Hey, te revoilà.",
    "Bonjour.",
    "Oh, un humain. Nice.",
    "Salut. Je t'écoute.",
]

GOODBYES_EN = _load_lines("phrases/goodbyes_en.txt") or [
    "Where'd you go?",
    "I lost your face. Still there?",
    "Okay, goodbye for now.",
    "Hey—don't vanish on me.",
]

GOODBYES_FR = _load_lines("phrases/goodbyes_fr.txt") or [
    "T'es où ?",
    "Je ne te vois plus. T'es encore là ?",
    "Ok, à plus.",
    "Hey—reviens.",
]


class Conversation:
    """Manages conversation history and context."""
    
    def __init__(self):
        self.history = deque(maxlen=max(2, int(config.HISTORY_TURNS) * 2))
        self.face_present = False
        self.last_lang = "en"
        self._last_phrases: dict[str, str] = {}  # avoid repeating same phrase

    def add_user(self, text: str):
        self.history.append({"role": "user", "content": text})

    def add_assistant(self, text: str):
        self.history.append({"role": "assistant", "content": text})

    def clear(self):
        self.history.clear()

    def get_random_phrase(self, phrases: list[str], key: str) -> str:
        """Get random phrase, avoiding immediate repetition."""
        if len(phrases) <= 1:
            return phrases[0] if phrases else ""
        
        last = self._last_phrases.get(key)
        available = [p for p in phrases if p != last] or phrases
        choice = random.choice(available)
        self._last_phrases[key] = choice
        return choice

    def build_messages(self, lang: str) -> list[dict]:
        sys_prompt = build_system_prompt(lang)

        if lang == "fr":
            presence_note = (
                "Visage présent à la caméra : OUI." if self.face_present else
                "Visage présent à la caméra : NON (l'utilisateur est peut-être parti)."
            )
        else:
            presence_note = (
                "Face present on camera: YES." if self.face_present else
                "Face present on camera: NO (user might be away)."
            )

        msgs = [
            {"role": "system", "content": sys_prompt},
            {"role": "system", "content": presence_note},
        ]
        msgs.extend(list(self.history))
        return msgs


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def apply_live_setting(key: str, value: float) -> str:
    """Changes config values in-memory."""
    key = (key or "").lower().strip()
    
    settings = {
        "niceness": ("NICENESS", lambda v: clamp01(v)),
        "formality": ("FORMALITY", lambda v: clamp01(v)),
        "banter": ("BANTER", lambda v: clamp01(v)),
        "intelligence": ("INTELLIGENCE", lambda v: clamp01(v)),
        "speed": ("SPEECH_RATE", lambda v: int(max(80, min(300, v)))),
        "temperature": ("TEMPERATURE", lambda v: float(max(0.0, min(2.0, v)))),
    }
    
    if key in settings:
        attr, transform = settings[key]
        new_val = transform(value)
        setattr(config, attr, new_val)
        return f"{attr} = {new_val:.2f}" if isinstance(new_val, float) else f"{attr} = {new_val}"
    
    return "Unknown setting."


def main():
    print("=" * 50)
    print("  Local Face + Voice AI")
    print(f"  Model: {config.OLLAMA_MODEL}")
    print("=" * 50)
    
    # Initialize components
    speaker = Speaker()
    convo = Conversation()
    ollama = OllamaClient()

    # Check Ollama status
    if ollama.is_up():
        print(f"[OK] Ollama is running with {config.OLLAMA_MODEL}")
    else:
        print("[!] Ollama is NOT running. Start it with: ollama serve")
        print("    Responses will use fallback mode until Ollama is available.")

    def say_presence_line(present: bool):
        lang = convo.last_lang
        if present:
            phrases = GREETINGS_FR if lang == "fr" else GREETINGS_EN
            text = convo.get_random_phrase(phrases, "greeting")
        else:
            phrases = GOODBYES_FR if lang == "fr" else GOODBYES_EN
            text = convo.get_random_phrase(phrases, "goodbye")
        speaker.say(text, lang)

    def on_face_change(evt: FaceEvent):
        convo.face_present = evt.present
        say_presence_line(evt.present)

    # Start vision
    vision = FacePresence(on_change=on_face_change)
    vision.start()

    # Initialize ASR
    asr = BilingualASR()

    print("\n[READY] Listening...")
    print("Voice commands:")
    print("  - 'stop' / 'arrête'  → interrupt speech")
    print("  - 'quit' / 'quitte'  → exit app")
    print("  - 'clear' / 'efface' → clear conversation history")
    print("  - 'set speed 200'    → change TTS speed")
    print("  - 'set banter 0.8'   → change personality")
    print("")

    stopped = threading.Event()

    def on_heard(heard):
        text = heard.text.strip()
        lang = heard.lang
        convo.last_lang = lang
        
        print(f"\n[YOU:{lang}] {text}")

        # Voice commands
        if is_stop_command(text):
            speaker.stop()
            print("[CMD] Stopped speaking")
            return
            
        if is_quit_command(text):
            print("[CMD] Quitting...")
            stopped.set()
            raise SystemExit

        # Clear command
        if text.lower() in {"clear", "efface", "reset", "recommence"}:
            convo.clear()
            msg = "Conversation cleared." if lang == "en" else "Conversation effacée."
            print(f"[CMD] {msg}")
            speaker.say(msg, lang)
            return

        # Settings command
        set_cmd = parse_set_command(text)
        if set_cmd:
            key, val = set_cmd
            msg = apply_live_setting(key, val)
            print(f"[SET] {msg}")
            speaker.say(msg, lang)
            return

        # Normal conversation
        convo.add_user(text)

        start_time = time.time()
        
        if not ollama.is_up():
            reply = fallback_reply(text, lang)
        else:
            messages = convo.build_messages(lang)
            try:
                reply = ollama.chat(
                    model=config.OLLAMA_MODEL,
                    messages=messages,
                    max_tokens=config.MAX_TOKENS,
                    temperature=config.TEMPERATURE,
                )
            except Exception as e:
                print(f"[ERROR] Ollama: {e}")
                reply = fallback_reply(text, lang)

        elapsed = time.time() - start_time
        
        reply = (reply or "").strip()
        if not reply:
            reply = "..." 

        convo.add_assistant(reply)
        print(f"[AI:{lang}] ({elapsed:.1f}s) {reply}")
        speaker.say(reply, lang)

    # Run ASR loop
    try:
        asr.run(on_heard)
    except SystemExit:
        pass
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")
    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        stopped.set()
        print("[INFO] Shutting down...")
        try:
            vision.stop()
        except Exception:
            pass
        try:
            speaker.close()
        except Exception:
            pass
        print("[INFO] Goodbye!")


if __name__ == "__main__":
    main()
