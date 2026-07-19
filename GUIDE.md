# Using Cortana — User Guide

Everything you need to run, talk to, and customize your Cortana (Project ECHO).
For setup/install, see [README.md](README.md).

---

## 1. Starting Cortana

Open a terminal in `E:\repos\Cortana` and activate the environment once per terminal:

```powershell
.venv\Scripts\Activate.ps1
```

Then pick a mode:

| Command | Mode | When to use it |
|---|---|---|
| `python main.py` | **Full voice** | The real deal. Say the wake word, then talk. Orb appears bottom-right. |
| `python main.py --push` | **Push-to-talk** | Press Enter, then speak. No wake word listening. Good in noisy rooms. |
| `python main.py --text` | **Text chat** | Type instead of talking. Fastest way to test; no audio models load. |
| `python main.py --no-ui` | (modifier) | Any mode above without the floating orb. |

First launch downloads models (Whisper ~500 MB, XTTS ~2 GB — accept the Coqui
license prompt in the terminal). Later launches start in seconds.

**Quitting:** say nothing and press `Ctrl+C` in the terminal, type `quit` in
text mode, or right-click the orb → *Quit Cortana*.

---

## 2. Talking to her

The wake word is currently **"Hey Jarvis"** (placeholder — no pretrained
"Cortana" model exists yet). The flow:

1. Orb glows dim blue → she's idle, listening for the wake word.
2. Say **"Hey Jarvis"** → orb turns cyan → *speak your request now*.
3. Stop talking → she detects ~1.2 s of silence and stops recording.
4. Orb pulses violet while she thinks (and uses tools if needed).
5. She answers out loud — orb shows animated rings while speaking.

Tips:
- Speak within ~6 seconds of the wake word, or she goes back to idle.
- One request at a time; she remembers the conversation, so follow-ups like
  *"and what about tomorrow?"* work.
- She's instructed to keep spoken replies short. Ask *"give me the details"*
  if you want more.

### Orb states at a glance

| Orb | Meaning |
|---|---|
| Dim blue, slow breathing | Idle — waiting for wake word |
| Cyan glow | Listening to you |
| Violet pulse | Thinking / using tools |
| Green-teal with rings | Speaking |

Drag the orb anywhere with the left mouse button.

---

## 3. What you can ask for

### Just talk
> "What do you think about mechanical keyboards?" · "Summarize what we talked
> about yesterday." · "Remind me what I said my project deadline was."

She remembers past conversations (see §4).

### Web research (silent, built-in)
> "What's the latest news on the RTX 50 series?" · "Look up how to fix error
> 0x80070057." · "Summarize this article: [paste URL in text mode]"

### Weather (plugin)
> "What's the weather in Stockholm?" · "Will it rain this weekend?"

### Desktop control
> "Open Notepad." · "Launch Chrome." · "Close Spotify." · "Copy that to my
> clipboard." · "What's on my clipboard?" · "Send me a notification in the
> corner saying the build is done."

### Files
> "Read the README in E:\repos\Cortana." · "Find all Python files mentioning
> 'wakeword' in this project." · "Create a shopping list file on my desktop
> with milk, eggs, bread." · "Rename that file to notes-old.txt." ·
> "Delete temp.txt" → she will **ask you to confirm** before recycling it.

### System status
> "How's my PC doing?" · "What's eating my CPU?" · "How much VRAM is in use?"
> · "What's my battery at?"

### Alarms
> "Set an alarm for 07:30 tomorrow called gym." · "Wake me in 20 minutes." ·
> "What alarms do I have?" · "Cancel the gym alarm."

Alarms survive restarts (stored in `data/alarms.json`) but only *ring* —
beeps + a Windows notification — while Cortana is running.

### Screen awareness
> "Look at my screen — what does this error mean?" · "What does this graph
> show?" · "Read the PDF I have open."

She screenshots the display, looks at it, and answers. Only when you ask.

### Everything at once
> "Check the weather in Malmö, and if it's raining tomorrow, create a file on
> my desktop called packing-list.txt with an umbrella on it."

She chains tools on her own.

---

## 4. Memory — how it works

- **Short-term:** the current session's conversation, kept automatically.
- **Long-term:** every exchange is embedded into a local vector database
  (`data/memory/`). When you say something, related past exchanges are
  retrieved and shown to her — so *"continue the database project"* pulls up
  earlier database talk, even weeks later.
- **Transcript:** a plain-text log of everything at `data/memory/transcript.log`.

Reset her memory: stop Cortana and delete the `data/memory/` folder.
Everything is local — nothing is stored in the cloud except your normal
Claude conversation processing.

---

## 5. Customizing her

### Personality — `config/personality.yaml`
Change her voice/traits/speaking style/mission and the rules (e.g. allow
emoji, longer answers, another language). Takes effect on next launch.

### Settings — `config/settings.yaml`

| Setting | What it does |
|---|---|
| `wake_word.model` | Wake word model (`hey_jarvis` for now). `threshold` lower = more sensitive. |
| `stt.model` | Whisper size: `tiny`/`base`/`small`/`medium`. Bigger = more accurate, slower. `small` fits your 4 GB GPU well. |
| `tts.engine` | `xtts` (natural) or `sapi` (lightweight Windows voice). |
| `tts.speaker` | XTTS built-in voice. Try `"Claribel Dervla"`, `"Daisy Studious"`, `"Gracie Wise"`, `"Alison Dietlinde"`, `"Ana Florence"`. |
| `tts.device` | `cpu` if XTTS fights Whisper for VRAM. |
| `claude.model` | `null` = your Claude Code default. Or `"sonnet"` / `"opus"` etc. |
| `tools.allow_bash` | `true` gives her a real terminal. Powerful — off by default. |
| `tools.enabled` | `false` = pure conversation, no PC control. |
| `plugins.enabled` | `false` = don't load `plugins/`. |
| `ui.enabled` | `false` = never show the orb. |
| `audio.silence_s` | How long a pause ends your utterance (raise it if she cuts you off). |

### Writing a plugin
Create `plugins/myplugin/` with two files:

```yaml
# plugins/myplugin/plugin.yaml
name: myplugin
description: What it does.
enabled: true
```

```python
# plugins/myplugin/tools.py
from claude_agent_sdk import tool

@tool("my_tool", "What this tool does and when to use it.", {"arg": str})
async def my_tool(args: dict) -> dict:
    return {"content": [{"type": "text", "text": f"You said {args['arg']}"}]}

TOOLS = [my_tool]
```

Restart Cortana — the loader picks it up automatically. Copy
`plugins/weather/` as a template.

---

## 6. Good to know

- **Your Claude Pro subscription is the brain.** Cortana's requests count
  toward the same usage limits as your Claude Code chats. Heavy all-day use
  can hit the 5-hour/weekly caps — she'll start failing to answer until the
  window resets.
- **Latency:** expect roughly 2–5 s from end of speech to start of reply
  (Whisper + Claude + XTTS). Text mode is faster.
- **Privacy:** audio never leaves your PC — wake word, transcription, and
  voice synthesis are all local. Only the transcribed *text* goes to Claude.
- **She asks before destructive things.** File deletion requires your verbal
  confirmation; closing apps only happens when you explicitly ask.

---

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| Wake word never triggers | Speak clearly ("Hey Jarvis"), check the right mic is Windows' default input, lower `wake_word.threshold` to `0.4`. |
| Want "Hey Cortana" instead | See §8 below. |
| She cuts me off mid-sentence | Raise `audio.silence_s` to `1.5`–`2.0`. |
| She records nothing / "no speech detected" | Check mic volume in Windows; noisy rooms confuse the auto-calibration — try `--push` mode. |
| Transcription is bad | Bump `stt.model` to `medium` (slower), check mic quality. |
| XTTS is slow | Set `tts.device: cpu` frees GPU for Whisper, or `tts.engine: sapi` for instant (robotic) speech. |
| "Sorry, I didn't get a response" | Claude Code auth or usage limit issue — run `claude` in a terminal to check you're logged in / not rate-limited. |
| Orb doesn't appear | `pip show PySide6` should say 6.8.3; run with `--no-ui` to bypass. |
| First reply is very slow | One-time model downloads/warmup. Subsequent replies are much faster. |

---

## 8. Getting "Hey Cortana" as the wake word

There's no pretrained "Cortana" model, but you can have one two ways. The
code already supports both — you only bring the model file.

### Option A — train your own OpenWakeWord model (free, no account)

1. Open the official training notebook in your browser:
   <https://colab.research.google.com/github/dscripka/openWakeWord/blob/main/notebooks/automatic_model_training.ipynb>
2. Runtime → *Change runtime type* → **GPU**, then run the cells top to bottom.
3. Where it asks for the target phrase, enter: **`hey cortana`**
   (you can also add variations like `cortana` in the same run).
4. Wait ~30–60 minutes. It synthesizes thousands of TTS samples of the phrase,
   trains a tiny model, and produces **`hey_cortana.onnx`** for download.
5. Put the file at `E:\repos\Cortana\models\hey_cortana.onnx` (create the
   `models` folder).
6. In `config/settings.yaml`:

   ```yaml
   wake_word:
     engine: openwakeword
     model: models/hey_cortana.onnx
   ```

7. Restart Cortana and say **"Hey Cortana."** If it false-triggers or misses,
   tune `threshold` (higher = stricter) or retrain with more variations.

**Colab error `torchaudio has no attribute 'set_audio_backend'`?** Add a code
cell above the failing step and run:

```python
!sed -i 's/torchaudio\.set_audio_backend("soundfile")/None/' /usr/local/lib/python3.12/dist-packages/torch_audiomentations/utils/io.py
!sed -i 's/torchaudio\.get_audio_backend()/"soundfile"/' /usr/local/lib/python3.12/dist-packages/torch_audiomentations/utils/io.py
```

then re-run the failed cell. (The notebook pins an old augmentation library
that calls a function newer torchaudio removed.)

**Colab error `No module named 'generate_samples'`?** The piper-sample-generator
repo was restructured in v3.0; re-clone it at the old version in a new cell:

```python
%cd /content
!rm -rf piper-sample-generator
!git clone --branch v2.0.0 --depth 1 https://github.com/rhasspy/piper-sample-generator
!wget -O piper-sample-generator/models/en_US-libritts_r-medium.pt 'https://github.com/rhasspy/piper-sample-generator/releases/download/v2.0.0/en_US-libritts_r-medium.pt'
!pip install -q -r piper-sample-generator/requirements.txt
```

then re-run the failed cell.

### Option B — Picovoice Porcupine (instant, but requires a *company* email)

> ⚠️ Picovoice rejects personal email addresses (gmail etc.) at signup.
> If you don't have a work email, use Option A above.

1. Sign up at <https://console.picovoice.ai> and copy your **AccessKey**.
2. In the console: *Porcupine* → type **"Hey Cortana"** → train (seconds) →
   download the Windows `.ppn` file.
3. Save it as `E:\repos\Cortana\models\hey_cortana.ppn`.
4. Set the key for your user (one-time, new terminals pick it up):

   ```powershell
   [Environment]::SetEnvironmentVariable("PICOVOICE_ACCESS_KEY", "your-key-here", "User")
   ```

5. Install the engine and switch config:

   ```powershell
   pip install pvporcupine
   ```

   ```yaml
   wake_word:
     engine: porcupine
     keyword_path: models/hey_cortana.ppn
   ```

6. Restart. Runtime stays fully offline; the key only validates your license.

**Which one?** Option A is the practical choice for personal use (Porcupine's
console requires a company email). Either way, detection runs 100% locally.

---

## 9. Giving her a custom voice (voice cloning)

XTTS can clone any voice from a short audio sample — no training needed.

1. Get a **10–30 second** sample of the voice: one speaker only, clean speech,
   no music/sound effects/reverb. WAV is ideal; MP3 works.
2. Save it as `models/cortana_voice.wav` (or `.mp3` — then update the path in
   settings).
3. `config/settings.yaml` already points at it:

   ```yaml
   tts:
     speaker_wav: models/cortana_voice.wav
   ```

4. Restart. Startup prints `[tts] cloning voice from cortana_voice.wav` when
   it's active. Remove/rename the file to go back to the built-in speaker.

Tips: quality of the sample matters far more than length — a clean 15 s beats
a noisy 60 s. If output sounds warbly, trim silences and background noise from
the sample (Audacity works). Cloning a real person's voice is for your own
personal use — don't publish audio of someone's cloned voice without their
consent.
