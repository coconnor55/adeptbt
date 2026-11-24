#!/usr/bin/env python3
"""Generate AdeptBT PCB using real KiCad footprints from hardware/libs/AdeptBT.pretty."""

from __future__ import annotations

import math
import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "hardware"
LIB = OUT / "libs" / "AdeptBT.pretty"

W, H = 85.6, 53.98
EDGE = 3.5

# TE 238394x-6 pad centers (local), 3.81 mm pitch
TE_PADS = [(-9.525, 0.0), (-5.715, 0.0), (-1.905, 0.0), (1.905, 0.0), (5.715, 0.0), (9.525, 0.0)]
HDR_PITCH = 2.54


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
    ref_at: tuple[float, float, float] | None = None,
    hide_ref: bool = False,
    ref_size: float | None = None,
) -> str:
    """Inject at/uuid and set Reference (and optional Value).

    ref_at: optional footprint-local (x, y, rot) for the Reference silk.
    hide_ref: hide Reference on F.SilkS (pads/courtyard stay).
    ref_size: optional Reference font size (mm) on F.SilkS.
    """
    # Replace or insert (at ...) after footprint name line
    # Normalize uuids to unique
    mod_text = re.sub(
        r'\(uuid "[^"]+"\)',
        lambda _m: f'(uuid "{uid()}")',
        mod_text,
    )

    # Footprint-level (at) only — do not overwrite property (at ...)
    at_line = f"(at {x:.4f} {y:.4f} {angle:g})"
    if re.search(r"\n\t\(at [-\d.]+ [-\d.]+", mod_text):
        mod_text = re.sub(
            r"\n\t\(at [^\)]+\)",
            f"\n\t{at_line}",
            mod_text,
            count=1,
        )
    else:
        mod_text = re.sub(
            r'(\(layer "[^"]+"\))',
            rf"\1\n\t{at_line}",
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
    if ref_at is not None:
        rx, ry, rrot = ref_at
        mod_text = re.sub(
            r'(\(property "Reference" "[^"]*"\s*\n\s*)\(at [^\)]+\)',
            rf"\1(at {rx:g} {ry:g} {rrot:g})",
            mod_text,
            count=1,
        )
    if hide_ref and "(hide yes)" not in mod_text[
        mod_text.find('(property "Reference"') : mod_text.find('(property "Reference"') + 280
    ]:
        mod_text = re.sub(
            r'(\(property "Reference" "[^"]*"[\s\S]*?\(layer "F\.SilkS"\))',
            r'\1\n\t\t(hide yes)',
            mod_text,
            count=1,
        )
    if ref_size is not None:
        th = round(ref_size * 0.15, 3)

        def _ref_font(m: re.Match[str]) -> str:
            block = m.group(0)
            block = re.sub(
                r'\(size [-\d.]+ [-\d.]+\)',
                f"(size {ref_size:g} {ref_size:g})",
                block,
                count=1,
            )
            if "(thickness" in block:
                block = re.sub(
                    r'\(thickness [-\d.]+\)',
                    f"(thickness {th})",
                    block,
                    count=1,
                )
            else:
                block = re.sub(
                    r'(\(size [-\d.]+ [-\d.]+\))',
                    rf"\1\n\t\t\t\t(thickness {th})",
                    block,
                    count=1,
                )
            return block

        mod_text = re.sub(
            r'\(property "Reference" "[^"]*"[\s\S]*?\n\t\)',
            _ref_font,
            mod_text,
            count=1,
        )
    return mod_text


def board_xy(fx: float, fy: float, angle: float, lx: float, ly: float) -> tuple[float, float]:
    """Footprint-local (lx, ly) → board mm (KiCad CCW)."""
    a = math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)
    return fx + lx * ca - ly * sa, fy + lx * sa + ly * ca


def silk(x: float, y: float, text: str, size: float = 1.0, angle: float = 0) -> str:
    # KiCad 10: omit justify for centered text (center token alone is invalid)
    th = round(size * 0.15, 3)
    return f"""  (gr_text "{text}"
    (at {x:.3f} {y:.3f} {angle:g})
    (layer "F.SilkS")
    (uuid "{uid()}")
    (effects (font (size {size} {size}) (thickness {th})))
  )"""


# Must match tools/check_silk.py HOLE_KEEP_HALF (6×6 mm square keepout).
HOLE_KEEP_HALF = 3.0


def silk_keepout_square(cx: float, cy: float, half: float = HOLE_KEEP_HALF) -> str:
    """Square F.SilkS keepout around a mounting hole (screw head clearance)."""
    return f"""  (gr_rect
    (start {cx - half:.3f} {cy - half:.3f})
    (end {cx + half:.3f} {cy + half:.3f})
    (stroke (width 0.12) (type dash))
    (fill none)
    (layer "F.SilkS")
    (uuid "{uid()}")
  )"""


def silk_at_pads(
    fx: float,
    fy: float,
    angle: float,
    pads: list[tuple[float, float]],
    labels: list[str],
    ox: float,
    oy: float,
    size: float = 0.55,
    text_angle: float | None = None,
) -> list[str]:
    """One silk label per pad; (ox, oy) is offset in footprint-local mm from pad center."""
    if len(pads) != len(labels):
        raise ValueError("pads/labels length mismatch")
    ta = angle if text_angle is None else text_angle
    out: list[str] = []
    for (lx, ly), lab in zip(pads, labels):
        tx, ty = board_xy(fx, fy, angle, lx + ox, ly + oy)
        out.append(silk(tx, ty, lab, size, ta))
    return out


def hdr_pads(n: int) -> list[tuple[float, float]]:
    return [(0.0, i * HDR_PITCH) for i in range(n)]


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

    # Mounting holes — no M1–M4 ref silk; square keepout on F.SilkS
    hole_xy = {
        "M1": (EDGE, EDGE),
        "M2": (W - EDGE, EDGE),
        "M3": (EDGE, H - EDGE),
        "M4": (W - EDGE, H - EDGE),
    }
    hole_keepouts: list[str] = []
    for ref, (x, y) in hole_xy.items():
        fps.append(
            place_footprint(
                load_mod("MountingHole_2.2mm_M2.kicad_mod"),
                x,
                y,
                0,
                ref,
                "M2",
                hide_ref=True,
            )
        )
        hole_keepouts.append(silk_keepout_square(x, y))

    # Floorplan (hand sketch): power UL | MCU LL + ant S | steppers R.
    # Pin labels: 1.25 mm (1.5 mm did not clear TE / header pitch on this board).
    PIN_FONT = 1.25
    REF_FONT = 1.5
    OUT_CLEAR = 1.5
    PIN_REF_GAP = 1.0

    def pin_past_outline(outline: float, toward: float = 1.0) -> float:
        return toward * (outline + OUT_CLEAR + PIN_FONT / 2)

    def ref_past_pins(pin_center: float, toward: float = 1.0) -> float:
        return pin_center + toward * (PIN_FONT / 2 + PIN_REF_GAP + REF_FONT / 2)

    def ref_past_outline(outline: float, toward: float = 1.0) -> float:
        return toward * (outline + OUT_CLEAR + REF_FONT / 2)

    term = "TE_2383945-6_1x06_P3.81mm_SMD.kicad_mod"  # geometry = TE 2383941-6
    te_outline = 4.5
    te_pin_oy = pin_past_outline(te_outline)
    te_ref_y = ref_past_pins(te_pin_oy)

    # --- Placement synced from hardware/snapshots/pcbnew-2026-11-23.kicad_pcb ---
    pwr_xy = (35.0, 5.2)
    fps.append(
        place_footprint(
            load_mod(term),
            pwr_xy[0],
            pwr_xy[1],
            0,
            "J_PWR",
            "TE_2383941-6",
            hide_ref=True,
            ref_size=REF_FONT,
        )
    )
    step1_xy = (66.0, 5.2)
    fps.append(
        place_footprint(
            load_mod(term),
            step1_xy[0],
            step1_xy[1],
            0,
            "J_STEP1",
            "TE_2383941-6",
            hide_ref=True,
            ref_size=REF_FONT,
        )
    )
    step2_xy = (66.0, 48.78)
    fps.append(
        place_footprint(
            load_mod(term),
            step2_xy[0],
            step2_xy[1],
            180,
            "J_STEP2",
            "TE_2383941-6",
            hide_ref=True,
            ref_size=REF_FONT,
        )
    )

    # Top edge east of barrel (pcbnew) — plug opens south
    bat_xy = (17.0, 5.0)
    bat_ang = 0
    fps.append(
        place_footprint(
            load_mod("JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal.kicad_mod"),
            bat_xy[0],
            bat_xy[1],
            bat_ang,
            "J_BAT",
            "BAT",
            hide_ref=True,
            ref_size=REF_FONT,
        )
    )

    # J_DC — ang -90: opening west (pcbnew)
    dc_xy = (10.0, 14.0)
    dc_ang = -90
    fps.append(
        place_footprint(
            load_mod("BarrelJack_CUI_PJ-063AH_Horizontal.kicad_mod"),
            dc_xy[0],
            dc_xy[1],
            dc_ang,
            "J_DC",
            "5.5x2.1",
            hide_ref=True,
            ref_size=REF_FONT,
        )
    )

    # J_USB — left edge; ang -90 (pcbnew). Inset from 3.5 so pads/F.Fab stay on-board.
    usb_xy = (5.0, 28.0)
    usb_ang = -90
    fps.append(
        place_footprint(
            load_mod("USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal.kicad_mod"),
            usb_xy[0],
            usb_xy[1],
            usb_ang,
            "J_USB",
            "USB-C",
            hide_ref=True,
            ref_size=REF_FONT,
        )
    )

    jlc = OUT / "libs" / "jlc" / "jlc.pretty"
    mcu_mod = (
        (jlc / "COMM-SMD_MDBT50Q-1MV2-1.kicad_mod")
        if (jlc / "COMM-SMD_MDBT50Q-1MV2-1.kicad_mod").exists()
        else (LIB / "Raytac_MDBT50Q.kicad_mod")
    )
    tmc_mod = (
        (jlc / "QFN-28_L5.0-W5.0-P0.50-BL-EP.kicad_mod")
        if (jlc / "QFN-28_L5.0-W5.0-P0.50-BL-EP.kicad_mod").exists()
        else (LIB / "QFN-28-1EP_5x5mm_P0.5mm_EP3.25x3.25mm_ThermalVias.kicad_mod")
    )

    def load_path(p: Path) -> str:
        text = p.read_text().strip()
        text = re.sub(r'\(uuid "[^"]+"\)', lambda _m: f'(uuid "{uid()}")', text)
        return text

    u1_xy = (13.75, 44.45)
    u1_ang = 180
    fps.append(
        place_footprint(
            load_path(mcu_mod),
            u1_xy[0],
            u1_xy[1],
            u1_ang,
            "U1",
            "MDBT50Q-1MV2",
            hide_ref=True,
            ref_size=REF_FONT,
        )
    )

    u2_xy = (68.5, 20.0)
    u3_xy = (69.0, 34.0)
    fps.append(
        place_footprint(
            load_path(tmc_mod),
            u2_xy[0],
            u2_xy[1],
            0,
            "U2",
            "TMC2209-LA",
            hide_ref=True,
            ref_size=REF_FONT,
        )
    )
    fps.append(
        place_footprint(
            load_path(tmc_mod),
            u3_xy[0],
            u3_xy[1],
            0,
            "U3",
            "TMC2209-LA",
            hide_ref=True,
            ref_size=REF_FONT,
        )
    )

    hdr_silk = 1.38
    step_labs = ["A1", "A2", "B1", "B2", "VM", "GND"]
    pwr_labs = ["VIN", "GND", "V+", "OUT1", "V+", "OUT2"]
    an_labs = ["AIN0", "AIN1", "AIN2", "AIN3", "3V3", "5V", "GND"]
    dg_labs = ["D0", "D1", "D2", "D3", "3V3", "GND"]
    swd_labs = ["SWDIO", "SWCLK", "GND", "3V3", "RST"]
    jp_vp_labs = ["3V3", "V+", "VIN"]
    jp_vm_labs = ["VIN", "EXT"]

    def pin_ox_left(labels: list[str]) -> float:
        half = max(len(s) for s in labels) * PIN_FONT * 0.65 / 2
        return -(hdr_silk + OUT_CLEAR + half)

    def pin_ox_right(labels: list[str]) -> float:
        half = max(len(s) for s in labels) * PIN_FONT * 0.65 / 2
        return hdr_silk + OUT_CLEAR + half

    swd_xy = (22.5, 40.0)
    an_xy = (47.0, 16.0)
    dg_xy = (47.0, 38.0)
    an_pin_ox = pin_ox_right(an_labs)
    dg_pin_ox = pin_ox_right(dg_labs)
    swd_pin_ox = pin_ox_right(swd_labs)
    fps.append(
        place_footprint(
            load_mod("PinHeader_1x05_P2.54mm_Vertical.kicad_mod"),
            swd_xy[0],
            swd_xy[1],
            0,
            "J_SWD",
            "SWD",
            hide_ref=True,
            ref_size=REF_FONT,
        )
    )
    fps.append(
        place_footprint(
            load_mod("PinHeader_1x06_P2.54mm_Vertical.kicad_mod"),
            dg_xy[0],
            dg_xy[1],
            0,
            "J_DG",
            "DIGITAL",
            hide_ref=True,
            ref_size=REF_FONT,
        )
    )
    fps.append(
        place_footprint(
            load_mod("PinHeader_1x07_P2.54mm_Vertical.kicad_mod"),
            an_xy[0],
            an_xy[1],
            0,
            "J_AN",
            "ANALOG",
            hide_ref=True,
            ref_size=REF_FONT,
        )
    )

    jp_vp_xy = (38.5, 15.96)
    jp_vm1_xy = (35.099, 49.46)
    jp_vm2_xy = (39.5, 49.5)
    jp_pin_ox = pin_ox_left(jp_vp_labs)
    jp_vm1_pin_ox = pin_ox_left(jp_vm_labs)
    jp_vm2_pin_ox = pin_ox_right(jp_vm_labs)
    fps.append(
        place_footprint(
            load_mod("PinHeader_1x03_P2.54mm_Vertical.kicad_mod"),
            jp_vp_xy[0],
            jp_vp_xy[1],
            0,
            "JP_V+",
            "V+",
            hide_ref=True,
            ref_size=REF_FONT,
        )
    )
    fps.append(
        place_footprint(
            load_mod("PinHeader_1x02_P2.54mm_Vertical.kicad_mod"),
            jp_vm1_xy[0],
            jp_vm1_xy[1],
            0,
            "JP_VM1",
            "VM1",
            hide_ref=True,
            ref_size=REF_FONT,
        )
    )
    fps.append(
        place_footprint(
            load_mod("PinHeader_1x02_P2.54mm_Vertical.kicad_mod"),
            jp_vm2_xy[0],
            jp_vm2_xy[1],
            0,
            "JP_VM2",
            "VM2",
            hide_ref=True,
            ref_size=REF_FONT,
        )
    )

    def place_cap(
        mod: str,
        x: float,
        y: float,
        ref: str,
        value: str,
        angle: float = 0,
    ) -> None:
        fps.append(
            place_footprint(
                load_mod(mod),
                x,
                y,
                angle,
                ref,
                value,
                hide_ref=True,
            )
        )

    def place_part(
        mod: str,
        x: float,
        y: float,
        ref: str,
        value: str,
        angle: float = 0,
    ) -> None:
        fps.append(
            place_footprint(
                load_mod(mod),
                x,
                y,
                angle,
                ref,
                value,
                hide_ref=True,
            )
        )

    # Power / buck / charger (pcbnew snapshot)
    place_part("Fuse_1812_4532Metric.kicad_mod", 27.0, 16.0, "F1", "PPTC_2A")
    place_part("SOT-23.kicad_mod", 20.0, 24.0, "Q1", "AO3407", 90)
    place_part("D_SMB.kicad_mod", 27.0, 21.0, "D1", "SMBJ24A")
    place_cap("C_0402_1005Metric.kicad_mod", 20.0, 33.0, "C30", "100n")
    place_cap("CP_Elec_6.3x5.3.kicad_mod", 17.5, 17.5, "C31", "100u")

    place_part("TSOT-23-6.kicad_mod", 41.5, 27.5, "U4", "AP63205")
    place_part("L_6.3x6.3_H3.kicad_mod", 27.0, 28.0, "L1", "4.7uH")
    place_cap("C_0805_2012Metric.kicad_mod", 20.0, 28.0, "C40", "10u")
    place_cap("C_0402_1005Metric.kicad_mod", 15.48, 35.0, "C40B", "100n")
    place_cap("C_0402_1005Metric.kicad_mod", 20.0, 35.0, "C42", "100n")
    place_cap("C_0805_2012Metric.kicad_mod", 15.45, 28.0, "C41", "22u")
    place_cap("C_0805_2012Metric.kicad_mod", 15.45, 30.5, "C41B", "22u")

    place_part(
        "QFN-20-1EP_4x4mm_P0.5mm_EP2.5x2.5mm.kicad_mod",
        35.375,
        27.125,
        "U5",
        "MCP73871",
    )
    place_cap("C_0805_2012Metric.kicad_mod", 29.45, 34.0, "C60", "4.7u")
    place_cap("C_0805_2012Metric.kicad_mod", 25.0, 34.0, "C61", "4.7u")
    place_part("R_0603_1608Metric.kicad_mod", 15.5, 25.0, "RPROG1", "2k")
    place_part("SOT-223-3_TabPin2.kicad_mod", 38.0, 35.0, "U6", "AMS1117-3.3", 0)
    place_cap("C_0805_2012Metric.kicad_mod", 37.95, 44.0, "C50", "10u")
    place_cap("C_0805_2012Metric.kicad_mod", 37.95, 41.0, "C51", "22u")

    # MCU / USB decoupling
    place_cap("C_0402_1005Metric.kicad_mod", 15.5, 33.0, "C1", "100n")
    place_cap("C_0603_1608Metric.kicad_mod", 20.0, 30.5, "C2", "1u")
    place_cap("C_0402_1005Metric.kicad_mod", 10.0, 28.0, "C3", "100n")
    place_cap("C_0805_2012Metric.kicad_mod", 10.0, 32.0, "C4", "10u")

    # LEDs + series 1k — west of U1, south of J_USB (added; not in pcbnew snapshot)
    place_part("LED_0603_1608Metric.kicad_mod", 4.8, 34.5, "LED1", "PWR", 90)
    place_part("LED_0603_1608Metric.kicad_mod", 4.8, 37.2, "LED2", "CHG", 90)
    place_part("LED_0603_1608Metric.kicad_mod", 4.8, 39.9, "LED3", "USER", 90)
    place_part("R_0603_1608Metric.kicad_mod", 6.7, 34.5, "R4", "1k", 90)
    place_part("R_0603_1608Metric.kicad_mod", 6.7, 37.2, "R5", "1k", 90)
    place_part("R_0603_1608Metric.kicad_mod", 6.7, 39.9, "R6", "1k", 90)

    # OUT1/OUT2 drivers — one row south of C15 / north of STEP2 pin silk (added; not in pcbnew snapshot)
    place_part("R_0603_1608Metric.kicad_mod", 56.0, 39.4, "R2", "1k")
    place_part("SOT-23.kicad_mod", 59.5, 39.4, "Q2", "MMBT2222A", 90)
    place_part("D_SOD-123.kicad_mod", 63.5, 39.4, "D2", "1N4148W", 0)
    place_part("R_0603_1608Metric.kicad_mod", 67.5, 39.4, "R3", "1k")
    place_part("SOT-23.kicad_mod", 71.5, 39.4, "Q3", "MMBT2222A", 90)
    place_part("D_SOD-123.kicad_mod", 79.5, 39.4, "D3", "1N4148W", 0)

    # Stepper passives (pcbnew)
    place_part("R_1206_3216Metric.kicad_mod", 58.0, 27.5, "RSA1", "0.11", 90)
    place_part("R_1206_3216Metric.kicad_mod", 61.5, 27.5, "RSB1", "0.11", 90)
    place_part("R_1206_3216Metric.kicad_mod", 61.5, 34.462, "RSA2", "0.11", 90)
    place_part("R_1206_3216Metric.kicad_mod", 58.0, 34.5, "RSB2", "0.11", 90)

    place_cap("C_0603_1608Metric.kicad_mod", 76.0, 14.0, "C10", "22n")
    place_cap("C_0402_1005Metric.kicad_mod", 76.0, 17.0, "C11", "100n")
    place_cap("C_0805_2012Metric.kicad_mod", 76.0, 20.5, "C12", "4.7u")
    place_cap("C_0402_1005Metric.kicad_mod", 76.0, 23.5, "C13", "100n")
    place_cap("C_0402_1005Metric.kicad_mod", 76.0, 26.0, "C14", "100n")
    place_cap("CP_Elec_6.3x5.3.kicad_mod", 79.5, 34.0, "C15", "100u")

    place_cap("C_0603_1608Metric.kicad_mod", 81.0, 14.0, "C20", "22n")
    place_cap("C_0402_1005Metric.kicad_mod", 81.0, 17.0, "C21", "100n")
    place_cap("C_0805_2012Metric.kicad_mod", 81.0, 20.5, "C22", "4.7u")
    place_cap("C_0402_1005Metric.kicad_mod", 81.0, 24.0, "C23", "100n")
    place_cap("C_0402_1005Metric.kicad_mod", 81.0, 27.0, "C24", "100n")
    place_cap("CP_Elec_6.3x5.3.kicad_mod", 59.0, 18.5, "C25", "100u")

    silks = [
        silk(64.0, 24.0, "AdeptBT v1", 1.2),
        # Rev mark — two lines above H4 (lower-right hole)
        silk(81.5, 44.0, "rev", 1.0),
        silk(81.5, 45.5, "2.12", 1.0),
        *silk_at_pads(
            pwr_xy[0], pwr_xy[1], 0, TE_PADS, pwr_labs, 0.0, te_pin_oy, PIN_FONT, text_angle=0
        ),
        *silk_at_pads(
            step1_xy[0], step1_xy[1], 0, TE_PADS, step_labs, 0.0, te_pin_oy, PIN_FONT, text_angle=0
        ),
        # STEP2 @180: oy 5.5 — south of OUT, north of TE silk outline
        *silk_at_pads(
            step2_xy[0],
            step2_xy[1],
            180,
            TE_PADS,
            step_labs,
            0.0,
            5.5,
            PIN_FONT,
            text_angle=0,
        ),
        *silk_at_pads(
            an_xy[0], an_xy[1], 0, hdr_pads(7), an_labs, an_pin_ox, 0.0, PIN_FONT, text_angle=0
        ),
        *silk_at_pads(
            dg_xy[0], dg_xy[1], 0, hdr_pads(6), dg_labs, dg_pin_ox, 0.0, PIN_FONT, text_angle=0
        ),
        *silk_at_pads(
            swd_xy[0], swd_xy[1], 0, hdr_pads(5), swd_labs, swd_pin_ox, 0.0, PIN_FONT, text_angle=0
        ),
        *silk_at_pads(
            jp_vp_xy[0], jp_vp_xy[1], 0, hdr_pads(3), jp_vp_labs, jp_pin_ox, 0.0, PIN_FONT, text_angle=0
        ),
        *silk_at_pads(
            jp_vm1_xy[0],
            jp_vm1_xy[1],
            0,
            hdr_pads(2),
            jp_vm_labs,
            jp_vm1_pin_ox,
            0.0,
            1.0,
            text_angle=0,
        ),
        *silk_at_pads(
            jp_vm2_xy[0],
            jp_vm2_xy[1],
            0,
            hdr_pads(2),
            jp_vm_labs,
            jp_vm2_pin_ox,
            0.0,
            1.0,
            text_angle=0,
        ),
        # +/- east of J_BAT (south hits J_DC in this pcbnew pack)
        silk(22.5, 4.5, "+", PIN_FONT),
        silk(22.5, 6.5, "−", PIN_FONT),
        silk(usb_xy[0] + 3.0, usb_xy[1] - 6.5, "J_USB", REF_FONT),
        # J_DC: no gr_text — footprint silk/fab already mark the jack; label always self-hit
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

    body = "\n".join([outline(), *hole_keepouts, *silks, *fps])
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
    (date "2026-11-23")
    (rev "2.12")
    (company "coconnor55")
    (comment 1 "6×6 hole keepouts; 1 mm outline keep-away; STEP/U1 clear of screws")
    (comment 2 "J_USB -90; LEDs+OUT drivers; pcbnew sync; check_silk; STACKUP.md")
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
    """Rough board preview — not a fab plot."""
    step = ["A1", "A2", "B1", "B2", "VM", "GND"]
    pwr = ["VIN", "GND", "V+", "OUT1", "V+", "OUT2"]
    an = ["AIN0", "AIN1", "AIN2", "AIN3", "3V3", "5V", "GND"]
    dg = ["D0", "D1", "D2", "D3", "3V3", "GND"]
    parts = [
        f'<text x="42.8" y="26" text-anchor="middle" fill="#f0e6d0" font-family="Helvetica" font-size="3">AdeptBT</text>',
        f'<text x="42.8" y="29" text-anchor="middle" fill="#aaa" font-family="Helvetica" font-size="1.2">rev 0.5 · coconnor55</text>',
    ]
    for i, lab in enumerate(step):
        x = 22 + TE_PADS[i][0]
        parts.append(f'<text x="{x}" y="7.2" text-anchor="middle" fill="#ccc" font-size="0.7">{lab}</text>')
        x2 = 58 + TE_PADS[i][0]
        parts.append(f'<text x="{x2}" y="7.2" text-anchor="middle" fill="#ccc" font-size="0.7">{lab}</text>')
    for i, lab in enumerate(pwr):
        # rot 180: board x = 48 - lx
        x = 48 - TE_PADS[i][0]
        parts.append(f'<text x="{x}" y="46.5" text-anchor="middle" fill="#ccc" font-size="0.7">{lab}</text>')
    for i, lab in enumerate(an):
        y = 18 + i * HDR_PITCH
        parts.append(f'<text x="77.5" y="{y + 0.3}" text-anchor="end" fill="#c8e67e" font-size="0.65">{lab}</text>')
    for i, lab in enumerate(dg):
        y = 38 + i * HDR_PITCH
        parts.append(f'<text x="77.5" y="{y + 0.3}" text-anchor="end" fill="#c8e67e" font-size="0.65">{lab}</text>')
    body = "\n  ".join(parts)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="856" height="540" viewBox="0 0 85.6 53.98">
  <rect width="85.6" height="53.98" fill="#1a1a1a" stroke="#c0c0c0" stroke-width="0.2"/>
  {body}
  <circle cx="3.5" cy="3.5" r="1.1" fill="none" stroke="#888" stroke-width="0.15"/>
  <circle cx="82.1" cy="3.5" r="1.1" fill="none" stroke="#888" stroke-width="0.15"/>
  <circle cx="3.5" cy="50.48" r="1.1" fill="none" stroke="#888" stroke-width="0.15"/>
  <circle cx="82.1" cy="50.48" r="1.1" fill="none" stroke="#888" stroke-width="0.15"/>
</svg>
"""


def main() -> None:
    raise SystemExit(
        "STOPPED: hardware/adeptbt.kicad_pcb is owned by pcbnew. "
        "Do not regenerate from this script. Edit and save the board in KiCad."
    )


if __name__ == "__main__":
    main()
