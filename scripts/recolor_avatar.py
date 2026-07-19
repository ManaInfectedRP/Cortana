"""Recolor a VRoid-exported VRM to the Cortana cyan/holographic palette.

VRM materials use the MToon shader (VRMC_materials_mtoon extension):
- pbrMetallicRoughness.baseColorFactor MULTIPLIES the existing texture
  (it tints, it doesn't replace) - so results depend on how light/dark
  the underlying texture already is.
- VRMC_materials_mtoon.shadeColorFactor is the toon shadow-side tint.
- Standard glTF emissiveFactor drives glow, but VRoid points emissiveTexture
  at a solid-black image by default, which zeroes any factor - we detach it
  so emissiveFactor alone applies.

Non-destructive: reads models/avatar/base.vrm, writes models/avatar/cortana.vrm.
Re-run any time you re-export a new base.vrm (e.g. after adding an outfit).

Usage:
    python scripts/recolor_avatar.py
"""

from pathlib import Path

from pygltflib import GLTF2

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "models" / "avatar" / "base.vrm"
DST = ROOT / "models" / "avatar" / "cortana.vrm"

# --- palette (0-1 RGB), see VROID_GUIDE.md §8 ------------------------------

IRIS = (0.0, 0.831, 1.0)          # #00D4FF bright cyan
IRIS_SHADE = (0.0, 0.55, 0.72)
IRIS_EMISSIVE = (0.0, 0.35, 0.45)

HAIR = (0.161, 0.714, 0.965)      # #29B6F6 electric blue-cyan
HAIR_SHADE = (0.08, 0.36, 0.48)
HAIR_EMISSIVE = (0.05, 0.30, 0.40)

SKIN_TINT = (0.92, 0.97, 1.0)     # subtle cool-white, keeps skin readable as skin
BROW_TINT = (0.55, 0.65, 0.78)    # cool blue-grey eyebrows

MTOON = "VRMC_materials_mtoon"


def blend(base: tuple, tint: tuple, amount: float) -> list:
    return [base[i] * (1 - amount) + tint[i] * amount for i in range(3)]


def set_emissive(material, color) -> None:
    """Detach the (usually solid-black) emissive texture so the flat
    emissiveFactor color actually shows, per the module docstring."""
    material.emissiveTexture = None
    material.emissiveFactor = list(color)


def recolor(materials: list) -> int:
    changed = 0
    for m in materials:
        name = m.name or ""
        ext = (m.extensions or {}).get(MTOON)
        pbr = m.pbrMetallicRoughness

        if "EyeIris" in name:
            pbr.baseColorFactor = [*IRIS, 1.0]
            if ext:
                ext["shadeColorFactor"] = list(IRIS_SHADE)
            set_emissive(m, IRIS_EMISSIVE)
            changed += 1

        elif "HAIR" in name:
            pbr.baseColorFactor = [*HAIR, 1.0]
            if ext:
                ext["shadeColorFactor"] = list(HAIR_SHADE)
            set_emissive(m, HAIR_EMISSIVE)
            changed += 1

        elif "FaceBrow" in name:
            pbr.baseColorFactor = [*BROW_TINT, 1.0]
            changed += 1

        elif "_SKIN" in name:
            pbr.baseColorFactor = [*SKIN_TINT, 1.0]
            if ext and "shadeColorFactor" in ext:
                ext["shadeColorFactor"] = blend(
                    tuple(ext["shadeColorFactor"]), SKIN_TINT, 0.3
                )
            changed += 1

        # EyeWhite, EyeHighlight, FaceMouth, FaceEyeline: left as VRoid
        # exported them - recoloring lips/eyeliner/sclera tends to look wrong.

    return changed


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"Not found: {SRC}\nExport your VRoid model there first.")

    gltf = GLTF2.load_binary(str(SRC))
    print(f"Loaded {SRC.name}: {len(gltf.materials)} materials, "
          f"{len(gltf.meshes)} meshes")

    n = recolor(gltf.materials)
    print(f"Recolored {n} materials")

    DST.parent.mkdir(parents=True, exist_ok=True)
    gltf.save_binary(str(DST))
    print(f"Saved {DST}")

    # round-trip sanity check
    check = GLTF2.load_binary(str(DST))
    assert len(check.materials) == len(gltf.materials)
    assert len(check.meshes) == len(gltf.meshes)
    print("Round-trip check passed (material/mesh counts match).")


if __name__ == "__main__":
    main()
