#!/usr/bin/env python3
"""Generate AdeptBT PCB using real KiCad footprints from hardware/libs/AdeptBT.pretty."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "hardware"
LIB = OUT / "libs" / "AdeptBT.pretty"

W, H = 85.6, 53.98
EDGE = 3.5


def uid() -> str:
    return str(uuid.uuid4())


def load_mod(name: str) -> str:
    path = LIB / name
    text = path.read_text()
    # strip outer wrapper we'll re-wrap; keep inner body
    text = text.strip()
    if not text.startswith("(footprint"):
        raise ValueError(f"Bad footprint {name}")
    return text


def place_footprint(
    mod_text: str,
    x: float,
    y: float,
    angle: float,
    ref: str,
    value: str | None = None,
) -> str:
    """Inject at/uuid and set Reference (and optional Value)."""
    # Replace or insert (at ...) after footprint name line
    # Normalize uuids to unique
    mod_text = re.sub(
        r'\(uuid "[^"]+"\)',
        lambda _m: f'(uuid "{uid()}")',
        mod_text,
    )

    # Force position
    if re.search(r"\(at [^\)]+\)", mod_text):
        mod_text = re.sub(
            r"\(at [^\)]+\)",
            f"(at {x:.4f} {y:.4f} {angle:g})",
            mod_text,
            count=1,
        )
    else:
        mod_text = re.sub(
            r'(\(footprint "[^"]+")',
            rf'\1\n\t(at {x:.4f} {y:.4f} {angle:g})',
            mod_text,
            count=1,
        )

    # Reference property
    def set_prop(src: str, prop: str, val: str) -> str:
        pat = rf'\(property "{prop}" "[^"]*"'
        if re.search(pat, src):
            return re.sub(pat, f'(property "{prop}" "{val}"', src, count=1)
        return src

    mod_text = set_prop(mod_text, "Reference", ref)
    if value is not None:
        mod_text = set_prop(mod_text, "Value", value)
    return mod_text


def silk(x: float, y: float, text: str, size: float = 1.0, angle: float = 0) -> str:
    # KiCad 10: omit justify for centered text (center token alone is invalid)
    th = round(size * 0.15, 3)
    return f"""  (gr_text "{text}"
    (at {x} {y} {angle})
    (layer "F.SilkS")
    (uuid "{uid()}")
    (effects (font (size {size} {size}) (thickness {th})))
  )"""


def outline() -> str:
    return f"""  (gr_rect
    (start 0 0)
    (end {W} {H})
    (stroke (width 0.15) (type default))
    (fill none)
    (layer "Edge.Cuts")
    (uuid "{uid()}")
  )"""


def build_pcb() -> str:
    fps = []

    # Mounting holes
    for ref, (x, y) in {
        "H1": (EDGE, EDGE),
        "H2": (W - EDGE, EDGE),
        "H3": (EDGE, H - EDGE),
        "H4": (W - EDGE, H - EDGE),
    }.items():
        fps.append(
            place_footprint(
                load_mod("MountingHole_2.2mm_M2.kicad_mod"), x, y, 0, ref, "M2"
            )
        )

    # Steppers — top long edge (THT MKDS pins along edge; body into board)
    # Footprint origin is typically at pin1; center-ish placement
    fps.append(
        place_footprint(
            load_mod("TerminalBlock_Phoenix_MKDS-1-6-3.81_1x06_P3.81mm_Horizontal.kicad_mod"),
            10.0,
            2.5,
            0,
            "J_STEP1",
            "STEPPER1",
        )
    )
    fps.append(
        place_footprint(
            load_mod("TerminalBlock_Phoenix_MKDS-1-6-3.81_1x06_P3.81mm_Horizontal.kicad_mod"),
            48.0,
            2.5,
            0,
            "J_STEP2",
            "STEPPER2",
        )
    )

    # Power/outs — bottom long edge, rotated 180 so wires exit south
    fps.append(
        place_footprint(
            load_mod("TerminalBlock_Phoenix_MKDS-1-6-3.81_1x06_P3.81mm_Horizontal.kicad_mod"),
            70.0,
            H - 2.5,
            180,
            "J_PWR",
            "PWR_OUT",
        )
    )

    # USB-C left short edge
    fps.append(
        place_footprint(
            load_mod("USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal.kicad_mod"),
            0.0,
            H / 2,
            90,
            "J_USB",
            "USB-C",
        )
    )

    # MCU
    fps.append(
        place_footprint(
            load_mod("Raytac_MDBT50Q.kicad_mod"),
            42.0,
            28.0,
            0,
            "U1",
            "MDBT50Q-1MV2",
        )
    )

    # TMC2209 x2
    fps.append(
        place_footprint(
            load_mod("QFN-28-1EP_5x5mm_P0.5mm_EP3.25x3.25mm_ThermalVias.kicad_mod"),
            20.0,
            22.0,
            0,
            "U2",
            "TMC2209",
        )
    )
    fps.append(
        place_footprint(
            load_mod("QFN-28-1EP_5x5mm_P0.5mm_EP3.25x3.25mm_ThermalVias.kicad_mod"),
            20.0,
            34.0,
            0,
            "U3",
            "TMC2209",
        )
    )

    # BAT
    fps.append(
        place_footprint(
            load_mod("JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal.kicad_mod"),
            68.0,
            28.0,
            0,
            "J_BAT",
            "BAT",
        )
    )

    # Headers
    fps.append(
        place_footprint(
            load_mod("PinHeader_1x07_P2.54mm_Vertical.kicad_mod"),
            80.0,
            18.0,
            0,
            "J_AN",
            "ANALOG",
        )
    )
    fps.append(
        place_footprint(
            load_mod("PinHeader_1x06_P2.54mm_Vertical.kicad_mod"),
            80.0,
            38.0,
            0,
            "J_DG",
            "DIGITAL",
        )
    )
    fps.append(
        place_footprint(
            load_mod("PinHeader_1x05_P2.54mm_Vertical.kicad_mod"),
            55.0,
            42.0,
            90,
            "J_SWD",
            "SWD",
        )
    )

    silks = [
        silk(W / 2, H / 2 - 6, "AdeptBT", 2.4),
        silk(W / 2, H / 2 - 3.2, "coconnor55", 1.0),
        silk(22, 12, "A1 A2 B1 B2 VM GND", 0.75),
        silk(60, 12, "A1 A2 B1 B2 VM GND", 0.75),
        silk(43, H - 12, "VIN GND V+ OUT1 V+ OUT2", 0.75),
        silk(74, 10, "AIN0-3 3V3 5V GND", 0.7),
        silk(74, 48, "D0-3 3V3 GND", 0.7),
        silk(32, 42, "JP V+: 3V3/5V/VIN", 0.65),
        silk(32, 43.5, "JP VM: VIN/ext", 0.65),
        silk(32, 45, "JP AIN: direct/div5", 0.65),
    ]

    layers = """  (layers
    (0 "F.Cu" signal)
    (1 "In1.Cu" signal)
    (2 "In2.Cu" signal)
    (31 "B.Cu" signal)
    (32 "B.Adhes" user "B.Adhesive")
    (33 "F.Adhes" user "F.Adhesive")
    (34 "B.Paste" user)
    (35 "F.Paste" user)
    (36 "B.SilkS" user "B.Silkscreen")
    (37 "F.SilkS" user "F.Silkscreen")
    (38 "B.Mask" user)
    (39 "F.Mask" user)
    (40 "Dwgs.User" user "User.Drawings")
    (41 "Cmts.User" user "User.Comments")
    (44 "Edge.Cuts" user)
    (45 "F.CrtYd" user "F.Courtyard")
    (46 "B.CrtYd" user "B.Courtyard")
    (47 "F.Fab" user)
    (48 "B.Fab" user)
  )"""

    body = "\n".join([outline(), *silks, *fps])
    return f"""(kicad_pcb
  (version 20241229)
  (generator "gen_adeptbt_pcb")
  (generator_version "10.0")
  (general
    (thickness 1.6)
    (legacy_teardrops no)
  )
  (paper "A4")
  (title_block
    (title "AdeptBT")
    (date "2026-11-22")
    (rev "0.2")
    (company "coconnor55")
    (comment 1 "Real footprints: Raytac MDBT50Q, TMC2209 QFN28, MKDS-1-6, USB-C, JST-PH")
    (comment 2 "Complete schematic nets + routing before fab")
  )
{layers}
  (setup
    (pad_to_mask_clearance 0.05)
    (allow_soldermask_bridges_in_footprints no)
  )
  (net 0 "")
{body}
)
"""


def build_silk_svg() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="856" height="540" viewBox="0 0 85.6 53.98">
  <rect width="85.6" height="53.98" fill="#1a1a1a" stroke="#c0c0c0" stroke-width="0.2"/>
  <text x="42.8" y="26" text-anchor="middle" fill="#f0e6d0" font-family="Helvetica" font-size="3">AdeptBT</text>
  <text x="42.8" y="29" text-anchor="middle" fill="#aaa" font-family="Helvetica" font-size="1.2">rev 0.2 · coconnor55</text>
  <rect x="8" y="0.4" width="28" height="9" fill="none" stroke="#f0e6d0" stroke-width="0.15"/>
  <text x="22" y="4" text-anchor="middle" fill="#f0e6d0" font-size="1.3">STEPPER1</text>
  <text x="22" y="7" text-anchor="middle" fill="#ccc" font-size="0.85">A1 A2 B1 B2 VM GND</text>
  <rect x="46" y="0.4" width="28" height="9" fill="none" stroke="#f0e6d0" stroke-width="0.15"/>
  <text x="60" y="4" text-anchor="middle" fill="#f0e6d0" font-size="1.3">STEPPER2</text>
  <text x="60" y="7" text-anchor="middle" fill="#ccc" font-size="0.85">A1 A2 B1 B2 VM GND</text>
  <rect x="28" y="44.5" width="30" height="9" fill="none" stroke="#f0e6d0" stroke-width="0.15"/>
  <text x="43" y="49.5" text-anchor="middle" fill="#f0e6d0" font-size="1.0">VIN GND V+ OUT1 V+ OUT2</text>
  <rect x="0.2" y="20" width="5" height="14" fill="none" stroke="#7ec8e3" stroke-width="0.15"/>
  <text x="74" y="16" fill="#c8e67e" font-size="1.1">ANALOG</text>
  <text x="74" y="42" fill="#c8e67e" font-size="1.1">DIGITAL</text>
  <circle cx="3.5" cy="3.5" r="1.1" fill="none" stroke="#888" stroke-width="0.15"/>
  <circle cx="82.1" cy="3.5" r="1.1" fill="none" stroke="#888" stroke-width="0.15"/>
  <circle cx="3.5" cy="50.48" r="1.1" fill="none" stroke="#888" stroke-width="0.15"/>
  <circle cx="82.1" cy="50.48" r="1.1" fill="none" stroke="#888" stroke-width="0.15"/>
</svg>
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "gerbers").mkdir(exist_ok=True)
    pcb = build_pcb()
    (OUT / "adeptbt.kicad_pcb").write_text(pcb)
    (OUT / "silkscreen_preview.svg").write_text(build_silk_svg())
    # bump schematic rev note
    sch = (OUT / "adeptbt.kicad_sch").read_text()
    sch = sch.replace('(rev "0.1")', '(rev "0.2")')
    (OUT / "adeptbt.kicad_sch").write_text(sch)
    print(f"Wrote {OUT / 'adeptbt.kicad_pcb'} with {len(list(LIB.glob('*.kicad_mod')))} lib footprints available")


if __name__ == "__main__":
    main()
