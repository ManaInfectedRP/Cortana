# 3D Avatar Routes: Unity and Unreal

Companion to [AVATAR.md](AVATAR.md) (Live2D). The design doc lists three
avatar engines — Live2D, Unity, Godot — and Unreal is the fourth obvious
candidate. This covers how the 3D routes would work for Cortana.

---

## 0. The shared architecture (applies to every engine)

A game engine can't live inside our Python process — it runs as its **own
executable** rendering the character in a borderless always-on-top window.
Cortana talks to it over a local WebSocket:

```
Cortana (Python)                       Avatar app (Unity/Unreal/Godot)
   voice loop ──► ws://localhost:8765 ──► state machine + animations
                    {"state": "thinking"}
                    {"state": "speaking", "mouth": 0.62}   ~30 msgs/s while talking
```

- `state`: `idle | listening | thinking | speaking` — same four states the
  orb already receives, so the Python side is a small addition
  (`ui/avatar_bridge.py`: a websocket broadcaster fed by the existing
  `StateBridge`, plus per-chunk audio amplitude during TTS playback for
  mouth movement).
- The engine app maps states to animations and drives the mouth
  blendshape/morph from `mouth`.
- Because the protocol is engine-agnostic, you can prototype in one engine
  and switch later without touching Cortana.

**Hardware reality check:** your GTX 1650 (4 GB) already runs Whisper (and
XTTS when on GPU). Whatever renders the avatar shares that budget —
lightweight rendering matters more than raw fidelity here.

---

## 1. Unity route (the practical 3D choice)

### Getting a character

- **VRoid Studio** (free, by Pixiv): a character-creator for anime-style 3D
  models — sliders + painting, no modeling skills needed. Exports **VRM**,
  an open humanoid-avatar format with standardized blendshapes (blink,
  visemes A/I/U/E/O) and spring-bone hair/clothes physics. This is the
  fastest path to "a Cortana that looks how I want." Step-by-step:
  [VROID_GUIDE.md](VROID_GUIDE.md).
- Alternatives: buy a VRM/humanoid model (Booth.pm, Unity Asset Store), or
  build in Blender and rig to Unity's Humanoid.

### Building the avatar app

1. Unity (LTS) + **URP** template, small window (e.g. 500×800), borderless.
2. Import **UniVRM** (github.com/vrm-c/UniVRM) → drag your `.vrm` in; you get
   the character with blendshape proxy + spring bones working.
3. **Animator** with four states mapped 1:1 to Cortana's states — idle sway /
   attentive lean-in / thinking pose / talking gestures. Free humanoid
   animations: Mixamo (adobe), Unity asset store.
4. **Blinking + gaze**: simple C# coroutines (random blink every 2–6 s; slight
   camera-facing look-at).
5. **Lip sync**: cheap and good-enough = drive the `A` viseme blendshape
   directly from the `mouth` amplitude Cortana sends. Fancier: **uLipSync**
   (free, analyses audio into real visemes) fed by loopback audio.
6. **WebSocket client**: NativeWebSocket (free) — connect to
   `ws://localhost:8765`, parse the JSON, set animator/blendshape values.
7. Build → a ~100–200 MB standalone exe that Cortana's `ui/avatar.py` can
   auto-launch at startup.

Transparent/cutout desktop window (character floating without a rectangle)
is possible on Windows via a small native-window styling script (the
"click-through transparent Unity window" trick — well documented in the
Unity community). Start with a normal window; make it fancy later.

**Perf:** a single VRM character in URP idles at trivial GPU cost — fine
alongside Whisper on the 1650.

**Effort:** comfortable weekend for someone new to Unity; the character
itself is hours in VRoid, not weeks.

---

## 2. Unreal route (maximum fidelity, maximum weight)

The headline attraction is **MetaHuman** — Epic's photorealistic human
creator (free with Unreal). A browser-based editor produces a
cinematic-quality digital human with a full facial rig.

How it would work:

1. Unreal Engine 5 + MetaHuman plugin; create the character in MetaHuman
   Creator, import via Quixel Bridge.
2. States via the same WebSocket protocol (UE has WebSocket support
   built-in; logic in Blueprint or C++).
3. Lip sync options: amplitude → jaw/mouth morphs (simple), or proper
   phoneme lip sync via plugins (e.g. OVR LipSync port, or NVIDIA
   Audio2Face streaming to the MetaHuman rig for the full uncanny effect).
4. Animations: idle/talk cycles from Mixamo retargeted, or Epic's free
   animation packs.

**The honest catch for this machine:** a MetaHuman at even modest quality
wants 2+ GB of VRAM and real GPU time — directly competing with Whisper on
your 4 GB card, plus UE's ~1.5 GB+ RAM runtime. A stylized low-poly
character in UE avoids that, but then Unity/Godot do the same job lighter.
**Unreal is the route if avatar fidelity becomes the point of the project**
(and ideally after a GPU upgrade); it's overkill as a desk companion widget.

---

## 3. Godot (honorable mention, from the design doc)

Open-source, tiny runtime (~50 MB), imports VRM via the `godot-vrm` addon,
WebSocket built-in. Same architecture as the Unity route with less installed
weight — the trade is a smaller ecosystem for lip-sync/animation tooling.
If you like lean tools, Godot 4 + VRM is a very reasonable pick.

---

## 4. Which one?

| | Live2D | **Unity + VRM** | Godot + VRM | Unreal + MetaHuman |
|---|---|---|---|---|
| Look | 2D anime | 3D anime/stylized | 3D anime/stylized | Photoreal |
| Char creation w/o art skills | ✖ (need art) | **VRoid, hours** | VRoid, hours | MetaHuman, hours |
| GPU cost on the 1650 | Minimal | Low | Low | Heavy |
| Runtime size | tiny (in-process) | ~150 MB exe | ~50 MB exe | GBs |
| Lip sync | our amplitude → param | amplitude or uLipSync | amplitude | plugins/Audio2Face |
| Engine learning curve | Cubism rigging | moderate | moderate | steepest |
| Fits current hardware | ✔✔ | ✔ | ✔ | ✖ |

**Recommendation:** if you want 3D, go **Unity + VRoid (VRM)** — you can
create the character yourself in an afternoon, the runtime is light enough
to coexist with Whisper/XTTS, and the WebSocket bridge keeps Cortana's side
engine-agnostic. Keep Unreal/MetaHuman as the dream tier for after a GPU
upgrade. Live2D remains the lightest and most "desk companion"-flavored if
2D appeals.

### Suggested order of attack

1. I build `ui/avatar_bridge.py` (WebSocket state/amplitude broadcaster) —
   engine-agnostic, small.
2. You make a character in VRoid Studio (free download, runs fine on your
   machine).
3. Unity app per §1, connect, iterate on animations.
4. Orb stays as fallback whenever the avatar app isn't running.
