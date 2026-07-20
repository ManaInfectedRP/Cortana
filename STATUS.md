# Cortana — Status & Roadmap

A running snapshot of what's actually built and working, plus ideas for
what could make her feel more alive next. See [README.md](README.md) and
[GUIDE.md](GUIDE.md) for setup/usage instructions — this file is about
capability, not how-to.

---

## 1. What's implemented today

### Core voice loop
- Wake word detection ("Hey Cortana", custom-trained via OpenWakeWord) or
  push-to-talk (`--push`, press Enter to speak) or text mode (`--text`).
- Speech-to-text via faster-whisper (CUDA), `small` model tuned for a 4 GB GPU.
- Reasoning via Claude (through the Claude Agent SDK, authenticated with your
  Claude Pro/subscription login — no separate API key or billing).
- Text-to-speech via Coqui XTTS v2, either a built-in speaker or a cloned
  voice from a sample file (`speaker_wav` in settings, ~10-30s clean audio).
  Falls back to Windows SAPI if XTTS is unavailable.
- Robust mic capture: noise-floor calibration, hysteresis-based
  end-of-speech detection, pinned input device by name so virtual mics
  (DroidCam, Voicemod, etc.) can't hijack it.

### Brain / conversation
- `core/conversation.py` — per-turn flow: transcription → emotion update →
  memory recall → prompt build → Claude (+ tool calls) → spoken reply.
- `core/personality.py` — traits, speaking style, and rules loaded from
  `config/personality.yaml`, rendered into Claude's system prompt.
- `core/prompt.py` — injects current date/time, conversation mood hint, and
  relevant memories into every turn.
- `core/emotion.py` — **tracks the user's mood** (not a fake emotion system
  for Cortana) via a hybrid of keyword cues (reliable on explicit language
  like "this is broken") and a small local emotion classifier
  (`j-hartmann/emotion-english-distilroberta-base`, CPU by default per
  `config/settings.yaml`'s `emotion` section so it doesn't compete with
  Whisper/XTTS for the 4 GB GPU budget) that catches subtler phrasing too:
  frustration, urgency, excitement, stress, surprise. Scores decay each
  turn. Feeds a tone hint into the prompt ("user seems frustrated — skip
  the humor") and drives the avatar's facial expression — surprise now
  finally uses the avatar's previously-unused "surprised" preset.
- `core/rapport.py` — **cross-session rapport**: a slow, persisted
  exponential average of each session's mood (`data/rapport.json`), folded
  into the system prompt as a long-term tone hint once enough sessions have
  built up (3+) — e.g. extra warmth after a run of upbeat sessions, extra
  patience after stressed ones. This is what actually changes *how* she
  talks based on accumulated history, distinct from `core/memory.py`'s
  *what she remembers*.
- Time-of-day tone: the prompt always includes the current time, and a
  personality rule tells Claude to let her tone drift subtly with it (more
  energy in the morning, calmer late at night).
- Long-term memory via ChromaDB (`core/memory.py`) — relevant past exchanges
  are recalled and injected into the prompt each turn.

### Tools (in-process MCP servers — Claude calls these directly, no shell)
- **Filesystem**: `create_document` (save notes/lists/drafts to Desktop by
  default), `rename_file`, `delete_file` (moves to Recycle Bin, requires
  verbal confirmation first). Reading/searching use Claude's built-in
  Read/Glob/Grep.
- **Desktop**: `launch_app`, `close_app`, `get_clipboard`/`set_clipboard`,
  `notify` (Windows toast notifications).
- **Browser**: `open_url`, `open_search` (opens in the user's real browser;
  silent research uses Claude's built-in WebSearch/WebFetch instead).
- **System**: `system_stats` (CPU/RAM/disk/GPU/temp/battery),
  `list_processes` (top processes by CPU or memory).
- **Screen**: `capture_screen` — screenshots the desktop, then Claude's
  built-in Read tool actually looks at the image (vision).
- **Alarms**: `set_alarm`, `list_alarms`, `cancel_alarm`, persisted to disk,
  with a background watcher thread that rings due alarms (notification +
  beep).
- **Bash**: available but disabled by default (`tools.allow_bash` in
  settings.yaml) — full shell access is powerful but off unless opted in.
- Optional built-in Claude tools (WebSearch, WebFetch, Read, Glob, Grep) are
  also allowed per `config/settings.yaml`.

### Plugins
- Drop-in plugin system (`plugins/loader.py`) — auto-discovers `plugins/*/`.
- Ships with a weather plugin (`get_weather`, Open-Meteo, no API key) as a
  working example for adding more.

### Avatar (Unity, primary visual presence)
A VRM10 3D avatar rendered in a small, transparent, borderless,
always-on-top desktop window (screen-corner docked, matching the old orb's
UX conventions), driven live over a local WebSocket from the Python process.

- **State machine**: idle / listening / thinking / speaking, each with its
  own pose animation, driven by `CortanaAnimatorDriver.cs` and wired via
  `SetupCortanaAnimator.cs`.
- **Idle variety**: a user-editable pool of idle poses (`CortanaIdlePoseSet`
  ScriptableObject) wired as a hub-and-spoke Animator graph — she cycles
  between poses on a randomized timer, each one always playing its full
  loop before smoothly blending to the next.
- **Facial expressions**: cross-fades between VRM10 presets (happy, angry,
  sad, relaxed, surprised, neutral) — a baseline per state, overridden by
  the user's tracked mood from `core/emotion.py` when strong enough, itself
  overridden by momentary click reactions.
- **Blinking + gaze**: autonomous blinking, Perlin-noise idle wander biased
  per state (thinking looks up-left, etc.), plus occasional glances toward
  the real desktop mouse cursor while idle (`MouseGazeTracker.cs`, Win32
  cursor polling in the build).
- **Breathing motion**: a subtle sine-wave chest-bone rotation
  (`BreathingMotion.cs`), applied after the Animator evaluates each frame's
  pose so it layers under whatever state/animation is currently playing
  without touching any clips.
- **Lip-sync**: mouth-open viseme driven by a live amplitude stream from
  whatever she's saying (`Lipsync.cs` + `voice/audio.py`'s
  `play_with_amplitude`), with a debug "simulate talking" toggle for
  testing without real speech.
- **Click reactions**: click her once for a "poked" reaction (pose + a
  short vocal line in her real voice); 5 clicks and *continuing* past that
  makes her genuinely angry — pose, angry voice line, and a **~30-minute
  facial-expression grudge** that persists well after the animation ends.
  Anti-spam guarded so rapid clicking can't cancel/restart the pose mid-play.
- **Voice cues**: short interjections generated offline with her real XTTS
  voice (`scripts/generate_avatar_sfx.py`) — poke reactions, angry lines,
  a gratitude reaction (fires once when the user thanks/praises her, see
  `core/emotion.py`'s `REACTIONS`), periodic "thinking" hums, rare
  low-frequency idle mutters, and time-of-day-bucketed startup/shutdown
  lines (played from the Python side at launch/exit).
- **Transparent desktop window**: borderless, per-pixel transparent (DWM
  compositing + BitBlt swapchain, not the default Flip Model), corner-docked,
  optional click-through, right-click to quit, stays responsive even when
  another window has focus (`Application.runInBackground`).
- **Debug tooling**, two layers:
  - An in-Inspector Play Mode panel (`CortanaAnimatorDriverEditor.cs`,
    Editor-only, stripped from builds) to fire any state, idle variant,
    expression, poke/angry/gratitude reaction, or fake-talking toggle.
  - A runtime debug menu (`AvatarDebugMenu.cs`) that actually ships in the
    built app - middle-click anywhere on her to toggle it, with buttons for
    state, a random idle variant, poke/angry, and gratitude. Useful for
    demoing/sanity-checking on the real exe without Python or the Editor
    running at all.

### Desktop presence (fallback)
- PySide6 floating orb (`ui/overlay.py`) — transparent, frameless,
  always-on-top, state-colored. Automatically suppressed when the Unity
  avatar is configured and its exe exists, so the two never show at once;
  still used if the avatar isn't built or is disabled.

### Quality of life
- Desktop shortcut + `Start Cortana.bat` — launch without opening
  VSCode or typing a command.
- Graceful shutdown: Ctrl+C, right-click-to-quit on the avatar, or closing
  the window all cleanly signal shutdown, terminate the avatar subprocess,
  and disconnect from Claude — no orphaned processes.
- Any startup/runtime crash now prints a real traceback instead of silently
  exiting (a bug fixed after a bad YAML edit caused silent failures).

---

## 2. Where things live (quick map)

| Concern | Python | Unity |
|---|---|---|
| Entry point | `main.py` | — |
| Conversation/brain | `core/conversation.py`, `core/prompt.py`, `core/personality.py` | — |
| User mood tracking | `core/emotion.py` | consumed via `FacialExpression.SetOverride` |
| Cross-session rapport | `core/rapport.py` → `data/rapport.json` | — |
| Memory | `core/memory.py` (ChromaDB) | — |
| STT/TTS/wake word | `voice/whisper.py`, `voice/tts.py`, `voice/wakeword.py`, `voice/audio.py` | — |
| Startup/shutdown lines | `voice/greetings.py` | — |
| Tools | `tools/*.py`, `plugins/*/` | — |
| Avatar bridge (WebSocket) | `ui/avatar_bridge.py` | `CortanaWebSocketClient.cs` |
| Fallback orb | `ui/overlay.py` | — |
| Avatar state/expression/voice | — | `CortanaAnimatorDriver.cs`, `FacialExpression.cs`, `AvatarSfx.cs` |
| Idle behavior | — | `CortanaIdleVariety.cs`, `BlinkingGaze.cs`, `MouseGazeTracker.cs`, `BreathingMotion.cs` |
| Click reactions | — | `AvatarClickReactions.cs` |
| In-build debug menu | — | `AvatarDebugMenu.cs` (middle-click to open) |
| Lip-sync | `voice/audio.py` (amplitude stream) | `Lipsync.cs` |
| Window transparency | — | `TransparentWindow.cs` |
| Editor setup menus | — | `Assets/Editor/Setup*.cs` (`Cortana` menu) |
| Generated voice cues | `scripts/generate_avatar_sfx.py` → `data/avatar_sfx/` | copied into `Assets/Cortana_Audio/` |

---

## 3. Ideas to make her feel more alive (not yet built)

Roughly ordered by value-for-effort:

- **Wake-word "notice" reaction** — a quick glance + soft sound the instant
  the wake word fires, before the full "listening" state kicks in (currently
  a slightly abrupt transition).
- **"Welcome back" reaction** — if she's been sitting idle for a long
  stretch (you stepped away), a small acknowledgment when you return —
  ties naturally into the existing idle-variety timer.
- **Rare idle easter egg** — a very low-probability special idle
  animation/line, distinct from the regular pool, so the idle loop never
  feels fully "solved" even after you've seen it a lot.
- **Screen-aware idle glances** — loosely tie her occasional idle gaze to
  screen activity (not spatially accurate, just an ambient nod to what
  she's picking up via `capture_screen`).
- **Multi-monitor-aware cursor gaze** — `MouseGazeTracker.cs` already uses
  absolute desktop coordinates, but hasn't been tested/tuned against a
  multi-monitor setup where the cursor may be very far from her window.
- **Positive/negative memory of specific interactions** — e.g. she could
  recall "you poked me a lot last time" the way she already recalls
  conversation content, referencing it in banter.

---

## 4. Known limitations / possible improvements

- **GPU headroom is tight.** A 4 GB card (GTX 1650-class) running XTTS +
  Whisper "small" simultaneously is the ceiling this was tuned for — a
  bigger GPU would allow a larger Whisper model (better transcription) or
  faster/more expressive TTS.
- **Wake word is a single custom-trained model.** Worth periodically
  retraining with more/varied samples if false positives/negatives creep
  up, especially as your mic setup changes.
- **Single-user, single-machine.** No profiles, no remote/mobile access, no
  multi-user memory separation — everything assumes one person on one PC.
- **Avatar transparency depends on a documented Unity 6.x + URP + D3D11
  regression workaround** (disabled Flip Model swapchain). Worth
  periodically checking if a Unity update fixes the underlying bug and the
  workaround can be simplified or removed.
- **No automated tests.** Everything's been verified by hand through actual
  runs; a growing project like this would benefit from at least smoke tests
  around the tool system and prompt building.
