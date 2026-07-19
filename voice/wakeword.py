"""Wake word detection.

Two engines:

- openwakeword (default): pretrained names ("hey_jarvis") or a path to a
  custom-trained model ("models/hey_cortana.onnx"). Train a custom "hey cortana"
  model with the official Colab notebook:
  https://colab.research.google.com/github/dscripka/openWakeWord/blob/main/notebooks/automatic_model_training.ipynb

- porcupine: Picovoice Porcupine with a .ppn keyword file from
  https://console.picovoice.ai (type the phrase, download). Needs a free
  AccessKey in the PICOVOICE_ACCESS_KEY environment variable.
"""

import os
import queue
from pathlib import Path

import numpy as np
import sounddevice as sd

OWW_CHUNK = 1280  # 80 ms @ 16 kHz, openwakeword's expected frame size


class WakeWordListener:
    """OpenWakeWord engine."""

    def __init__(self, model_name: str = "hey_jarvis", threshold: float = 0.5):
        import openwakeword
        from openwakeword.model import Model

        if model_name.endswith((".onnx", ".tflite")):
            # custom-trained model file (relative paths resolve from repo root)
            path = Path(model_name)
            if not path.is_absolute():
                path = Path(__file__).resolve().parent.parent / path
            if not path.exists():
                raise FileNotFoundError(f"custom wake word model not found: {path}")
            self.model_name = path.stem
            model_ref = str(path)
        else:
            openwakeword.utils.download_models([model_name])
            self.model_name = model_name
            model_ref = model_name

        self.model = Model(wakeword_models=[model_ref], inference_framework="onnx")
        self.threshold = threshold

    def wait_for_wake(self, sample_rate: int = 16000, stop_event=None) -> bool:
        """Block until the wake word is heard. Returns False if stopped."""
        q: queue.Queue[np.ndarray] = queue.Queue()

        def callback(indata, frames, time_info, status):
            q.put(indata[:, 0].copy())

        self.model.reset()
        with sd.InputStream(
            samplerate=sample_rate, channels=1, dtype="int16",
            blocksize=OWW_CHUNK, callback=callback,
        ):
            while True:
                if stop_event is not None and stop_event.is_set():
                    return False
                try:
                    frame = q.get(timeout=0.3)
                except queue.Empty:
                    continue
                prediction = self.model.predict(frame)
                for score in prediction.values():
                    if score >= self.threshold:
                        return True


class PorcupineListener:
    """Picovoice Porcupine engine (custom .ppn keyword files)."""

    def __init__(self, keyword_path: str, sensitivity: float = 0.5):
        import pvporcupine

        access_key = os.environ.get("PICOVOICE_ACCESS_KEY")
        if not access_key:
            raise RuntimeError(
                "Set the PICOVOICE_ACCESS_KEY environment variable "
                "(free key from https://console.picovoice.ai)"
            )
        path = Path(keyword_path)
        if not path.is_absolute():
            path = Path(__file__).resolve().parent.parent / path
        if not path.exists():
            raise FileNotFoundError(f"keyword file not found: {path}")

        self.porcupine = pvporcupine.create(
            access_key=access_key,
            keyword_paths=[str(path)],
            sensitivities=[sensitivity],
        )
        self.model_name = path.stem

    def wait_for_wake(self, sample_rate: int = 16000, stop_event=None) -> bool:
        q: queue.Queue[np.ndarray] = queue.Queue()
        frame_len = self.porcupine.frame_length  # 512 samples @ 16 kHz

        def callback(indata, frames, time_info, status):
            q.put(indata[:, 0].copy())

        with sd.InputStream(
            samplerate=self.porcupine.sample_rate, channels=1, dtype="int16",
            blocksize=frame_len, callback=callback,
        ):
            while True:
                if stop_event is not None and stop_event.is_set():
                    return False
                try:
                    frame = q.get(timeout=0.3)
                except queue.Empty:
                    continue
                if self.porcupine.process(frame) >= 0:
                    return True


def create_wakeword_listener(cfg: dict):
    engine = cfg.get("engine", "openwakeword")
    if engine == "porcupine":
        return PorcupineListener(
            keyword_path=cfg.get("keyword_path", "models/hey_cortana.ppn"),
            sensitivity=cfg.get("threshold", 0.5),
        )
    return WakeWordListener(
        model_name=cfg.get("model", "hey_jarvis"),
        threshold=cfg.get("threshold", 0.5),
    )
