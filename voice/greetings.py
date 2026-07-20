"""Time-of-day-aware startup/shutdown voice lines - pre-rendered by
scripts/generate_avatar_sfx.py (same XTTS voice as her real speech) and
picked here by the current hour. See config/personality.yaml's time-of-day
rule for how her spoken *replies* also drift with time of day - this covers
the two moments (launch/exit) that happen outside any conversation turn.
"""

import datetime
import random
from pathlib import Path

import soundfile as sf

from voice.audio import play, play_with_amplitude

ROOT = Path(__file__).resolve().parent.parent
SFX_DIR = ROOT / "data" / "avatar_sfx"


def _bucket(hour: int | None = None) -> str:
    """Keep these hour ranges in sync with generate_avatar_sfx.py's LINES keys."""
    hour = datetime.datetime.now().hour if hour is None else hour
    if 5 <= hour < 11:
        return "morning"
    if hour >= 21 or hour < 5:
        return "night"
    return "day"


def _play_random(prefix: str) -> bool:
    """Play a random clip matching data/avatar_sfx/{prefix}_*.wav. False
    (silent no-op) if none exist - safe even if generation hasn't run yet."""
    candidates = sorted(SFX_DIR.glob(f"{prefix}_*.wav"))
    if not candidates:
        return False
    path = random.choice(candidates)
    wav, sr = sf.read(str(path), dtype="float32")
    try:
        from ui.avatar_bridge import send_mouth_amplitude
        play_with_amplitude(wav, sr, send_mouth_amplitude)
    except Exception:
        play(wav, sr)
    return True


def play_startup() -> bool:
    return _play_random(f"startup_{_bucket()}")


def play_shutdown() -> bool:
    # only two shutdown buckets - "morning" still gets the "day" line
    bucket = "night" if _bucket() == "night" else "day"
    return _play_random(f"shutdown_{bucket}")
