# ECHO — Project Cortana

A persistent AI voice companion inspired by Halo's Cortana. See
[Cortana_Implementation_Summary.md](Cortana_Implementation_Summary.md) for the full design,
and **[GUIDE.md](GUIDE.md) for how to use her day-to-day**.

## Architecture

```
Mic -> Wake word (OpenWakeWord) -> Faster-Whisper (CUDA) -> Conversation Manager
         |                                                        |
         |            Memory (ChromaDB)  Personality (yaml)  Emotion tracker
         |                     \\               |               /
         |                      Claude (Agent SDK, Pro subscription)
         |                          |                \\
         |                     Tool Manager       built-in tools
         |               (desktop, files, browser,  (WebSearch, WebFetch,
         |                screen, system, plugins)   Read, Glob, Grep)
         v                          |
   Floating orb UI  <-  states      v
   (idle/listening/       XTTS v2 -> Speakers
    thinking/speaking)
```

Claude access goes through the **Claude Agent SDK**, which reuses your Claude Code
login (Pro subscription) — no API key needed. Speech recognition, wake word, TTS,
and memory all run locally. Claude never executes anything directly: it emits tool
requests, the tool manager executes them and returns results.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Requirements: Python 3.10+, Node.js (for Claude Code), a logged-in Claude Code
install, a microphone. NVIDIA GPU recommended for Whisper.

First run downloads models: Whisper `small` (~500 MB), wake word (~5 MB),
XTTS v2 (~2 GB — you'll be asked to accept the Coqui CPML license in the
terminal; it's free for personal/non-commercial use).

## Run

```powershell
python main.py --text    # text mode — test the brain without audio
python main.py --push    # push-to-talk — Enter, then speak (orb visible)
python main.py           # full voice — say "Hey Jarvis" (placeholder wake word)
python main.py --no-ui   # any mode without the floating orb
```

## What Cortana can do

- **Converse** with persistent memory across sessions (ChromaDB vector recall).
- **Research**: silent web search/summarize via built-in WebSearch/WebFetch.
- **Desktop**: launch/close apps, clipboard, notifications.
- **Files**: read/search (built-in Read/Glob/Grep), create documents, rename,
  recycle-bin delete (asks for confirmation first).
- **Browser**: open URLs/searches in your real browser.
- **System**: CPU/RAM/GPU/disk/battery stats, top processes.
- **Screen awareness**: on request, screenshots the screen and *looks at it*
  ("what error is on my screen?").
- **Plugins**: drop a folder in `plugins/` with `plugin.yaml` + `tools.py`
  (weather ships as an example, Open-Meteo, no key).
- **Emotional layer**: tracks conversation mood (frustration, urgency,
  excitement, stress) and adapts tone/verbosity.
- **Presence**: floating orb bottom-right — breathing when idle, cyan when
  listening, violet pulse when thinking, rings when speaking. Drag to move,
  right-click to quit.

## Configuration

- `config/personality.yaml` — who Cortana is; injected into every session.
- `config/settings.yaml` — models, devices, tools, UI, memory:
  - `tools.allow_bash: true` gives Cortana a full terminal (off by default).
  - `tts.engine: sapi` for the lightweight Windows voice instead of XTTS.
  - `ui.enabled: false` to never show the orb.

## Notes

- **Wake word:** OpenWakeWord has no pretrained "Cortana" model, so the default
  is `hey_jarvis`. Train a custom "Cortana" model later:
  <https://github.com/dscripka/openWakeWord#training-new-models>
- **GPU:** tuned for a 4 GB card (Whisper `small` fp16). If XTTS doesn't fit
  alongside it, set `tts.device: cpu`.
- **Memory:** conversations are embedded into ChromaDB (`data/memory/`) and
  relevant past exchanges are recalled into each new turn.

## Roadmap

- [x] Phase 1: wake word → STT → Claude → memory → TTS
- [x] Phase 2: tool system (desktop, filesystem, browser, screen, system)
- [x] Phase 3: desktop presence (floating orb UI)
- [x] Phase 4: plugins, screen awareness, vision, emotional layer
- [ ] Future: custom "Cortana" wake word model, avatar — Live2D
      ([AVATAR.md](AVATAR.md)) or Unity/Unreal/Godot 3D
      ([AVATAR_3D.md](AVATAR_3D.md)), smart home (Home Assistant plugin),
      streaming sentence-by-sentence TTS
