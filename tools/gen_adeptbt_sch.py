#!/usr/bin/env python3
"""gen_adeptbt_sch.py — Generate AdeptBT schematic rev 0.14 (traditional wired).

Reads lib_symbols from the pre-redraw snapshot and connectivity from the
exported JSON.  Places components in functional blocks with wires for local
connections and global labels for inter-block / power nets.
"""

from __future__ import annotations

import json
import math
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HW = ROOT / "hardware"
OUT = HW / "adeptbt.kicad_sch"
SNAP = HW / "snapshots" / "pre-sch-redraw-20261125.kicad_sch"
CONN = HW / "exports" / "sch_connectivity.json"

PROJECT = "adeptbt"
SHEET_UUID = "46fc2e97-3959-4095-a2dc-23d7ed974c68"

# ── helpers ─────────────────────────────────────────────────────


def uid() -> str:
    return str(uuid.uuid4())


def extract_lib_symbols(sch_text: str) -> str:
    """Return the ``(lib_symbols ...)`` block verbatim."""
    tag = "\t(lib_symbols"
    start = sch_text.find(tag)
    if start < 0:
        raise ValueError("lib_symbols not found")
    depth = 0
    i = start
    while i < len(sch_text):
        if sch_text[i] == "(":
            depth += 1
        elif sch_text[i] == ")":
            depth -= 1
            if depth == 0:
                return sch_text[start : i + 1]
        i += 1
    raise ValueError("unclosed lib_symbols")


# ── pin-position math ───────────────────────────────────────────


def psp(ix: float, iy: float, angle: float, lx: float, ly: float):
    """Library pin (lx, ly) → schematic coords for symbol at (ix, iy, angle°).

    Rotate in symbol space (Y-up) then project onto schematic (Y-down).
    """
    theta = math.radians(angle)
    ct, st = math.cos(theta), math.sin(theta)
    xp = lx * ct - ly * st
    yp = -(lx * st + ly * ct)
    return (round(ix + xp, 2), round(iy + yp, 2))


# ── s-expression emitters ──────────────────────────────────────


def _prop(name, value, x, y, hide=False):
    h = "\n\t\t\t(hide yes)" if hide else ""
    return (
        f'\t\t(property "{name}" "{value}"\n'
        f"\t\t\t(at {x} {y} 0){h}\n"
        f"\t\t\t(effects\n"
        f"\t\t\t\t(font\n"
        f"\t\t\t\t\t(size 1.27 1.27)\n"
        f"\t\t\t\t)\n"
        f"\t\t\t)\n"
        f"\t\t)"
    )


def _pin_uuids(nums):
    return "\n".join(
        f'\t\t(pin "{n}"\n\t\t\t(uuid "{uid()}")\n\t\t)' for n in nums
    )


def _inst(ref):
    return (
        f"\t\t(instances\n"
        f'\t\t\t(project "{PROJECT}"\n'
        f'\t\t\t\t(path "/{SHEET_UUID}"\n'
        f'\t\t\t\t\t(reference "{ref}")\n'
        f"\t\t\t\t\t(unit 1)\n"
        f"\t\t\t\t)\n"
        f"\t\t\t)\n"
        f"\t\t)"
    )


def sym(lib_id, ref, value, fp, x, y, pins, angle=0):
    return (
        f"\t(symbol\n"
        f'\t\t(lib_id "{lib_id}")\n'
        f"\t\t(at {x} {y} {angle:g})\n"
        f"\t\t(unit 1)\n"
        f"\t\t(exclude_from_sim no)\n"
        f"\t\t(in_bom yes)\n"
        f"\t\t(on_board yes)\n"
        f"\t\t(dnp no)\n"
        f'\t\t(uuid "{uid()}")\n'
        f'{_prop("Reference", ref, x, y - 5.08)}\n'
        f'{_prop("Value", value, x, y + 5.08)}\n'
        f'{_prop("Footprint", fp, x, y, True)}\n'
        f'{_prop("Datasheet", "~", x, y, True)}\n'
        f'{_prop("Description", "", x, y, True)}\n'
        f"{_pin_uuids(pins)}\n"
        f"{_inst(ref)}\n"
        f"\t)"
    )


def gl(name, x, y, angle=0, shape="input"):
    return (
        f'\t(global_label "{name}"\n'
        f"\t\t(shape {shape})\n"
        f"\t\t(at {x:g} {y:g} {angle:g})\n"
        f"\t\t(fields_autoplaced yes)\n"
        f"\t\t(effects\n"
        f"\t\t\t(font\n"
        f"\t\t\t\t(size 1.27 1.27)\n"
        f"\t\t\t)\n"
        f"\t\t\t(justify left)\n"
        f"\t\t)\n"
        f'\t\t(uuid "{uid()}")\n'
        f'\t\t(property "Intersheetrefs" "${{INTERSHEET_REFS}}"\n'
        f"\t\t\t(at {x:g} {y:g} 0)\n"
        f"\t\t\t(effects\n"
        f"\t\t\t\t(font\n"
        f"\t\t\t\t\t(size 1.27 1.27)\n"
        f"\t\t\t\t)\n"
        f"\t\t\t\t(hide yes)\n"
        f"\t\t\t)\n"
        f"\t\t)\n"
        f"\t)"
    )


def nc(x, y):
    return (
        f"\t(no_connect\n"
        f"\t\t(at {x:g} {y:g})\n"
        f'\t\t(uuid "{uid()}")\n'
        f"\t)"
    )


def wr(x1, y1, x2, y2):
    return (
        f"\t(wire\n"
        f"\t\t(pts\n"
        f"\t\t\t(xy {x1:g} {y1:g})\n"
        f"\t\t\t(xy {x2:g} {y2:g})\n"
        f"\t\t)\n"
        f"\t\t(stroke\n"
        f"\t\t\t(width 0)\n"
        f"\t\t\t(type default)\n"
        f"\t\t)\n"
        f'\t\t(uuid "{uid()}")\n'
        f"\t)"
    )


def jn(x, y):
    return (
        f"\t(junction\n"
        f"\t\t(at {x:g} {y:g})\n"
        f"\t\t(diameter 0)\n"
        f"\t\t(color 0 0 0 0)\n"
        f'\t\t(uuid "{uid()}")\n'
        f"\t)"
    )


def txt(s, x, y, size=2.5):
    s = s.replace("\\", "\\\\").replace('"', '\\"')
    return (
        f'\t(text "{s}"\n'
        f"\t\t(exclude_from_sim no)\n"
        f"\t\t(at {x} {y} 0)\n"
        f"\t\t(effects\n"
        f"\t\t\t(font\n"
        f"\t\t\t\t(size {size} {size})\n"
        f"\t\t\t\t(bold yes)\n"
        f"\t\t\t)\n"
        f"\t\t\t(justify left top)\n"
        f"\t\t)\n"
        f'\t\t(uuid "{uid()}")\n'
        f"\t)"
    )


# ── pin library offsets (Y-up in symbol editor) ────────────────

V1 = (0, 3.81)    # 2-pin vertical devices: pin 1 (top)
V2 = (0, -3.81)   # pin 2 (bottom)
H1 = (-3.81, 0)   # horizontal D/LED: pin 1 K (left)
H2 = (3.81, 0)    # pin 2 A (right)

CONN_Y0 = {1: 0, 2: 0.0, 3: 2.54, 5: 5.08, 6: 5.08, 7: 7.62}


def cpn(count, pin_1):
    """Library coords for Connector_Generic:Conn_01xNN pin (1-based)."""
    y0 = CONN_Y0[count]
    return (-5.08, y0 - (pin_1 - 1) * 2.54)


def conn_labels(x, y, count, nets, P_list, L_list):
    """Emit labels for a standard generic connector's left-side pins."""
    for i, net in enumerate(nets, 1):
        px, py = psp(x, y, 0, *cpn(count, i))
        L_list.append(gl(net, px, py, 0, "input"))


# ── main ────────────────────────────────────────────────────────


def main() -> None:
    lib_syms = extract_lib_symbols(SNAP.read_text())

    P: list[str] = []  # symbols
    L: list[str] = []  # labels + no-connects
    W: list[str] = []  # wires + junctions
    T: list[str] = []  # section-title text blocks

    # footprint shorthands
    fp0402 = "AdeptBT:C_0402_1005Metric"
    fp0603 = "AdeptBT:C_0603_1608Metric"
    fp0805 = "AdeptBT:C_0805_2012Metric"
    fp_elec = "AdeptBT:CP_Elec_6.3x5.3"
    fp_r06 = "Resistor_SMD:R_0603_1608Metric"
    fp_r12 = "AdeptBT:R_1206_3216Metric"
    fp_led = "LED_SMD:LED_0603_1608Metric"

    def vcap(ref, value, fp, net_a, net_b, x, y, polar=False):
        """Vertical cap: pin1 (top)=net_a, pin2 (bottom)=net_b."""
        lib = "Device:C_Polarized" if polar else "Device:C"
        P.append(sym(lib, ref, value, fp, x, y, ["1", "2"]))
        L.append(gl(net_a, x, y - 3.81, 90, "passive"))
        L.append(gl(net_b, x, y + 3.81, 270, "passive"))

    def vres(ref, value, fp, net_a, net_b, x, y):
        """Vertical resistor: pin1 (top)=net_a, pin2 (bottom)=net_b."""
        P.append(sym("Device:R", ref, value, fp, x, y, ["1", "2"]))
        L.append(gl(net_a, x, y - 3.81, 90, "passive"))
        L.append(gl(net_b, x, y + 3.81, 270, "passive"))

    # ================================================================
    #  POWER PATH
    # ================================================================
    T.append(txt("Power path", 25, 22))
    T.append(
        txt(
            "AdeptBT rev 0.14 — JLCPCB-first schematic\\n"
            "MCU U1 Raytac MDBT50Q-1MV2  |  U2/U3 TMC2209-LA\\n"
            "U4 AP63205  |  U5 MCP73871  |  U6 AMS1117\\n"
            "VIN_RAW\\u2192F1\\u2192Q1\\u2192D1\\u2192VIN\\u2192buck\\u2192+5V\\u2192LDO\\u2192+3V3",
            25,
            10,
            1.4,
        )
    )

    # --- J_DC1 barrel jack ---
    jdc_x, jdc_y = 38, 50
    P.append(
        sym(
            "Connector:Barrel_Jack_MountingPin",
            "J_DC1",
            "5.5x2.1",
            "AdeptBT:BarrelJack_CUI_PJ-063AH_Horizontal",
            jdc_x,
            jdc_y,
            ["1", "2", "MP"],
        )
    )
    jdc_p1 = psp(jdc_x, jdc_y, 0, 7.62, 2.54)   # tip  VIN_RAW
    jdc_p2 = psp(jdc_x, jdc_y, 0, 7.62, -2.54)   # sleeve GND
    jdc_mp = psp(jdc_x, jdc_y, 0, 0, -7.62)       # MP  GND
    L.append(gl("VIN_RAW", *jdc_p1, 180, "output"))
    L.append(gl("GND", *jdc_p2, 180, "output"))
    L.append(gl("GND", *jdc_mp, 270, "input"))

    # --- F1 PPTC fuse (horizontal, angle 90 → pin1 left, pin2 right) ---
    f1_x, f1_y = 68, 50
    P.append(
        sym("Device:Fuse", "F1", "PPTC_2A",
            "AdeptBT:Fuse_1812_4532Metric", f1_x, f1_y, ["1", "2"], 90)
    )
    f1_p1 = psp(f1_x, f1_y, 90, *V1)  # VIN_RAW (left)
    f1_p2 = psp(f1_x, f1_y, 90, *V2)  # VIN_F   (right)
    L.append(gl("VIN_RAW", *f1_p1, 0, "input"))

    # --- Q1 P-FET (angle 0, vertical: D top, S bottom, G left) ---
    # Pin lib offsets: G=1 (-5.08,0), S=2 (2.54,-5.08), D=3 (2.54,5.08)
    q1_x, q1_y = 85, 55
    P.append(
        sym("Device:Q_PMOS", "Q1", "AO3407",
            "AdeptBT:SOT-23", q1_x, q1_y, ["1", "2", "3"])
    )
    L.append(gl("GND", *psp(q1_x, q1_y, 0, -5.08, 0), 0, "input"))        # G
    L.append(gl("VIN_F", *psp(q1_x, q1_y, 0, 2.54, -5.08), 270, "input"))  # S
    L.append(gl("VIN", *psp(q1_x, q1_y, 0, 2.54, 5.08), 90, "output"))     # D

    # F1.pin2 label (VIN_F net, label instead of wire to avoid cross-pin)
    L.append(gl("VIN_F", *f1_p2, 180, "passive"))

    # --- D1 TVS diode (vertical angle 270 → K top=VIN, A bottom=GND) ---
    d1_x, d1_y = 105, 60
    P.append(
        sym("Device:D", "D1", "SMBJ24A",
            "AdeptBT:D_SMB", d1_x, d1_y, ["1", "2"], 270)
    )
    L.append(gl("VIN", *psp(d1_x, d1_y, 270, *H1), 90, "input"))
    L.append(gl("GND", *psp(d1_x, d1_y, 270, *H2), 270, "input"))

    # VIN entry caps
    vcap("C30", "100n", fp0402, "VIN", "GND", 118, 55)
    vcap("C31", "100u/25V", fp_elec, "VIN", "GND", 128, 55, polar=True)

    # --- Jumpers ---
    jpv_x, jpv_y = 148, 50
    P.append(
        sym("Connector_Generic:Conn_01x03", "JP_V+1", "V+",
            "AdeptBT:PinHeader_1x03_P2.54mm_Vertical", jpv_x, jpv_y,
            ["1", "2", "3"])
    )
    conn_labels(jpv_x, jpv_y, 3, ["+3V3", "V+", "VIN"], P, L)

    jpvm1_x, jpvm1_y = 148, 72
    P.append(
        sym("Connector_Generic:Conn_01x02", "JP_VM1", "VM1",
            "AdeptBT:PinHeader_1x02_P2.54mm_Vertical", jpvm1_x, jpvm1_y,
            ["1", "2"])
    )
    conn_labels(jpvm1_x, jpvm1_y, 2, ["VIN", "VM1"], P, L)

    jpvm2_x, jpvm2_y = 148, 88
    P.append(
        sym("Connector_Generic:Conn_01x02", "JP_VM2", "VM2",
            "AdeptBT:PinHeader_1x02_P2.54mm_Vertical", jpvm2_x, jpvm2_y,
            ["1", "2"])
    )
    conn_labels(jpvm2_x, jpvm2_y, 2, ["VIN", "VM2"], P, L)

    # --- J_PWR1 ---
    jpwr_x, jpwr_y = 38, 90
    P.append(
        sym("Connector_Generic:Conn_01x06", "J_PWR1", "TE_2383941-6",
            "AdeptBT:TE_2383945-6_1x06_P3.81mm_SMD", jpwr_x, jpwr_y,
            [str(i) for i in range(1, 7)])
    )
    conn_labels(jpwr_x, jpwr_y, 6,
                ["VIN_RAW", "GND", "V+", "OUT1", "V+", "OUT2"], P, L)

    # ================================================================
    #  BUCK CONVERTER
    # ================================================================
    T.append(txt("Buck converter", 170, 22))

    vcap("C40", "10u", fp0805, "VIN", "GND", 178, 55)
    vcap("C402", "100n", fp0402, "VIN", "GND", 188, 55)

    # --- U4 AP63205WU ---
    u4_x, u4_y = 215, 50
    P.append(
        sym("Regulator_Switching:AP63205WU", "U4", "AP63205WU-7",
            "AdeptBT:TSOT-23-6", u4_x, u4_y,
            ["1", "2", "3", "4", "5", "6"])
    )
    # pin lib offsets: 1=FB(10.16,-2.54) 2=EN(-10.16,-2.54) 3=IN(-10.16,2.54)
    #                  4=GND(0,-7.62)    5=SW(10.16,2.54)   6=BST(10.16,0)
    L.append(gl("+5V", *psp(u4_x, u4_y, 0, 10.16, -2.54), 180, "output"))   # FB
    L.append(gl("VIN", *psp(u4_x, u4_y, 0, -10.16, -2.54), 0, "input"))    # EN
    L.append(gl("VIN", *psp(u4_x, u4_y, 0, -10.16, 2.54), 0, "input"))     # IN
    L.append(gl("GND", *psp(u4_x, u4_y, 0, 0, -7.62), 270, "input"))       # GND
    L.append(gl("SW", *psp(u4_x, u4_y, 0, 10.16, 2.54), 180, "output"))    # SW
    L.append(gl("BST", *psp(u4_x, u4_y, 0, 10.16, 0), 180, "output"))      # BST

    # Bootstrap cap
    vcap("C42", "100n", fp0402, "BST", "SW", 240, 40)

    # --- L1 inductor (horizontal angle 90 → pin1 left=SW, pin2 right=+5V) ---
    l1_x, l1_y = 255, 50
    P.append(
        sym("Device:L", "L1", "4.7uH",
            "AdeptBT:L_6.3x6.3_H3", l1_x, l1_y, ["1", "2"], 90)
    )
    L.append(gl("SW", *psp(l1_x, l1_y, 90, *V1), 0, "passive"))
    L.append(gl("+5V", *psp(l1_x, l1_y, 90, *V2), 180, "output"))

    # Buck output caps
    vcap("C41", "22u", fp0805, "+5V", "GND", 270, 55)
    vcap("C412", "22u", fp0805, "+5V", "GND", 280, 55)

    # ================================================================
    #  LDO
    # ================================================================
    T.append(txt("LDO", 300, 22))

    vcap("C50", "10u", fp0805, "+5V", "GND", 305, 55)

    u6_x, u6_y = 330, 50
    P.append(
        sym("Regulator_Linear:AMS1117-3.3", "U6", "AMS1117-3.3",
            "AdeptBT:SOT-223-3_TabPin2", u6_x, u6_y, ["1", "2", "3"])
    )
    # pin lib: 1=GND(0,-7.62) 2=VO(7.62,0) 3=VI(-7.62,0)
    L.append(gl("GND", *psp(u6_x, u6_y, 0, 0, -7.62), 270, "input"))
    L.append(gl("+3V3", *psp(u6_x, u6_y, 0, 7.62, 0), 180, "output"))
    L.append(gl("+5V", *psp(u6_x, u6_y, 0, -7.62, 0), 0, "input"))

    vcap("C51", "22u", fp0805, "+3V3", "GND", 350, 55)

    # ================================================================
    #  BATTERY CHARGER
    # ================================================================
    T.append(txt("Battery charger", 370, 22))

    u5_x, u5_y = 435, 55
    P.append(
        sym("Battery_Management:MCP73871", "U5", "MCP73871",
            "AdeptBT:QFN-20-1EP_4x4mm_P0.5mm_EP2.5x2.5mm",
            u5_x, u5_y, [str(i) for i in range(1, 22)])
    )
    # Right side
    L.append(gl("+5V", *psp(u5_x, u5_y, 0, 17.78, 15.24), 180, "output"))    # OUT 1/20
    L.append(gl("VBAT", *psp(u5_x, u5_y, 0, 17.78, 7.62), 180, "output"))    # VBAT 14/15
    L.append(gl("VBAT", *psp(u5_x, u5_y, 0, 17.78, 2.54), 180, "input"))     # VBAT_SENSE 16
    L.append(nc(*psp(u5_x, u5_y, 0, 17.78, -5.08)))                           # ~PG  6
    L.append(nc(*psp(u5_x, u5_y, 0, 17.78, -12.7)))                           # STAT2 7
    L.append(gl("CHG_STAT", *psp(u5_x, u5_y, 0, 17.78, -10.16), 180, "output"))  # STAT1 8
    # Left side
    L.append(gl("+5V", *psp(u5_x, u5_y, 0, -17.78, 15.24), 0, "input"))      # VPCC 2
    L.append(gl("GND", *psp(u5_x, u5_y, 0, -17.78, 10.16), 0, "input"))      # SEL 3
    L.append(gl("GND", *psp(u5_x, u5_y, 0, -17.78, 2.54), 0, "input"))       # PROG2 4
    L.append(gl("GND", *psp(u5_x, u5_y, 0, -17.78, -5.08), 0, "input"))      # THERM 5
    L.append(gl("+5V", *psp(u5_x, u5_y, 0, -17.78, -10.16), 0, "input"))     # ~TE 9
    L.append(gl("GND", *psp(u5_x, u5_y, 0, -17.78, 0), 0, "input"))          # PROG3 12
    L.append(gl("PROG1", *psp(u5_x, u5_y, 0, -17.78, 5.08), 0, "input"))     # PROG1 13
    L.append(gl("+5V", *psp(u5_x, u5_y, 0, -17.78, -15.24), 0, "input"))     # CE 17
    # Top / bottom
    L.append(gl("+5V", *psp(u5_x, u5_y, 0, 0, 22.86), 90, "input"))          # IN 18/19
    L.append(gl("GND", *psp(u5_x, u5_y, 0, 0, -22.86), 270, "input"))        # VSS 10/11/21

    vres("RPROG1", "2k", "AdeptBT:R_0603_1608Metric", "PROG1", "GND", 410, 75)
    vcap("C61", "4.7u", fp0805, "+5V", "GND", 400, 90)
    vcap("C60", "4.7u", fp0805, "VBAT", "GND", 465, 90)

    # J_BAT1
    jbat_x, jbat_y = 485, 55
    P.append(
        sym("Connector_Generic_MountingPin:Conn_01x02_MountingPin",
            "J_BAT1", "BAT",
            "AdeptBT:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal",
            jbat_x, jbat_y, ["1", "2", "MP"])
    )
    conn_labels(jbat_x, jbat_y, 2, ["VBAT", "GND"], P, L)
    L.append(gl("GND", *psp(jbat_x, jbat_y, 0, 0, -7.62), 270, "input"))

    # ================================================================
    #  MCU U1 + USB / SWD / LEDs
    # ================================================================
    T.append(txt("MCU U1 MDBT50Q-1MV2", 100, 115))

    mcu_x, mcu_y = 200, 200
    P.append(
        sym("jlc:MDBT50Q-1MV2", "U1", "MDBT50Q-1MV2",
            "jlc:COMM-SMD_MDBT50Q-1MV2-1", mcu_x, mcu_y,
            [str(i) for i in range(1, 62)])
    )

    # Left bank: pins 1-31  lib (-31.75, 38.1 - (n-1)*2.54)
    left_nets = {
        1: "GND", 2: "GND", 9: "AIN1", 11: "AIN0", 15: "GND",
        20: "AIN2", 21: "AIN3", 22: "OUT1_DRV", 23: "LED_USER",
        24: "OUT2_DRV", 28: "+3V3", 30: "+3V3",
    }
    for n in range(1, 32):
        ly = 38.1 - (n - 1) * 2.54
        px, py = psp(mcu_x, mcu_y, 0, -31.75, ly)
        if n in left_nets:
            L.append(gl(left_nets[n], px, py, 0, "input"))
        else:
            L.append(nc(px, py))

    # Right bank: pins 32-61  lib (31.75, -38.1 + (n-32)*2.54)
    right_nets = {
        32: "USB_5V", 33: "GND", 34: "USB_D-", 35: "USB_D+",
        36: "TMC_UART", 37: "STEP1_EN", 38: "STEP2_STEP",
        39: "STEP2_DIR", 40: "nRESET", 41: "STEP2_EN",
        43: "STEP1_STEP", 44: "STEP1_DIR",
        45: "D0", 46: "D1", 47: "D2", 48: "D3",
        49: "CHG_STAT", 51: "SWDIO", 53: "SWDCLK", 55: "GND",
    }
    for n in range(32, 62):
        ly = -38.1 + (n - 32) * 2.54
        px, py = psp(mcu_x, mcu_y, 0, 31.75, ly)
        if n in right_nets:
            L.append(gl(right_nets[n], px, py, 180, "output"))
        else:
            L.append(nc(px, py))

    # MCU decoupling
    vcap("C1", "100n", fp0402, "+3V3", "GND", 158, 142)
    vcap("C2", "1u", fp0603, "+3V3", "GND", 168, 142)

    # ---- USB ----
    T.append(txt("USB + SWD", 25, 115))

    jusb_x, jusb_y = 55, 185
    usb_all = [
        "A4", "A9", "B4", "B9", "A6", "B6", "A7", "B7",
        "A5", "B5", "A1", "A12", "B1", "B12", "SH", "A8", "B8",
    ]
    P.append(
        sym("AdeptBT:USB_C_GCT_16P", "J_USB1", "USB-C",
            "AdeptBT:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal",
            jusb_x, jusb_y, usb_all)
    )
    for net, ly in zip(
        ["USB_5V", "USB_D+", "USB_D-", "CC1", "CC2", "GND"],
        [5.08, 2.54, 0, -2.54, -5.08, -7.62],
    ):
        L.append(gl(net, *psp(jusb_x, jusb_y, 0, -5.08, ly), 0, "input"))
    L.append(nc(*psp(jusb_x, jusb_y, 0, 5.08, 2.54)))   # SBU1
    L.append(nc(*psp(jusb_x, jusb_y, 0, 5.08, 0)))       # SBU2

    vcap("C3", "100n", fp0402, "USB_5V", "GND", 70, 212)
    vcap("C4", "10u", fp0805, "USB_5V", "GND", 80, 212)
    vres("RCC1", "5.1k", fp_r06, "CC1", "GND", 40, 215)
    vres("RCC2", "5.1k", fp_r06, "CC2", "GND", 50, 215)

    # ---- SWD ----
    jswd_x, jswd_y = 260, 165
    P.append(
        sym("Connector_Generic:Conn_01x05", "J_SWD1", "SWD",
            "AdeptBT:PinHeader_1x05_P2.54mm_Vertical", jswd_x, jswd_y,
            [str(i) for i in range(1, 6)])
    )
    conn_labels(jswd_x, jswd_y, 5,
                ["SWDIO", "SWDCLK", "GND", "+3V3", "nRESET"], P, L)

    # ================================================================
    #  STATUS LEDs (vertical chain: LED → wire → R)
    # ================================================================
    T.append(txt("Status LEDs", 280, 115))

    for lx, led_ref, led_val, r_ref, anode_net, tail_net in [
        (295, "PWR1", "PWR", "R4", "+3V3", "GND"),
        (315, "CHG1", "CHG", "R5", "+3V3", "CHG_STAT"),
        (335, "USR1", "USR", "R6", "LED_USER", "GND"),
    ]:
        ly_led = 140
        # LED vertical (angle 90): A top, K bottom
        P.append(
            sym("Device:LED", led_ref, led_val, fp_led,
                lx, ly_led, ["1", "2"], 90)
        )
        led_a = psp(lx, ly_led, 90, *H2)  # A top
        led_k = psp(lx, ly_led, 90, *H1)  # K bottom
        L.append(gl(anode_net, *led_a, 90, "input"))

        # R directly below
        ly_r = ly_led + 15.24
        P.append(sym("Device:R", r_ref, "1k", fp_r06, lx, ly_r, ["1", "2"]))
        r_p1 = (lx, ly_r - 3.81)
        r_p2 = (lx, ly_r + 3.81)

        # Wire LED.K → R.pin1 (vertical, same X)
        W.append(wr(*led_k, *r_p1))
        k_net = f"Net_{led_ref}_K"
        L.append(gl(k_net, *led_k, 0, "passive"))

        L.append(gl(tail_net, *r_p2, 270, "passive"))

    # ================================================================
    #  OUT DRIVERS (R → wire → Q; D flyback)
    # ================================================================
    T.append(txt("OUT drivers", 370, 115))

    for ox, q_ref, r_ref, d_ref, drv_net, out_net, b_net in [
        (390, "Q2", "R2", "D2", "OUT1_DRV", "OUT1", "OUT1_B"),
        (430, "Q3", "R3", "D3", "OUT2_DRV", "OUT2", "OUT2_B"),
    ]:
        # R (vertical)
        ry = 150
        P.append(sym("Device:R", r_ref, "1k", fp_r06, ox, ry, ["1", "2"]))
        r_p1 = (ox, ry - 3.81)
        r_p2 = (ox, ry + 3.81)
        L.append(gl(drv_net, *r_p1, 90, "input"))

        # Q NPN
        qy = ry + 20.32
        P.append(
            sym("Device:Q_NPN", q_ref, "MMBT2222A",
                "Package_TO_SOT_SMD:SOT-23", ox + 5.08, qy,
                ["1", "2", "3"])
        )
        q_b = psp(ox + 5.08, qy, 0, -5.08, 0)       # B
        q_e = psp(ox + 5.08, qy, 0, 2.54, -5.08)     # E (below)
        q_c = psp(ox + 5.08, qy, 0, 2.54, 5.08)      # C (above)

        # Wire R.pin2 → Q.B
        W.append(wr(*r_p2, *q_b))
        L.append(gl(b_net, *r_p2, 0, "passive"))

        L.append(gl("GND", *q_e, 270, "input"))

        # D flyback (angle 270 → K top V+, A bottom)
        dy = qy - 15.24
        P.append(
            sym("Device:D", d_ref, "1N4148W", "Diode_SMD:D_SOD-123",
                ox + 7.62, dy, ["1", "2"], 270)
        )
        d_k = psp(ox + 7.62, dy, 270, *H1)
        d_a = psp(ox + 7.62, dy, 270, *H2)

        # Wire D.A → Q.C (both at same X, OUT net)
        W.append(wr(*d_a, *q_c))
        L.append(gl(out_net, *q_c, 90, "output"))
        L.append(gl("V+", *d_k, 90, "input"))

    # ================================================================
    #  TMC2209 U2 + STEP1  /  U3 + STEP2
    # ================================================================

    def place_tmc(ref, x, y, suffix, ms1_net):
        tmc_pins = [str(i) for i in range(1, 30)]
        P.append(
            sym("jlc:TMC2209-LA", ref, "TMC2209-LA",
                "jlc:QFN-28_L5.0-W5.0-P0.50-BL-EP", x, y, tmc_pins)
        )
        # Left pins 1-15:  lib (-15.24, 17.78 - (n-1)*2.54)
        left = {
            1: f"B2_{suffix}", 2: f"STEP{suffix}_EN", 3: "GND",
            4: f"CPO{suffix}", 5: f"CPI{suffix}", 6: f"VCP{suffix}",
            7: "GND", 8: f"5VOUT{suffix}", 9: ms1_net,
            10: "GND", 13: "GND", 14: "TMC_UART", 15: "+3V3",
        }
        for n, net in left.items():
            ly = 17.78 - (n - 1) * 2.54
            L.append(gl(net, *psp(x, y, 0, -15.24, ly), 0, "input"))
        for n in (11, 12):
            ly = 17.78 - (n - 1) * 2.54
            L.append(nc(*psp(x, y, 0, -15.24, ly)))

        # Right pins 16-29
        rly = {
            16: -16.51, 17: -13.97, 18: -11.43, 19: -8.89,
            20: -6.35, 21: -3.81, 22: -1.27, 23: 1.27,
            24: 3.81, 25: 6.35, 26: 8.89, 27: 11.43,
            28: 13.97, 29: 16.51,
        }
        right = {
            16: f"STEP{suffix}_STEP", 17: f"VREF_{suffix}",
            18: "GND", 19: f"STEP{suffix}_DIR", 20: "GND",
            21: f"A2_{suffix}", 22: f"VM{suffix}",
            23: f"BRA_{suffix}", 24: f"A1_{suffix}",
            26: f"B1_{suffix}", 27: f"BRB_{suffix}",
            28: f"VM{suffix}", 29: "GND",
        }
        for n, net in right.items():
            L.append(gl(net, *psp(x, y, 0, 15.24, rly[n]), 180, "output"))
        L.append(nc(*psp(x, y, 0, 15.24, rly[25])))   # NC pin 25

        # --- caps near TMC ---
        cx_l = x - 28
        c0 = 10 if suffix == "1" else 20

        vcap(f"C{c0}", "22n/50V", fp0603, f"CPO{suffix}", f"CPI{suffix}",
             cx_l, y - 10)
        vcap(f"C{c0+1}", "100n", fp0402, f"VCP{suffix}", f"VM{suffix}",
             cx_l + 10, y - 10)
        vcap(f"C{c0+2}", "4.7u", fp0805, f"5VOUT{suffix}", "GND",
             cx_l, y + 5)
        vcap(f"C{c0+3}", "100n", fp0402, "+3V3", "GND",
             cx_l + 10, y + 5)
        vcap(f"C{c0+4}", "100n", fp0402, f"VM{suffix}", "GND",
             x + 25, y - 5)
        vcap(f"C{c0+5}", "100u/25V", fp_elec, f"VM{suffix}", "GND",
             x + 35, y - 5, polar=True)

        # Sense Rs
        vres(f"RSA{suffix}", "0.10", fp_r12, f"BRA_{suffix}", "GND",
             x + 25, y + 10)
        vres(f"RSB{suffix}", "0.10", fp_r12, f"BRB_{suffix}", "GND",
             x + 35, y + 10)
        vres(f"RVREF{suffix}", "10k", fp_r06, f"VREF_{suffix}", "GND",
             x + 45, y + 10)

        # Stepper connector
        jx = x + 55
        P.append(
            sym("Connector_Generic:Conn_01x06", f"J_STEP{suffix}",
                "TE_2383941-6",
                "AdeptBT:TE_2383945-6_1x06_P3.81mm_SMD",
                jx, y, [str(i) for i in range(1, 7)])
        )
        conn_labels(jx, y, 6,
                    [f"A1_{suffix}", f"A2_{suffix}", f"B1_{suffix}",
                     f"B2_{suffix}", f"VM{suffix}", "GND"], P, L)

    T.append(txt("TMC U2 + STEP1", 25, 260))
    place_tmc("U2", 100, 310, "1", "GND")

    T.append(txt("TMC U3 + STEP2", 215, 260))
    place_tmc("U3", 290, 310, "2", "+3V3")

    # ================================================================
    #  CONNECTORS / HEADERS / HOLES
    # ================================================================
    T.append(txt("Connectors + holes", 460, 115))

    jan_x, jan_y = 480, 165
    P.append(
        sym("Connector_Generic:Conn_01x07", "J_AN1", "ANALOG",
            "AdeptBT:PinHeader_1x07_P2.54mm_Vertical", jan_x, jan_y,
            [str(i) for i in range(1, 8)])
    )
    conn_labels(jan_x, jan_y, 7,
                ["AIN0", "AIN1", "AIN2", "AIN3", "+3V3", "+5V", "GND"],
                P, L)

    jdg_x, jdg_y = 480, 205
    P.append(
        sym("Connector_Generic:Conn_01x06", "J_DG1", "DIGITAL",
            "AdeptBT:PinHeader_1x06_P2.54mm_Vertical", jdg_x, jdg_y,
            [str(i) for i in range(1, 7)])
    )
    conn_labels(jdg_x, jdg_y, 6,
                ["D0", "D1", "D2", "D3", "+3V3", "GND"], P, L)

    hole_fp = "AdeptBT:MountingHole_2.2mm_M2"
    for i, hx in enumerate([500, 515, 530, 545], 1):
        P.append(sym("Mechanical:MountingHole", f"M{i}", "M2", hole_fp,
                      hx, 240, []))

    # ================================================================
    #  POWER SYMBOLS + PWR_FLAG
    # ================================================================
    pwr_y = 395
    for ref, lib, val, px in [
        ("#PWR01", "power:GND", "GND", 25),
        ("#PWR02", "power:+3V3", "+3V3", 40),
        ("#PWR03", "power:+5V", "+5V", 55),
    ]:
        P.append(sym(lib, ref, val, "", px, pwr_y, ["1"]))
        L.append(gl(val, px, pwr_y, 0, "input"))

    for i, (net, px) in enumerate(
        [("GND", 75), ("VIN", 90), ("USB_5V", 105), ("VIN_RAW", 120)], 1
    ):
        P.append(sym("power:PWR_FLAG", f"#FLG{i:02d}", "PWR_FLAG", "",
                      px, pwr_y + 10, ["1"]))
        L.append(gl(net, px, pwr_y + 10, 0, "input"))

    # ================================================================
    #  ASSEMBLE
    # ================================================================
    body = "\n".join(T + P + L + W)
    sch = (
        f"(kicad_sch\n"
        f'\t(version 20260306)\n'
        f'\t(generator "gen_adeptbt_sch")\n'
        f'\t(generator_version "0.14")\n'
        f'\t(uuid "{SHEET_UUID}")\n'
        f'\t(paper "A2")\n'
        f"\t(title_block\n"
        f'\t\t(title "AdeptBT")\n'
        f'\t\t(date "2026-11-25")\n'
        f'\t\t(rev "0.14")\n'
        f'\t\t(company "coconnor55")\n'
        f'\t\t(comment 1 "JLCPCB: Raytac C5118826, TMC C465949,'
        f' TE C3816695, MCP73871 C5121473, AP63205 C2071056")\n'
        f'\t\t(comment 2 "Power path + sense Rs; CC Rd;'
        f' stackup docs/STACKUP.md")\n'
        f"\t)\n"
        f"{lib_syms}\n"
        f"{body}\n"
        f"\t(sheet_instances\n"
        f'\t\t(path "/"\n'
        f'\t\t\t(page "1")\n'
        f"\t\t)\n"
        f"\t)\n"
        f"\t(embedded_fonts no)\n"
        f")\n"
    )

    OUT.write_text(sch)
    print(f"Wrote {OUT}")
    print(f"  {len(P)} parts, {len(L)} labels/NC, {len(W)} wires, {len(T)} texts")


if __name__ == "__main__":
    main()
