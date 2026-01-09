"""
Ollama LLM Client - Local AI inference
Supports both streaming and non-streaming modes.
"""
from __future__ import annotations
import requests
import json
import config


class OllamaClient:
    """Client for Ollama local LLM API."""
    
    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or config.OLLAMA_BASE_URL).rstrip("/")

    def is_up(self) -> bool:
        """Check if Ollama server is running."""
        try:
            r = requests.get(self.base_url, timeout=2)
            return r.status_code < 500
        except Exception:
            return False

    def list_models(self) -> list[str]:
        """List available models."""
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=5)
            r.raise_for_status()
            data = r.json()
            return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            return []

    def chat(self, model: str, messages: list[dict], *, max_tokens: int, temperature: float) -> str:
        """
        Send chat request to Ollama (non-streaming).
        """
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": float(temperature),
                "num_predict": int(max_tokens),
            },
        }
        
        r = requests.post(url, json=payload, timeout=config.OLLAMA_TIMEOUT_SEC)
        r.raise_for_status()
        data = r.json()
        msg = data.get("message", {}) or {}
        return (msg.get("content") or "").strip()

    def chat_stream(self, model: str, messages: list[dict], *, max_tokens: int, temperature: float):
        """
        Send chat request to Ollama with streaming.
        Yields tokens as they arrive.
        """
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": float(temperature),
                "num_predict": int(max_tokens),
            },
        }
        
        with requests.post(url, json=payload, stream=True, timeout=config.OLLAMA_TIMEOUT_SEC) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        msg = data.get("message", {}) or {}
                        token = msg.get("content", "")
                        if token:
                            yield token
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue

    def chat_stream_full(self, model: str, messages: list[dict], *, max_tokens: int, temperature: float) -> str:
        """
        Streaming chat that returns full response.
        Faster time-to-first-token than non-streaming.
        """
        tokens = []
        for token in self.chat_stream(model, messages, max_tokens=max_tokens, temperature=temperature):
            tokens.append(token)
        return "".join(tokens).strip()


def fallback_reply(text: str, lang: str) -> str:
    """
    Fallback responses when Ollama isn't running.
    """
    t = text.lower().strip()
    
    if lang == "fr":
        if any(w in t for w in ["bonjour", "salut", "hey", "coucou"]):
            return "Salut ! Mon cerveau local (Ollama) n'est pas lancé. Lance Ollama et je deviens beaucoup plus intelligent."
        if "comment" in t and ("ça va" in t or "tu vas" in t):
            return "Je vais bien, mais là je suis en mode simple. Lance Ollama et on discute pour vrai."
        if any(w in t for w in ["merci", "thanks"]):
            return "De rien ! Mais lance Ollama pour des vraies conversations."
        if "?" in text:
            return "Bonne question ! Mais mon cerveau IA n'est pas actif. Lance Ollama et je pourrai vraiment t'aider."
        return "Je t'entends, mais mon modèle IA local n'est pas actif. Lance Ollama pour de vraies conversations."
    
    else:  # English
        if any(w in t for w in ["hello", "hi", "hey", "yo"]):
            return "Hey! I can hear you, but my local brain (Ollama) isn't running. Start Ollama and I get way smarter."
        if "how are" in t or "how's it going" in t:
            return "I'm good — just stuck in simple mode. Start Ollama and we can actually talk."
        if any(w in t for w in ["thanks", "thank you"]):
            return "You're welcome! But start Ollama for real conversations."
        if "?" in text:
            return "Good question! But my AI brain isn't active. Start Ollama and I can actually help you."
        return "I heard you, but my local AI model isn't running. Install and start Ollama to enable real conversation."
