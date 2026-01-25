"""
Local Face + Voice AI - Assistant modules
"""
from .audio import BilingualASR, Heard, is_stop_command, is_quit_command, parse_set_command
from .llm_ollama import OllamaClient, fallback_reply
from .persona import build_system_prompt
from .tts import Speaker
from .vision import FacePresence, FaceEvent

__all__ = [
    "BilingualASR",
    "Heard",
    "is_stop_command",
    "is_quit_command", 
    "parse_set_command",
    "OllamaClient",
    "fallback_reply",
    "build_system_prompt",
    "Speaker",
    "FacePresence",
    "FaceEvent",
]
