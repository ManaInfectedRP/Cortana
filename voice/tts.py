"""Local speech synthesis.

Primary engine: Coqui XTTS v2 (natural, expressive, offline).
Fallback: Windows SAPI via pyttsx3 (robotic but always works).

Note: the first XTTS run downloads the model (~2 GB) and asks you to accept
the Coqui CPML license in the terminal.
"""

import re
from pathlib import Path

import numpy as np

from voice.audio import play, play_with_amplitude

XTTS_SAMPLE_RATE = 24000


def _patch_torchaudio_load() -> None:
    """torchaudio >= 2.9 delegates all decoding to torchcodec, which needs
    shared FFmpeg DLLs that are rarely present on Windows. Swap in a
    soundfile-based decoder (wav/flac/mp3/ogg, bundled libs) so voice cloning
    works without FFmpeg; fall back to the original for anything exotic."""
    import torch
    import torchaudio

    if getattr(torchaudio, "_cortana_patched", False):
        return
    import soundfile as sf

    _orig_load = torchaudio.load

    def load(path, *args, **kwargs):
        try:
            data, sr = sf.read(str(path), dtype="float32", always_2d=True)
            return torch.from_numpy(data.T.copy()), sr
        except Exception:
            return _orig_load(path, *args, **kwargs)

    torchaudio.load = load
    torchaudio._cortana_patched = True


class XTTSEngine:
    def __init__(self, device: str = "auto", speaker: str = "Ana Florence",
                 language: str = "en", speaker_wav: str | None = None):
        import torch

        _patch_torchaudio_load()
        from TTS.api import TTS

        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device
        self.speaker = speaker
        self.language = language

        # voice cloning: a 10-30 s clean sample (wav/mp3) overrides the
        # built-in speaker
        self.speaker_wav = None
        if speaker_wav:
            path = Path(speaker_wav)
            if not path.is_absolute():
                path = Path(__file__).resolve().parent.parent / path
            if path.exists():
                self.speaker_wav = str(path)
                print(f"[tts] cloning voice from {path.name}")
            else:
                print(f"[tts] speaker_wav not found ({path}); "
                      f"using built-in speaker '{speaker}'")

        self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

    # hard cap per sentence — guards against XTTS's runaway-generation bug
    MAX_SENTENCE_SECONDS = 30

    def speak(self, text: str) -> None:
        for sentence in split_sentences(text):
            # unpunctuated text is the classic trigger for endless generation
            if sentence[-1] not in ".!?…":
                sentence += "."
            if self.speaker_wav:
                wav = self.tts.tts(
                    text=sentence, speaker_wav=self.speaker_wav,
                    language=self.language,
                )
            else:
                wav = self.tts.tts(
                    text=sentence, speaker=self.speaker, language=self.language
                )
            wav = np.asarray(wav, dtype=np.float32)
            wav = wav[: XTTS_SAMPLE_RATE * self.MAX_SENTENCE_SECONDS]

            try:
                from ui.avatar_bridge import send_mouth_amplitude
                play_with_amplitude(wav, XTTS_SAMPLE_RATE, send_mouth_amplitude)
            except Exception:
                play(wav, XTTS_SAMPLE_RATE)


class SAPIEngine:
    def __init__(self, **_kwargs):
        import pyttsx3

        self.engine = pyttsx3.init()
        # prefer a female voice if the system has one (Zira on most Windows installs)
        for voice in self.engine.getProperty("voices"):
            if "zira" in voice.name.lower() or "female" in voice.name.lower():
                self.engine.setProperty("voice", voice.id)
                break

    def speak(self, text: str) -> None:
        self.engine.say(text)
        self.engine.runAndWait()


def create_tts(engine: str = "xtts", **kwargs):
    if engine == "xtts":
        try:
            return XTTSEngine(**kwargs)
        except Exception as e:
            print(f"[tts] XTTS unavailable ({e}); falling back to Windows SAPI")
    return SAPIEngine()


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p]
