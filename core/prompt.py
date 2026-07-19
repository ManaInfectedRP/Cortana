"""Per-turn prompt construction: user utterance + context Claude needs."""

import datetime


def build_turn_prompt(
    user_text: str,
    memories: list[str],
    mood: str | None = None,
) -> str:
    now = datetime.datetime.now().strftime("%A %Y-%m-%d %H:%M")
    parts = [f"[Current time: {now}]"]
    if mood:
        parts.append(f"[Conversation mood: {mood}]")
    if memories:
        parts.append("[Relevant memories from past conversations:]")
        parts.extend(f"- {m}" for m in memories)
    parts.append("")
    parts.append(user_text)
    return "\n".join(parts)
