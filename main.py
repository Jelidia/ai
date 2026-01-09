from __future__ import annotations
import threading
from collections import deque
import random

import config
from assistant.tts import Speaker
from assistant.vision import FacePresence, FaceEvent
from assistant.audio import BilingualASR, is_stop_command, is_quit_command, parse_set_command
from assistant.llm_ollama import OllamaClient, fallback_reply
from assistant.persona import build_system_prompt

def _load_lines(path: str) -> list[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]
            return lines
    except Exception:
        return []

GREETINGS_EN = _load_lines("phrases/greetings_en.txt") or [
    "Hey! I see you.",
    "Hi — you’re back.",
    "Hello there.",
    "Oh, a human. Nice.",
    "Hi. I’m listening.",
]
GREETINGS_FR = _load_lines("phrases/greetings_fr.txt") or [
    "Salut, je te vois.",
    "Hey, te revoilà.",
    "Bonjour.",
    "Oh, un humain. Nice.",
    "Salut. Je t’écoute.",
]
GOODBYES_EN = _load_lines("phrases/goodbyes_en.txt") or [
    "Where’d you go?",
    "I lost your face. Still there?",
    "Okay, goodbye for now.",
    "Hey—don’t vanish on me.",
]
GOODBYES_FR = _load_lines("phrases/goodbyes_fr.txt") or [
    "T’es où ?",
    "Je ne te vois plus. T’es encore là ?",
    "Ok, à plus.",
    "Hey—reviens.",
]

class Conversation:
    def __init__(self):
        self.history = deque(maxlen=max(2, int(config.HISTORY_TURNS) * 2))  # user+assistant pairs
        self.face_present = False
        self.last_lang = "en"

    def add_user(self, text: str):
        self.history.append({"role": "user", "content": text})

    def add_assistant(self, text: str):
        self.history.append({"role": "assistant", "content": text})

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
    """
    Changes config values in-memory (doesn't rewrite the file).
    """
    key = (key or "").lower().strip()
    if key == "niceness":
        config.NICENESS = clamp01(value)
        return f"NICENESS = {config.NICENESS:.2f}"
    if key == "formality":
        config.FORMALITY = clamp01(value)
        return f"FORMALITY = {config.FORMALITY:.2f}"
    if key == "banter":
        config.BANTER = clamp01(value)
        return f"BANTER = {config.BANTER:.2f}"
    if key == "intelligence":
        config.INTELLIGENCE = clamp01(value)
        return f"INTELLIGENCE = {config.INTELLIGENCE:.2f}"
    if key == "speed":
        v = int(max(80, min(300, value)))
        config.SPEECH_RATE = v
        return f"SPEECH_RATE = {config.SPEECH_RATE}"
    if key == "temperature":
        config.TEMPERATURE = float(max(0.0, min(2.0, value)))
        return f"TEMPERATURE = {config.TEMPERATURE:.2f}"
    return "Unknown setting."

def main():
    speaker = Speaker()
    convo = Conversation()
    ollama = OllamaClient()

    def say_presence_line(present: bool):
        lang = convo.last_lang
        if present:
            text = random.choice(GREETINGS_FR if lang == "fr" else GREETINGS_EN)
        else:
            text = random.choice(GOODBYES_FR if lang == "fr" else GOODBYES_EN)
        speaker.say(text, lang)

    def on_face_change(evt: FaceEvent):
        convo.face_present = evt.present
        say_presence_line(evt.present)

    vision = FacePresence(on_change=on_face_change)
    vision.start()

    asr = BilingualASR()

    print("Local Face + Voice AI running.")
    print("Voice commands: 'stop/arrête' to interrupt, 'quit/quitte' to exit.")
    print("Optional: set WAKE_WORDS_ENABLED=True in config.py if it responds to background noise.")

    stopped = threading.Event()

    def on_heard(heard):
        text = heard.text.strip()
        lang = heard.lang
        convo.last_lang = lang
        print(f"[HEARD:{lang} conf={heard.confidence:.2f}] {text}")

        # Voice commands
        if is_stop_command(text):
            speaker.stop()
            return
        if is_quit_command(text):
            stopped.set()
            raise SystemExit

        set_cmd = parse_set_command(text)
        if set_cmd:
            key, val = set_cmd
            msg = apply_live_setting(key, val)
            print("[SET]", msg)
            speaker.say(msg, lang)
            return

        # Normal conversation
        convo.add_user(text)

        if not ollama.is_up():
            reply = fallback_reply(text, lang)
        else:
            messages = convo.build_messages(lang)
            reply = ollama.chat(
                model=config.OLLAMA_MODEL,
                messages=messages,
                max_tokens=config.MAX_TOKENS,
                temperature=config.TEMPERATURE,
            )

        reply = (reply or "").strip()
        if not reply:
            reply = "..." if lang == "en" else "..."

        convo.add_assistant(reply)
        print(f"[AI:{lang}] {reply}")
        speaker.say(reply, lang)

    # Run ASR loop
    try:
        asr.run(on_heard)
    except SystemExit:
        pass
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print("[ERROR]", e)
    finally:
        stopped.set()
        try:
            vision.stop()
        except Exception:
            pass
        try:
            speaker.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()
