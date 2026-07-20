"""One-off generator for Cortana's avatar sound cues - poke/angry/gratitude
click and mood reactions, thinking hums, rare idle mutters, and
time-of-day-bucketed startup/shutdown lines. Uses the exact same XTTS engine
and voice settings as her real speech (config/settings.yaml's tts section -
built-in speaker or a cloned speaker_wav, whichever is currently configured),
so these sound like her rather than a generic UI blip.

Run once from the repo root with the project's venv active:
    python scripts/generate_avatar_sfx.py

Output goes to data/avatar_sfx/*.wav.
  - poke / angry / gratitude / thinking_hum / idle_mutter: copy into the
    Unity project at Assets/Cortana_Audio/ and assign on the avatar's
    AvatarSfx component (pokeClips / angryClips / gratitudeClips /
    thinkingHumClips / idleMutterClips).
  - startup_<bucket> / shutdown_<bucket>: stay on the Python side - played
    directly by voice/greetings.py at process start/exit, picked by the
    current hour. No Unity copy needed.
"""

import sys
from pathlib import Path

import soundfile as sf
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT_DIR = ROOT / "data" / "avatar_sfx"

# Time buckets shared with voice/greetings.py - keep the hour ranges in sync.
LINES = {
    "poke": ["Hey!", "Ooh!", "Hey, watch it!", "Hm?"],
    "angry": ["Okay, that's enough!", "Hey! Personal space, please.", "I said stop!"],
    # Fires when the user thanks/praises Cortana - see core/emotion.py's
    # "gratitude" keyword cues and REACTIONS.
    "gratitude": ["Aww, you're welcome!", "Happy to help!", "Anytime!",
                  "Glad that worked out!"],
    "thinking_hum": ["Hmm...", "Hmmm, let's see...", "Mmm, one moment...", "Hmm, okay..."],
    # Rare idle mutters - she's not talking TO the user, just thinking out
    # loud for a second. Kept short and low-key so they read as a quirk, not
    # a full line.
    "idle_mutter": [
        "Hm, just thinking.", "...just processing.", "Mm, quiet moment.",
        "Just here.", "Hmm, nothing important.",
    ],
    "startup_morning": ["Good morning. Cortana online.", "Morning. Systems up."],
    "startup_day": ["Cortana online.", "Systems up. Good to be back."],
    "startup_night": ["Cortana online. Burning the midnight oil, I see.",
                       "Systems up. Bit late, isn't it?"],
    "shutdown_day": ["Cortana signing off.", "Powering down for now. Talk soon."],
    "shutdown_night": ["Cortana signing off. Get some sleep.",
                        "Powering down. Don't stay up too late."],
}


def main() -> None:
    with open(ROOT / "config" / "settings.yaml", encoding="utf-8") as f:
        settings = yaml.safe_load(f)
    tts_cfg = settings["tts"]

    from voice.tts import XTTS_SAMPLE_RATE, XTTSEngine

    print("[sfx] loading XTTS with Cortana's configured voice...")
    engine = XTTSEngine(
        device=tts_cfg["device"], speaker=tts_cfg["speaker"],
        language=tts_cfg["language"], speaker_wav=tts_cfg.get("speaker_wav"),
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for category, lines in LINES.items():
        for i, line in enumerate(lines, start=1):
            wav = engine.synthesize(line)
            out_path = OUT_DIR / f"{category}_{i}.wav"
            sf.write(out_path, wav, XTTS_SAMPLE_RATE)
            print(f"[sfx] {out_path.relative_to(ROOT)}  <-  \"{line}\"")

    print(f"[sfx] done - {sum(len(v) for v in LINES.values())} clips in "
          f"{OUT_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
