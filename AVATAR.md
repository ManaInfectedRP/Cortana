# Giving Cortana a Live2D Avatar

> Looking at 3D instead? Unity, Unreal, and Godot routes are covered in
> [AVATAR_3D.md](AVATAR_3D.md).

How to go from the floating orb to an animated 2D character on your desktop —
what Live2D is, how a model gets made, and how it would plug into this project
(`ui/avatar.py` is the reserved slot for it).

---

## 1. What a Live2D model actually is

Live2D is *not* 3D and *not* frame-by-frame animation. It takes a **single
layered illustration** and deforms its parts in real time — so one drawing can
blink, breathe, tilt its head, follow the mouse, and lip-sync. A finished model
is a folder of files:

| File | What it is |
|---|---|
| `*.moc3` | The rigged model (meshes + deformers) |
| `*.model3.json` | Manifest tying everything together — this is what apps load |
| `textures/*.png` | The artwork atlas |
| `*.physics3.json` | Hair/clothes sway physics |
| `*.motion3.json` | Canned animations (idle, wave, nod) |
| `*.exp3.json` | Expressions (smile, angry, blush) |

The whole pipeline: **art → rigging → export → runtime**.

---

## 2. Step-by-step: making the model

### Step 1 — The artwork (the biggest job)

Draw (or commission) the character as a **PSD with every movable part on its
own layer**: each eyebrow, each eyelid, each iris, upper/lower lip, jaw, hair
front/side/back, torso, each arm segment, accessories. A typical
half-body model has **50–150 layers**. Face drawn straight-on; parts that will
rotate need hidden overlap painted behind neighbors so gaps don't show.

Tools: Clip Studio Paint, Photoshop, or Krita (all export PSD).
Canvas: 3000–4500 px tall is typical for a desktop model.

> Not an artist? Options: free sample models (see §4), marketplace models
> (Booth.pm, nizima.com — many under $50), or commissioning (art + rigging
> for a simple half-body typically starts in the low hundreds).

### Step 2 — Rigging in Live2D Cubism Editor

Download **Cubism Editor** from live2d.com — the **free version is enough to
start** (Pro trial is 42 days; free tier limits mesh/deformer counts but
exports working models).

The rigging loop:
1. **Import the PSD** — each layer becomes an "ArtMesh".
2. **Mesh** each part (auto-mesh, then refine around eyes/mouth).
3. **Deformers** — wrap parts in warp/rotation deformers (jaw in head, head
   in body...).
4. **Parameters** — bind deformations to standard sliders. The ones that
   matter for Cortana:
   - `ParamAngleX/Y/Z` — head turn/tilt
   - `ParamEyeLOpen`, `ParamEyeROpen` — blinking
   - `ParamEyeBallX/Y` — gaze
   - `ParamMouthOpenY` — **lip sync uses this one**
   - `ParamBodyAngleX/Y/Z`, `ParamBreath` — idle life
5. **Physics** — attach hair/clothing sway to head/body params.
6. **Idle motion** — record a subtle breathing/blinking `motion3.json`.

Rigging a first model is genuinely a learn-a-tool experience: budget **a
weekend for a rough first rig**, more for something polished. Live2D's
official YouTube tutorials are good; the community wiki (docs.live2d.com) is
the reference.

### Step 3 — Export for runtime

`File → Export for Runtime → moc3` — produces the folder from §1. Keep
texture atlas at 2048 or 4096 px.

---

## 3. Plugging it into Cortana

Two realistic integration routes:

### Route A — Rendered inside our app (`live2d-py`) ← the plan

There's a Python binding for the official Cubism runtime:
[`live2d-py`](https://github.com/Arkueid/live2d-py) (`pip install live2d-py`).
It renders into any OpenGL context — and PySide6 gives us one via
`QOpenGLWidget`. So the orb window in `ui/overlay.py` gets a sibling:
a frameless, transparent, always-on-top window drawing the model.

State mapping (same signals the orb already receives):

| Cortana state | Avatar behavior |
|---|---|
| idle | idle motion (breathing, occasional blink), slow gaze wander |
| listening | eyes toward screen center, attentive expression |
| thinking | "hmm" expression, eyes up-left, subtle head tilt |
| speaking | **lip sync**: drive `ParamMouthOpenY` from TTS audio amplitude |

Lip sync is simple in practice: while XTTS audio plays, we already have the
waveform — compute RMS per ~50 ms window and feed it to `ParamMouthOpenY`.
`live2d-py` also ships a built-in wav lip-sync helper.

Rough implementation plan for `ui/avatar.py` (when a model exists):
1. `pip install live2d-py PyOpenGL`
2. Load `models/avatar/<name>.model3.json`
3. QOpenGLWidget subclass: init Cubism GL, `model.Update()` + draw each frame
   (reuse the 30 fps QTimer pattern from the orb)
4. Subscribe to the existing `StateBridge.state_changed` signal
5. During `tts.speak`, publish amplitude values → mouth parameter

### Route B — VTube Studio (zero code, quickest visual win)

[VTube Studio](https://denchisoft.com/) (free on Steam) loads any Live2D
model and handles rendering, physics, idle motion itself. Feed it Cortana's
voice: install a virtual audio cable, route XTTS output through it, and VTS
lip-syncs off the audio automatically. Its WebSocket API can trigger
expressions, so a small plugin could still map thinking/listening states.
Downside: separate app, less "hers", no deep integration.

---

## 4. Try-it-today shortcut

You don't need art to prototype the pipeline:

1. Live2D publishes **free sample models** (Hiyori, Mao, etc.) licensed for
   personal use: <https://www.live2d.com/en/learn/sample/>
2. Download one, drop the folder into `models/avatar/`
3. When `ui/avatar.py` gets implemented (Route A), it points at that
   `model3.json` — swap in a custom Cortana model later without touching code

A sensible order: **sample model + Route A integration first** (proves
renderer, states, lip sync), then invest in custom Cortana artwork once it's
fun to look at.

---

## 5. Effort summary

| Piece | Effort |
|---|---|
| Route A renderer in `ui/avatar.py` | a coding session (I can build it when you want) |
| Lip sync wiring | small — we already own the audio buffer |
| Free sample model to prototype | 10 minutes |
| Custom artwork (DIY) | days–weeks depending on skill |
| Custom rigging (DIY, first time) | a weekend for rough, more for polish |
| Marketplace/commissioned model | money instead of time |

**TL;DR:** the code side is modest and fits the existing orb architecture;
the artwork/rigging is the real project. Start with a free sample model to
make it real, then upgrade the art.
