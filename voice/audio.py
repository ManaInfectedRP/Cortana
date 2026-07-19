"""Microphone capture with energy-based end-of-speech detection, plus playback."""

import queue

import numpy as np
import sounddevice as sd

FRAME_MS = 30


def select_input_device(name_or_index=None) -> str:
    """Pin the input device by index or name substring; return the active name.

    None/empty keeps the system default. Matching is case-insensitive on the
    device name; the first matching input-capable device wins.
    """
    if name_or_index in (None, ""):
        idx = sd.default.device[0]
        return sd.query_devices(idx)["name"] if idx is not None and idx >= 0 \
            else "system default"

    devices = sd.query_devices()
    if isinstance(name_or_index, int):
        idx = name_or_index
    else:
        needle = str(name_or_index).lower()
        idx = next(
            (i for i, d in enumerate(devices)
             if d["max_input_channels"] > 0 and needle in d["name"].lower()),
            None,
        )
        if idx is None:
            print(f"[audio] no input device matching '{name_or_index}'; "
                  "using system default")
            didx = sd.default.device[0]
            return sd.query_devices(didx)["name"] if didx is not None else "default"

    sd.default.device = (idx, sd.default.device[1])
    return devices[idx]["name"]


def record_utterance(
    sample_rate: int = 16000,
    max_seconds: float = 20.0,
    silence_seconds: float = 1.2,
    start_timeout: float = 8.0,
    stop_event=None,
    threshold_override: float | None = None,
) -> np.ndarray | None:
    """Record one utterance. Returns int16 mono audio, or None if no speech.

    Speech detection is relative to the ambient noise floor (median of the
    first ~300 ms), with hysteresis so quiet word-endings don't end the
    utterance early. `threshold_override` pins the start threshold for mics
    where auto-calibration misbehaves.
    """
    from collections import deque

    frame_len = int(sample_rate * FRAME_MS / 1000)
    q: queue.Queue[np.ndarray] = queue.Queue()

    def callback(indata, frames, time_info, status):
        q.put(indata[:, 0].copy())

    def next_frame() -> np.ndarray | None:
        """Blocking get that stays interruptible via stop_event."""
        while True:
            if stop_event is not None and stop_event.is_set():
                return None
            try:
                return q.get(timeout=0.3)
            except queue.Empty:
                continue

    frames: list[np.ndarray] = []
    prebuffer: deque[np.ndarray] = deque(maxlen=5)  # so the first syllable isn't clipped
    speech_started = False
    consecutive_above = 0
    silence_frames = 0
    waited_frames = 0
    max_frames = int(max_seconds * 1000 / FRAME_MS)
    silence_needed = int(silence_seconds * 1000 / FRAME_MS)
    start_limit = int(start_timeout * 1000 / FRAME_MS)

    with sd.InputStream(
        samplerate=sample_rate, channels=1, dtype="int16", blocksize=frame_len,
        callback=callback,
    ):
        # calibrate noise floor: median of the first ~300 ms (robust to spikes)
        noise_levels = []
        for _ in range(10):
            frame = next_frame()
            if frame is None:
                return None
            noise_levels.append(_rms(frame))
        noise = float(np.median(noise_levels))

        if threshold_override:
            start_threshold = float(threshold_override)
        else:
            start_threshold = max(noise * 1.4, 80.0)
        stop_threshold = start_threshold * 0.8  # hysteresis

        peak = 0.0
        while len(frames) < max_frames:
            frame = next_frame()
            if frame is None:
                return None
            level = _rms(frame)
            peak = max(peak, level)

            if not speech_started:
                prebuffer.append(frame)
                waited_frames += 1
                if level > start_threshold:
                    consecutive_above += 1
                    if consecutive_above >= 2:  # 2 frames = not just a click
                        speech_started = True
                        frames.extend(prebuffer)
                else:
                    consecutive_above = 0
                if waited_frames > start_limit:
                    ratio = peak / noise if noise > 0 else 0
                    print(f"[audio] no speech: noise floor {noise:.0f}, "
                          f"threshold {start_threshold:.0f}, loudest heard "
                          f"{peak:.0f} (only {ratio:.1f}x the noise floor). "
                          "Windows Sound settings -> your mic -> Properties "
                          "-> Levels tab -> raise 'Microphone Boost' (not "
                          "just Volume) by +10-20dB. Or set audio.threshold "
                          f"in settings.yaml below {peak:.0f}.")
                    return None
            else:
                frames.append(frame)
                if level > stop_threshold:
                    silence_frames = 0
                else:
                    silence_frames += 1
                    if silence_frames >= silence_needed:
                        break

    if not frames:
        return None
    return np.concatenate(frames)


def play(audio: np.ndarray, sample_rate: int) -> None:
    sd.play(audio, sample_rate)
    sd.wait()


def _rms(frame: np.ndarray) -> float:
    return float(np.sqrt(np.mean(frame.astype(np.float64) ** 2)))
