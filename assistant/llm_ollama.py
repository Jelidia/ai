from __future__ import annotations
import requests
import config

class OllamaClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or config.OLLAMA_BASE_URL).rstrip("/")

    def is_up(self) -> bool:
        try:
            r = requests.get(self.base_url, timeout=2)
            return r.status_code < 500
        except Exception:
            return False

    def chat(self, model: str, messages: list[dict], *, max_tokens: int, temperature: float) -> str:
        """
        Uses Ollama's local HTTP API: POST /api/chat
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

def fallback_reply(text: str, lang: str) -> str:
    """
    If Ollama isn't running, we still respond with something.
    """
    t = text.lower().strip()
    if lang == "fr":
        if "bonjour" in t or "salut" in t:
            return "Salut. Mon cerveau local (Ollama) n’est pas lancé, mais je t’entends. Lance Ollama et je deviens beaucoup plus intelligent."
        if "comment" in t and "ça va" in t:
            return "Je vais bien, mais là je suis en mode simple. Lance Ollama et on discute pour vrai."
        return "Je t’ai entendu, mais mon modèle IA local n’est pas actif. Installe/lance Ollama et je réponds comme un vrai assistant."
    else:
        if "hello" in t or "hi" in t:
            return "Hey. I can hear you, but my local brain (Ollama) isn't running yet. Start Ollama and I get way smarter."
        if "how are" in t:
            return "I'm good — just stuck in simple mode. Start Ollama and we can actually talk."
        return "I heard you, but my local AI model isn't running. Install/start Ollama to enable real conversation."
