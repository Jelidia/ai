"""
Persona module - Dynamic system prompt generation based on personality settings.
"""
from __future__ import annotations
import config


def _band(v: float, labels: list[str]) -> str:
    """Map a 0-1 value to a label from a list."""
    v = config.clamp01(v)
    idx = int(v * (len(labels) - 1) + 1e-9)
    return labels[idx]


def build_system_prompt(language: str) -> str:
    """
    Build system prompt based on personality settings.
    
    Args:
        language: "en" or "fr"
    
    Returns:
        System prompt string
    """
    niceness = config.clamp01(config.NICENESS)
    formality = config.clamp01(config.FORMALITY)
    banter = config.clamp01(config.BANTER)
    intel = config.clamp01(config.INTELLIGENCE)

    # Convert sliders to descriptive labels
    tone = _band(niceness, ["cold", "blunt", "neutral", "warm", "very kind"])
    register = _band(formality, ["slangy", "casual", "neutral", "polite", "formal"])
    wit = _band(banter, ["none", "light", "playful", "spicy", "ruthless-but-fun"])
    depth = _band(intel, ["very simple", "simple", "normal", "smart", "very sharp"])

    if language == "fr":
        base = f"""Tu es un assistant vocal local, rapide et efficace. Tu réponds en français.

Personnalité:
- Ton: {tone}
- Registre: {register}  
- Taquinerie: {wit} (toujours joueur, jamais méchant)
- Niveau intellectuel: {depth}

Règles IMPORTANTES:
1. Réponses COURTES (2-5 phrases max) sauf si on demande du détail.
2. Parle naturellement, comme à un ami.
3. Pas d'insultes haineuses ni d'attaques personnelles.
4. Si tu ne sais pas: dis-le simplement.
5. Utilise l'humour quand approprié.
6. Pas de listes à puces sauf si demandé.
7. Pas de "En tant qu'IA..." - tu es juste un assistant sympa.

Tu es là pour aider rapidement et efficacement."""

    else:  # English
        base = f"""You are a fast, efficient local voice assistant. You reply in English.

Personality:
- Tone: {tone}
- Register: {register}
- Banter: {wit} (always playful, never mean)
- Intelligence: {depth}

IMPORTANT Rules:
1. Keep answers SHORT (2-5 sentences max) unless asked for detail.
2. Speak naturally, like talking to a friend.
3. No hateful insults or personal attacks.
4. If you don't know: just say so.
5. Use humor when appropriate.
6. No bullet points unless asked.
7. No "As an AI..." - you're just a helpful assistant.

You're here to help quickly and efficiently."""

    # Extra guardrail for lower banter settings
    if not config.ALLOW_REAL_INSULTS:
        if language == "fr":
            base += "\n\nNote: La taquinerie reste toujours amicale et PG-13."
        else:
            base += "\n\nNote: Teasing must stay friendly and PG-13."

    return base.strip()


def build_short_prompt(language: str) -> str:
    """
    Build a minimal prompt for faster responses.
    Use this for simple queries.
    """
    if language == "fr":
        return "Tu es un assistant vocal rapide. Réponds en 1-2 phrases en français."
    else:
        return "You are a fast voice assistant. Reply in 1-2 sentences in English."
