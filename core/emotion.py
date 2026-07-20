"""Emotional layer.

Not fake emotions for Cortana herself - tracks the *user's* mood (stress,
excitement, frustration, urgency, surprise, gratitude) from their language
and feeds it into the prompt so Cortana adapts tone, verbosity and humor,
and into the avatar's facial expression (and, for gratitude specifically, a
one-shot voice reaction - see REACTIONS/triggered_reaction()). Scores decay
each turn.

Frustration/excitement/stress/surprise are read from two complementary
sources, both applied every turn:
  1. Keyword cues (the original approach) - reliable on explicit, obvious
     language ("this is broken", "amazing"), and run unconditionally rather
     than only as a fallback. Kept because in testing, a small
     general-purpose emotion classifier under-rates blunt tech-support
     venting like "it's still broken" as anger - it reads closer to mild
     sadness to a model trained on more general text than a human would
     call it, and keywords catch what the classifier misses.
  2. A local emotion classifier (j-hartmann/emotion-english-distilroberta-
     base, ~330MB, CPU by default - see config/settings.yaml's `emotion`
     section, to avoid competing with Whisper/XTTS for the tight 4GB GPU
     budget) - adds coverage for subtler phrasing with no exact keyword hit.
     Optional: if it can't load (offline, download failed, disk full), only
     the keyword signal runs and Cortana still works, just less nuanced.

Urgency stays purely keyword-based - it's a discourse/politeness signal, not
really an emotion a sentiment classifier would capture.
"""

import re

MODEL_NAME = "j-hartmann/emotion-english-distilroberta-base"

URGENCY_CUES = [
    "asap", "right now", "quickly", "hurry", "urgent", "deadline",
    "immediately", "fast",
]

KEYWORD_CUES = {
    "frustration": [
        "not working", "doesn't work", "broken", "again", "still", "ugh",
        "annoying", "wtf", "damn", "stupid", "why won't", "hate",
    ],
    "excitement": [
        "awesome", "amazing", "cool", "love it", "great", "excellent", "yes!",
        "perfect", "finally",
    ],
    "stress": [
        "stressed", "overwhelmed", "tired", "exhausted", "too much",
        "can't keep up", "anxious",
    ],
    "surprise": ["whoa", "wow", "no way", "seriously?", "what?!", "can't believe"],
    # Doesn't try to filter "no thanks" (declining, not thanking) - a false
    # positive there is harmless (worst case a slightly-too-happy beat), and
    # every other category here has the same kind of naive substring match.
    "gratitude": [
        "thanks", "thank you", "thx", "good job", "well done", "nice work",
        "appreciate it", "you're the best", "great job",
    ],
}

DECAY = 0.6
THRESHOLD = 0.8
CLASSIFIER_GAIN = 1.2  # amplifies a confident single-turn read past THRESHOLD

# Facial expression to show on the avatar while a mood is active - see
# ui/avatar_bridge.py's "emotion" field and Unity's FacialExpression.cs.
# Names must match the VRM10 expression presets (happy/angry/sad/relaxed/
# surprised/neutral).
EXPRESSIONS = {
    "frustration": "relaxed",   # calming, reassuring - not mirroring the user
    "stress": "relaxed",
    "urgency": "neutral",       # focused, no extra warmth to slow things down
    "excitement": "happy",
    "surprise": "surprised",
    "gratitude": "happy",
}

HINTS = {
    "frustration": "user seems frustrated - be extra helpful and "
                   "solution-focused, skip the humor",
    "urgency": "user is in a hurry - be maximally brief and direct",
    "excitement": "user is excited - match their energy a little",
    "stress": "user seems stressed - be calm, warm and reassuring",
    "surprise": "user seems caught off guard - a brief acknowledgment is fine",
    "gratitude": "user is thanking or praising you - accept it warmly and "
                 "briefly, don't over-explain",
}

# Moods that trigger a one-shot avatar voice reaction (see AvatarSfx.cs on
# the Unity side) in addition to the per-turn expression/prompt-hint - not
# every mood needs a dedicated voice line, so this is a subset of EXPRESSIONS.
REACTIONS = {"gratitude"}


class EmotionTracker:
    def __init__(self, enabled: bool = True, device: str = "cpu"):
        self.state = {k: 0.0 for k in (*KEYWORD_CUES, "urgency")}
        self._joy_sum = 0.0
        self._strain_sum = 0.0
        self._turns = 0
        self._classifier = None

        if enabled:
            try:
                from transformers import pipeline

                dev = 0 if device == "cuda" else -1
                print(f"[emotion] loading {MODEL_NAME} ({device})...")
                self._classifier = pipeline(
                    "text-classification", model=MODEL_NAME, top_k=None, device=dev,
                )
            except Exception as e:
                print(f"[emotion] classifier unavailable ({e}); "
                      "keyword-only mood detection")

    @property
    def has_data(self) -> bool:
        """True once at least one turn has been read - used to avoid
        recording an empty/never-started session into core/rapport.py."""
        return self._turns > 0

    def update(self, user_text: str) -> None:
        text = user_text.lower()
        for mood in self.state:
            self.state[mood] *= DECAY

        for w in URGENCY_CUES:
            if w in text:
                self.state["urgency"] += 1.0

        for mood, words in KEYWORD_CUES.items():
            for w in words:
                if w in text:
                    self.state[mood] += 1.0

        if self._classifier is not None:
            self._add_classifier_scores(user_text)

        # punctuation / caps signals
        if text.count("!") >= 2:
            self.state["urgency"] += 0.5
            self.state["frustration"] += 0.3
        letters = re.sub(r"[^a-zA-Z]", "", user_text)
        if letters and sum(c.isupper() for c in letters) / len(letters) > 0.6 \
                and len(letters) > 8:
            self.state["frustration"] += 1.0

        self._turns += 1
        self._joy_sum += min(1.0, self.state["excitement"])
        self._strain_sum += min(1.0, max(self.state["frustration"], self.state["stress"]))

    def _add_classifier_scores(self, user_text: str) -> None:
        scores = {r["label"]: r["score"] for r in self._classifier(user_text)[0]}
        self.state["excitement"] += scores.get("joy", 0.0) * CLASSIFIER_GAIN
        self.state["frustration"] += scores.get("anger", 0.0) * CLASSIFIER_GAIN
        self.state["stress"] += (
            max(scores.get("fear", 0.0), scores.get("sadness", 0.0)) * CLASSIFIER_GAIN
        )
        self.state["surprise"] += scores.get("surprise", 0.0) * CLASSIFIER_GAIN

    def _dominant(self) -> str | None:
        """Strongest mood past THRESHOLD, or None. Single-mood on purpose:
        with keyword + classifier signals both contributing, a strong spike
        takes a couple of turns to decay back out, and joining every active
        mood's hint could surface a stale one alongside the current one
        (e.g. "user seems frustrated... user is excited" when the
        excitement was really just residue from the previous message)."""
        active = [(m, v) for m, v in self.state.items() if v >= THRESHOLD]
        if not active:
            return None
        return max(active, key=lambda kv: kv[1])[0]

    def describe(self) -> str | None:
        mood = self._dominant()
        return HINTS.get(mood) if mood else None

    def expression(self) -> str | None:
        """Avatar facial-expression hint, or None to use the current state's
        default (see Unity's FacialExpression.cs)."""
        mood = self._dominant()
        return EXPRESSIONS.get(mood) if mood else None

    def triggered_reaction(self) -> str | None:
        """Name of a one-shot avatar voice reaction to fire this turn (see
        REACTIONS), or None. Distinct from expression() because more than
        one mood can map to the same expression - e.g. gratitude and
        excitement both read as "happy" - but only gratitude has its own
        voice line, so callers need to know WHICH mood won, not just what
        face to show."""
        mood = self._dominant()
        return mood if mood in REACTIONS else None

    def session_averages(self) -> tuple[float, float]:
        """(joy_avg, strain_avg) across this session's turns, for
        core/rapport.py to fold into the long-term cross-session signal.
        (0.0, 0.0) if no turns happened yet - check has_data first."""
        if self._turns == 0:
            return 0.0, 0.0
        return self._joy_sum / self._turns, self._strain_sum / self._turns
