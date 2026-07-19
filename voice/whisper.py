"""Local speech recognition via Faster-Whisper."""

import os
from pathlib import Path

import numpy as np


def _add_torch_cuda_dlls() -> None:
    """ctranslate2 on Windows needs CUDA/cuDNN DLLs; torch's wheel bundles them."""
    try:
        import torch

        lib = Path(torch.__file__).parent / "lib"
        if lib.is_dir():
            os.add_dll_directory(str(lib))
            os.environ["PATH"] = str(lib) + os.pathsep + os.environ.get("PATH", "")
    except Exception:
        pass


class SpeechRecognizer:
    def __init__(self, model_size: str = "small", device: str = "auto",
                 language: str = "en"):
        _add_torch_cuda_dlls()
        from faster_whisper import WhisperModel

        self.language = language
        if device in ("auto", "cuda"):
            try:
                self.model = WhisperModel(
                    model_size, device="cuda", compute_type="float16"
                )
                self.device = "cuda"
                return
            except Exception as e:
                if device == "cuda":
                    raise
                print(f"[stt] CUDA unavailable ({e}); falling back to CPU")
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        self.device = "cpu"

    def transcribe(self, audio_int16: np.ndarray) -> str:
        audio = audio_int16.astype(np.float32) / 32768.0
        segments, _info = self.model.transcribe(
            audio, language=self.language, vad_filter=True, beam_size=5
        )
        return " ".join(s.text.strip() for s in segments).strip()
