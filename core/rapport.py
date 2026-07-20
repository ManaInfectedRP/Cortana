"""Cross-session rapport.

core/emotion.py's EmotionTracker resets to zero every process start - it's
deliberately reactive, within a single conversation. This module is the slow
counterpart: a persisted, exponentially-averaged read on how sessions have
been trending over days/weeks, folded into Personality.system_prompt() as a
long-term tone hint. This is what actually changes HOW Cortana talks based
on accumulated history - core/memory.py (ChromaDB) already covers WHAT she
remembers, but recalling a fact never changed her tone.
"""

import json
from pathlib import Path

RAPPORT_FILE = Path(__file__).resolve().parent.parent / "data" / "rapport.json"

ALPHA = 0.15               # slow EMA - takes several sessions to meaningfully shift
MIN_SESSIONS_FOR_HINT = 3  # don't act on rapport until there's enough history


class Rapport:
    def __init__(self, path: Path = RAPPORT_FILE):
        self.path = Path(path)
        self._data = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"sessions": 0, "warmth_ema": 0.0, "strain_ema": 0.0}

    def record_session(self, joy_avg: float, strain_avg: float) -> None:
        """Blend one session's averaged mood (from
        EmotionTracker.session_averages(), only call if .has_data) into the
        long-term EMA and persist."""
        d = self._data
        d["warmth_ema"] = d.get("warmth_ema", 0.0) + ALPHA * (joy_avg - d.get("warmth_ema", 0.0))
        d["strain_ema"] = d.get("strain_ema", 0.0) + ALPHA * (strain_avg - d.get("strain_ema", 0.0))
        d["sessions"] = d.get("sessions", 0) + 1
        self._data = d
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(d, indent=2), encoding="utf-8")

    def describe(self) -> str | None:
        """Long-term tone hint for Personality.system_prompt(), or None if
        there's not enough history yet or nothing notable to say."""
        d = self._data
        if d.get("sessions", 0) < MIN_SESSIONS_FOR_HINT:
            return None
        if d.get("strain_ema", 0.0) > 0.35:
            return ("Recent sessions with this user have trended stressed or "
                     "frustrated - default to extra patience and warmth, go "
                     "lighter on jokes than usual until that eases.")
        if d.get("warmth_ema", 0.0) > 0.45:
            return ("This user has been consistently upbeat and engaged across "
                     "recent sessions - a bit more playfulness and personality "
                     "is welcome.")
        return None
