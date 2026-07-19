"""Emotional layer.

Not fake emotions - tracks the *conversation's* mood (stress, excitement,
frustration, urgency) from the user's language and feeds it into the prompt so
Cortana adapts tone, verbosity and humor. Scores decay each turn.
"""

import re

CUES = {
    "frustration": [
        "not working", "doesn't work", "broken", "again", "still", "ugh",
        "annoying", "wtf", "damn", "stupid", "why won't", "hate",
    ],
    "urgency": [
        "asap", "right now", "quickly", "hurry", "urgent", "deadline",
        "immediately", "fast",
    ],
    "excitement": [
        "awesome", "amazing", "cool", "love it", "great", "excellent", "yes!",
        "perfect", "finally",
    ],
    "stress": [
        "stressed", "overwhelmed", "tired", "exhausted", "too much",
        "can't keep up", "anxious",
    ],
}

DECAY = 0.6
THRESHOLD = 0.8


class EmotionTracker:
    def __init__(self):
        self.state = {k: 0.0 for k in CUES}

    def update(self, user_text: str) -> None:
        text = user_text.lower()
        for mood in self.state:
            self.state[mood] *= DECAY
        for mood, words in CUES.items():
            for w in words:
                if w in text:
                    self.state[mood] += 1.0
        # punctuation / caps signals
        if text.count("!") >= 2:
            self.state["urgency"] += 0.5
            self.state["frustration"] += 0.3
        letters = re.sub(r"[^a-zA-Z]", "", user_text)
        if letters and sum(c.isupper() for c in letters) / len(letters) > 0.6 \
                and len(letters) > 8:
            self.state["frustration"] += 1.0

    def describe(self) -> str | None:
        active = [m for m, v in self.state.items() if v >= THRESHOLD]
        if not active:
            return None
        hints = {
            "frustration": "user seems frustrated - be extra helpful and "
                           "solution-focused, skip the humor",
            "urgency": "user is in a hurry - be maximally brief and direct",
            "excitement": "user is excited - match their energy a little",
            "stress": "user seems stressed - be calm, warm and reassuring",
        }
        return "; ".join(hints[m] for m in active)
