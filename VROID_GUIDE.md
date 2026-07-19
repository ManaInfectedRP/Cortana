# Making a Cortana-Inspired Character in VRoid Studio

A practical walkthrough for building a holographic, Cortana-flavored avatar
in VRoid Studio — for your own personal desktop companion. This is a
fan-inspired *original* character (glowing cyan holographic AI aesthetic),
not a copy of Microsoft/343 Industries' character model or assets — keep it
personal-use.

This feeds into the [AVATAR_3D.md](AVATAR_3D.md) Unity route: VRoid exports
a `.vrm` file that UniVRM drops straight into Unity with working blendshapes
and physics.

---

## 1. Install VRoid Studio

Free, Windows/Mac: <https://vroid.com/en/studio>. Download, install, launch,
**New Project → Custom (Start from a base body)**. Pick the female base;
you'll reshape everything anyway.

The editor has five tabs down the left: **Face, Body, Hair, Outfit,
Material/Preset**. Work roughly in that order.

---

## 2. Face — the part that sells the character

Cortana's design language: youthful, symmetrical, slightly stylized/idealized
features, calm expression, high cheekbones, an intelligent/alert look rather
than soft-and-round.

**Face → Face shape:**
- Slightly narrow jaw, subtle cheekbone definition (`Cheek` sliders)
- Keep proportions clean and symmetrical — nudge every left/right paired
  slider identically

**Face → Eyes** (this matters most for the "AI" read):
- Shape: alert, slightly angular rather than big-anime-round — pull
  `Eye Size` down a touch from default, increase `Eye Angle` slightly for a
  focused look
- **Iris color: bright cyan/electric blue** (`#00D4FF`–`#29B6F6` range) —
  this single choice does more for the "Cortana" read than anything else
- Under **Iris texture presets**, pick a bright, high-contrast ring pattern;
  you'll add the glow separately (§5)
- Eyebrows: thin, high-arched, cool-toned (blue-grey rather than warm brown)

**Face → Mouth/Nose:** keep small and refined; default presets work — this
isn't where the character reads as "her."

---

## 3. Hair — Cortana's signature is data-stream, not strands

Real Cortana renders are wireframe/particle hair, which VRoid can't do
literally — the practical substitute:

- **Hair → Preset**: start from a **sleek, short-to-mid-length bob or
  slicked-back style** (search presets for "short straight" / "slicked")
- **Hair → Color**: cyan/blue-white, NOT black or brown — try a pale
  cyan-white base (`#D6F5FF`) or full electric blue depending on how bold
  you want it
- **Hair → Material**: crank **Specular/Shine** up high — glossy, almost
  wet-look hair reads as "digital" far better than matte
- Optional: use the **Hair particle/strand tool** to add a few
  jagged, asymmetric "data" strands jutting out — small touch, big effect

---

## 4. Outfit — sleek and minimal, not armored

Skip the default cloth-heavy presets. Cortana reads as smooth, form-fitting,
almost seamless:

- **Outfit → Preset**: pick a simple **bodysuit/leotard-style base** (VRoid's
  default sample avatars usually include one, or search the free VRoid Hub
  presets for "bodysuit")
- **Outfit → Material → Color**: dark base (near-black or deep navy) with
  **cyan glowing seam lines** — VRoid's material editor lets you paint an
  emission-colored trim along outfit edges
- **Emission**: this is key — in the Material tab, turn up **Emissive
  Strength** on the trim/seam parts and set the emissive color to the same
  cyan as the eyes/hair, for a consistent glow line down the character
- Skip shoes/gloves detail — smooth, minimal, second-skin is the vibe

---

## 5. Skin — the holographic glow

VRoid doesn't have a true "hologram" shader out of the box, but you can fake
it convincingly:

- **Material/Preset → Skin**: choose a **pale, slightly blue-tinted** skin
  tone rather than a natural one (subtle — don't go full blue, a cool
  undertone is enough)
- Turn up **Skin → Specular** slightly for a smooth, synthetic sheen
- If you want the strong "translucent hologram" effect (like she's made of
  light), that's easier to add **after export**, in Unity: apply a
  Fresnel/rim-light shader (many free ones on the Unity Asset Store search
  "hologram shader") that glows brighter at silhouette edges. VRoid gets you
  the *shape and colors*; Unity's shader gets you the *shimmer*.

---

## 6. Accessories (optional, keeps it recognizable without copying)

- A subtle **circuit-pattern or line-art texture** on the outfit (VRoid lets
  you paint custom textures onto clothing — a simple blue line pattern in
  an image editor, imported as a texture, goes a long way)
- Small glowing accent pieces (wrist bands, a collar line) using the same
  emissive-cyan trick from §4
- Avoid literal Halo insignia/logos if you ever plan to share the model
  publicly — keep it "inspired by," which is exactly what a re-imagined
  holographic AI companion is anyway

---

## 7. Export

**File → Export → VRM 1.0** (or 0.x if your target tooling needs it —
UniVRM in Unity supports both, but 1.0 is current).

- Set the model's permission fields (VRM embeds a usage-permission block) —
  for personal desktop use only, the defaults are fine
- Save as `models/avatar/cortana.vrm` in this repo — that's where the Unity
  route in [AVATAR_3D.md](AVATAR_3D.md) expects to find it

---

## 8. Quick pass checklist

| Element | Cortana-flavored choice |
|---|---|
| Iris color | Bright cyan/electric blue |
| Hair color | Cyan/blue-white, glossy |
| Hair style | Sleek, short-mid, slicked or asymmetric strands |
| Skin tone | Pale, cool/blue undertone |
| Outfit | Dark, minimal, form-fitting |
| Outfit trim | Emissive cyan seam lines |
| Overall feel | Symmetrical, alert expression, smooth/synthetic materials |
| Post-export polish | Fresnel/rim-light hologram shader in Unity |

---

## 9. Where this goes next

Once you have `cortana.vrm`:

1. Follow [AVATAR_3D.md](AVATAR_3D.md) §1 (Unity route) — import via
   UniVRM, wire up the four Cortana states (idle/listening/thinking/speaking)
   to animations, and connect the WebSocket bridge.
2. Tell me when the `.vrm` exists and I'll build
   `ui/avatar_bridge.py` (the Python-side WebSocket broadcaster) so the
   Unity app has something to connect to.

VRoid itself is quick to iterate in — expect an hour or two to get a look you
like, most of it spent nudging sliders and previewing from different angles
(there's a live 3D preview pane the whole time you're editing).
