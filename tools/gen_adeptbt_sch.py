#!/usr/bin/env python3
"""Generate AdeptBT schematic (rev 0.12) — symbols + global labels from NETLIST."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HW = ROOT / "hardware"
JLC_SYM = HW / "libs" / "jlc" / "jlc.kicad_sym"
KICAD_SYM = Path(
    "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"
)
OUT = HW / "adeptbt.kicad_sch"
PROJECT = "adeptbt"
SHEET_UUID = "46fc2e97-3959-4095-a2dc-23d7ed974c68"


def uid() -> str:
    return str(uuid.uuid4())


def extract_symbol(lib_path: Path, name: str) -> str:
    text = lib_path.read_text()
    # top-level symbols are indented with one tab inside kicad_symbol_lib
    pat = rf'\n\t\(symbol "{re.escape(name)}"'
    m = re.search(pat, text)
    if not m:
        # Connector_Generic style may use two tabs in some versions
        pat2 = rf'\(symbol "{re.escape(name)}"'
        m = re.search(pat2, text)
        if not m:
            raise KeyError(f"{name} not in {lib_path}")
        start = m.start()
    else:
        start = m.start() + 1  # skip leading newline
    i = start
    depth = 0
    while i < len(text):
        c = text[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                block = text[start : i + 1]
                # Derived parts (extends) have no pins — pull the parent body.
                ext = re.search(r'\(extends "([^"]+)"\)', block)
                if ext:
                    parent_name = ext.group(1)
                    parent = extract_symbol(lib_path, parent_name)
                    parent = rename_symbol_tree(parent.lstrip(), parent_name, name)
                    return parent
                return block
        i += 1
    raise RuntimeError(f"unclosed symbol {name}")


def rename_symbol_tree(block: str, old_name: str, new_name: str) -> str:
    """Rename parent symbol and every nested unit prefix old_name_U_S → new_name_U_S."""
    block = re.sub(
        rf'^\(symbol "{re.escape(old_name)}"',
        f'(symbol "{new_name}"',
        block,
        count=1,
    )
    block = re.sub(
        rf'\(symbol "{re.escape(old_name)}_(\d+)_(\d+)"',
        rf'(symbol "{new_name}_\1_\2"',
        block,
    )
    return block


def embed_as(lib_id: str, block: str) -> str:
    """Rename outer (symbol "Name") to Lib:Name; keep unit prefixes on the entry name."""
    block = block.lstrip()
    entry = lib_id.split(":", 1)[-1]
    m = re.match(r'^\(symbol "([^"]+)"', block)
    if m and m.group(1) != entry and ":" not in m.group(1):
        block = rename_symbol_tree(block, m.group(1), entry)
    return re.sub(
        r'^\(symbol "[^"]+"',
        f'(symbol "{lib_id}"',
        block,
        count=1,
    )


def prop(name: str, value: str, x: float, y: float, hide: bool = False) -> str:
    hide_s = "\n\t\t\t(hide yes)" if hide else ""
    return f"""\t\t(property "{name}" "{value}"
\t\t\t(at {x} {y} 0){hide_s}
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t)
\t\t)"""


def pin_uuids(numbers: list[str]) -> str:
    lines = []
    for n in numbers:
        lines.append(f'\t\t(pin "{n}"\n\t\t\t(uuid "{uid()}")\n\t\t)')
    return "\n".join(lines)


def instance(ref: str) -> str:
    return f"""\t\t(instances
\t\t\t(project "{PROJECT}"
\t\t\t\t(path "/{SHEET_UUID}"
\t\t\t\t\t(reference "{ref}")
\t\t\t\t\t(unit 1)
\t\t\t\t)
\t\t\t)
\t\t)"""


def place_symbol(
    lib_id: str,
    ref: str,
    value: str,
    footprint: str,
    x: float,
    y: float,
    pin_nums: list[str],
    angle: float = 0,
) -> str:
    return f"""\t(symbol
\t\t(lib_id "{lib_id}")
\t\t(at {x} {y} {angle:g})
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(uuid "{uid()}")
{prop("Reference", ref, x, y - 5.08)}
{prop("Value", value, x, y + 5.08)}
{prop("Footprint", footprint, x, y, True)}
{prop("Datasheet", "~", x, y, True)}
{prop("Description", "", x, y, True)}
{pin_uuids(pin_nums)}
{instance(ref)}
\t)"""


def pin_xy(ix: float, iy: float, lx: float, ly: float) -> tuple[float, float]:
    """Library pin local (lx, ly) → sheet mm. Sheet Y is flipped vs symbol editor."""
    return ix + lx, iy - ly


def global_label(name: str, x: float, y: float, angle: float = 0, shape: str = "input") -> str:
    return f"""\t(global_label "{name}"
\t\t(shape {shape})
\t\t(at {x:g} {y:g} {angle:g})
\t\t(fields_autoplaced yes)
\t\t(effects
\t\t\t(font
\t\t\t\t(size 1.27 1.27)
\t\t\t)
\t\t\t(justify left)
\t\t)
\t\t(uuid "{uid()}")
\t\t(property "Intersheetrefs" "${{INTERSHEET_REFS}}"
\t\t\t(at {x:g} {y:g} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(hide yes)
\t\t\t)
\t\t)
\t)"""


def no_connect(x: float, y: float) -> str:
    return f"""\t(no_connect
\t\t(at {x:g} {y:g})
\t\t(uuid "{uid()}")
\t)"""


def label_pin(
    net: str,
    ix: float,
    iy: float,
    lx: float,
    ly: float,
    angle: float = 0,
    shape: str = "passive",
) -> str:
    x, y = pin_xy(ix, iy, lx, ly)
    return global_label(net, x, y, angle, shape)


def text_block(txt: str, x: float, y: float, size: float = 1.5) -> str:
    esc = txt.replace("\\", "\\\\").replace('"', '\\"')
    return f"""\t(text "{esc}"
\t\t(exclude_from_sim no)
\t\t(at {x} {y} 0)
\t\t(effects
\t\t\t(font
\t\t\t\t(size {size} {size})
\t\t\t)
\t\t\t(justify left top)
\t\t)
\t\t(uuid "{uid()}")
\t)"""


def conn_pins(n: int) -> list[str]:
    return [str(i) for i in range(1, n + 1)]


# Connector_Generic |pin1| Y offsets (lib +Y); sheet labels use negated Y
CONN_Y0 = {2: 0.0, 3: 2.54, 5: 5.08, 6: 5.08, 7: 7.62}


def label_conn_row(nets: list[str], x: float, y: float) -> list[str]:
    """Labels on Connector_Generic left pin tips (pitch 2.54)."""
    out = []
    y0 = CONN_Y0[len(nets)]
    px = x - 5.08
    for i, net in enumerate(nets):
        # KiCad sheet Y: negate library pin Y for correct binding
        out.append(global_label(net, px, y - y0 + i * 2.54, 0, "input"))
    return out


def _q_numeric_pins(block: str, kind: str) -> str:
    """Map Device Q pin numbers G/D/S or B/C/E → 1/2/3 for SOT-23 footprints."""
    if kind == "PMOS":
        # G=1, S=2, D=3 (AO3407)
        block = block.replace('(number "G"', '(number "1"', 1)
        block = block.replace('(number "S"', '(number "2"', 1)
        block = block.replace('(number "D"', '(number "3"', 1)
    else:
        # B=1, E=2, C=3 (MMBT2222A)
        block = block.replace('(number "B"', '(number "1"', 1)
        block = block.replace('(number "E"', '(number "2"', 1)
        block = block.replace('(number "C"', '(number "3"', 1)
    return block


def main() -> None:
    # --- library symbols ---
    conn_lib = KICAD_SYM / "Connector_Generic.kicad_sym"
    connector_lib = KICAD_SYM / "Connector.kicad_sym"
    device_lib = KICAD_SYM / "Device.kicad_sym"
    power_lib = KICAD_SYM / "power.kicad_sym"
    mech_lib = KICAD_SYM / "Mechanical.kicad_sym"
    reg_sw = KICAD_SYM / "Regulator_Switching.kicad_sym"
    reg_lin = KICAD_SYM / "Regulator_Linear.kicad_sym"
    bat_mgmt = KICAD_SYM / "Battery_Management.kicad_sym"

    needed = [
        ("jlc:MDBT50Q-1MV2", extract_symbol(JLC_SYM, "MDBT50Q-1MV2")),
        ("jlc:TMC2209-LA", extract_symbol(JLC_SYM, "TMC2209-LA")),
        ("Connector_Generic:Conn_01x06", extract_symbol(conn_lib, "Conn_01x06")),
        ("Connector_Generic:Conn_01x07", extract_symbol(conn_lib, "Conn_01x07")),
        ("Connector_Generic:Conn_01x05", extract_symbol(conn_lib, "Conn_01x05")),
        ("Connector_Generic:Conn_01x03", extract_symbol(conn_lib, "Conn_01x03")),
        ("Connector_Generic:Conn_01x02", extract_symbol(conn_lib, "Conn_01x02")),
        (
            "Connector_Generic_MountingPin:Conn_01x02_MountingPin",
            extract_symbol(
                KICAD_SYM / "Connector_Generic_MountingPin.kicad_sym",
                "Conn_01x02_MountingPin",
            ),
        ),
        (
            "Connector:Barrel_Jack_MountingPin",
            extract_symbol(connector_lib, "Barrel_Jack_MountingPin"),
        ),
        ("Mechanical:MountingHole", extract_symbol(mech_lib, "MountingHole")),
        (
            "AdeptBT:USB_C_GCT_16P",
            extract_symbol(HW / "libs" / "AdeptBT.kicad_sym", "USB_C_GCT_16P"),
        ),
        ("Device:Q_NPN", _q_numeric_pins(extract_symbol(device_lib, "Q_NPN"), "NPN")),
        ("Device:Q_PMOS", _q_numeric_pins(extract_symbol(device_lib, "Q_PMOS"), "PMOS")),
        ("Device:D", extract_symbol(device_lib, "D")),
        ("Device:R", extract_symbol(device_lib, "R")),
        ("Device:C", extract_symbol(device_lib, "C")),
        ("Device:C_Polarized", extract_symbol(device_lib, "C_Polarized")),
        ("Device:L", extract_symbol(device_lib, "L")),
        ("Device:Fuse", extract_symbol(device_lib, "Fuse")),
        ("Device:LED", extract_symbol(device_lib, "LED")),
        ("Regulator_Switching:AP63205WU", extract_symbol(reg_sw, "AP63205WU")),
        ("Regulator_Linear:AMS1117-3.3", extract_symbol(reg_lin, "AMS1117-3.3")),
        ("Battery_Management:MCP73871", extract_symbol(bat_mgmt, "MCP73871")),
        ("power:GND", extract_symbol(power_lib, "GND")),
        ("power:+3V3", extract_symbol(power_lib, "+3V3")),
        ("power:+5V", extract_symbol(power_lib, "+5V")),
        ("power:PWR_FLAG", extract_symbol(power_lib, "PWR_FLAG")),
    ]

    lib_syms = "\n".join(embed_as(lid, blk) for lid, blk in needed)

    parts: list[str] = []
    labels: list[str] = []

    # All coords on 1.27 mm schematic grid
    cy = 25.4
    # KiCad annotation requires every ref to end in a digit (J_USB → J_USB1).
    connectors = [
        ("J_STEP1", "STEPPER1", "AdeptBT:TE_2383945-6_1x06_P3.81mm_SMD", 25.4,
         ["A1_1", "A2_1", "B1_1", "B2_1", "VM1", "GND"], 6),
        ("J_STEP2", "STEPPER2", "AdeptBT:TE_2383945-6_1x06_P3.81mm_SMD", 50.8,
         ["A1_2", "A2_2", "B1_2", "B2_2", "VM2", "GND"], 6),
        ("J_PWR1", "PWR_OUT", "AdeptBT:TE_2383945-6_1x06_P3.81mm_SMD", 76.2,
         ["VIN_RAW", "GND", "V+", "OUT1", "V+", "OUT2"], 6),
        # TE footprint file name unchanged (same 3.81 mm geometry); value TE 2383941-6
        ("J_AN1", "ANALOG", "AdeptBT:PinHeader_1x07_P2.54mm_Vertical", 101.6,
         ["AIN0", "AIN1", "AIN2", "AIN3", "+3V3", "+5V", "GND"], 7),
        ("J_DG1", "DIGITAL", "AdeptBT:PinHeader_1x06_P2.54mm_Vertical", 127.0,
         ["D0", "D1", "D2", "D3", "+3V3", "GND"], 6),
        ("J_SWD1", "SWD", "AdeptBT:PinHeader_1x05_P2.54mm_Vertical", 152.4,
         ["SWDIO", "SWDCLK", "GND", "+3V3", "nRESET"], 5),
        ("J_BAT1", "BAT", "AdeptBT:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal", 177.8,
         ["VBAT", "GND"], 2),
        ("J_USB1", "USB-C", "AdeptBT:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal", 203.2,
         ["USB_5V", "USB_D+", "USB_D-", "CC1", "CC2", "GND"], 6),
    ]
    # GCT 16P pad set; stacked same-net pins share one label tip.
    usb_pins = [
        "A4", "A9", "B4", "B9",
        "A6", "B6",
        "A7", "B7",
        "A5", "B5",
        "A1", "A12", "B1", "B12", "SH",
        "A8", "B8",
    ]
    for ref, val, fp, x, nets, n in connectors:
        if ref == "J_PWR1":
            val = "TE_2383941-6"
        if ref.startswith("J_STEP"):
            val = "TE_2383941-6"
        if ref == "J_USB1":
            parts.append(
                place_symbol("AdeptBT:USB_C_GCT_16P", ref, val, fp, x, cy, usb_pins)
            )
            # Left stack tips (lib Y): VBUS 5.08, D+ 2.54, D- 0, CC1 -2.54, CC2 -5.08, GND -7.62
            for net, ly in zip(
                nets, [5.08, 2.54, 0.0, -2.54, -5.08, -7.62], strict=True
            ):
                labels.append(label_pin(net, x, cy, -5.08, ly, 0, "input"))
            # SBU unused
            labels.append(no_connect(*pin_xy(x, cy, 5.08, 2.54)))
            labels.append(no_connect(*pin_xy(x, cy, 5.08, 0.0)))
            continue
        if ref == "J_BAT1":
            lib = "Connector_Generic_MountingPin:Conn_01x02_MountingPin"
            parts.append(place_symbol(lib, ref, val, fp, x, cy, ["1", "2", "MP"]))
            labels += label_conn_row(nets, x, cy)
            labels.append(label_pin("GND", x, cy, 0.0, -7.62, 270, "input"))
            continue
        lib = f"Connector_Generic:Conn_01x{n:02d}"
        parts.append(place_symbol(lib, ref, val, fp, x, cy, conn_pins(n)))
        labels += label_conn_row(nets, x, cy)

    # J_DC1 5.5×2.1 barrel — pin1 tip=VIN_RAW, pin2 sleeve=GND, MP→GND
    dc_x, dc_y = 228.6, 25.4
    parts.append(
        place_symbol(
            "Connector:Barrel_Jack_MountingPin",
            "J_DC1",
            "5.5x2.1",
            "AdeptBT:BarrelJack_CUI_PJ-063AH_Horizontal",
            dc_x,
            dc_y,
            ["1", "2", "MP"],
        )
    )
    labels.append(label_pin("VIN_RAW", dc_x, dc_y, 7.62, 2.54, 180, "output"))
    labels.append(label_pin("GND", dc_x, dc_y, 7.62, -2.54, 180, "output"))
    labels.append(label_pin("GND", dc_x, dc_y, 0.0, -7.62, 270, "input"))

    # Jumpers (docs/NETLIST.md): JP_V+1 3V3/V+/VIN; JP_VM* VIN↔VMn
    jumpers = [
        ("JP_V+1", "V+", "AdeptBT:PinHeader_1x03_P2.54mm_Vertical", 254.0,
         ["+3V3", "V+", "VIN"], 3),
        ("JP_VM1", "VM1", "AdeptBT:PinHeader_1x02_P2.54mm_Vertical", 279.4,
         ["VIN", "VM1"], 2),
        ("JP_VM2", "VM2", "AdeptBT:PinHeader_1x02_P2.54mm_Vertical", 292.1,
         ["VIN", "VM2"], 2),
    ]
    for ref, val, fp, x, nets, n in jumpers:
        lib = f"Connector_Generic:Conn_01x{n:02d}"
        parts.append(place_symbol(lib, ref, val, fp, x, cy, conn_pins(n)))
        labels += label_conn_row(nets, x, cy)

    # Corner mounting holes (M2 screw) — mechanical only
    hole_fp = "AdeptBT:MountingHole_2.2mm_M2"
    for i, x in enumerate([25.4, 50.8, 76.2, 101.6], start=1):
        parts.append(
            place_symbol(
                "Mechanical:MountingHole",
                f"M{i}",
                "M2",
                hole_fp,
                x,
                50.8,
                [],
            )
        )

    # ========== MCU ==========
    mcu_x, mcu_y = 101.6, 139.7
    mdbt_pins = [str(i) for i in range(1, 62)]
    parts.append(
        place_symbol(
            "jlc:MDBT50Q-1MV2",
            "U1",
            "MDBT50Q-1MV2",
            "jlc:COMM-SMD_MDBT50Q-1MV2-1",
            mcu_x,
            mcu_y,
            mdbt_pins,
        )
    )

    # Left-side MCU pins (angle 0 → label to the left of pin tip at x-31.75)
    # Pin Y offsets from symbol (absolute = mcu_y + pin_y)
    left_map = {
        # pin: net  (only wired pins; others float / NC for now)
        1: "GND",
        2: "GND",
        9: "AIN1",  # P0.03
        11: "AIN0",  # P0.02
        15: "GND",
        20: "AIN2",  # P0.04
        21: "AIN3",  # P0.05
        22: "OUT1_DRV",  # P0.06 → R2 → Q2 base
        23: "LED_USER",  # P0.07
        24: "OUT2_DRV",  # P0.08 → R3 → Q3 base
        28: "+3V3",  # VDD
        30: "+3V3",  # VDDH (module typically tied)
    }
    # From symbol: pin N at y = 38.1 - (N-1)*2.54 for left bank 1..31
    for n, net in left_map.items():
        lib_y = 38.1 - (n - 1) * 2.54
        px = mcu_x - 31.75
        labels.append(global_label(net, px, mcu_y - lib_y, 0, "input"))
    # NC unused left-bank GPIO / crystal / DCCH
    for n in list(range(3, 9)) + [10, 12, 13, 14, 16, 17, 18, 19, 25, 26, 27, 29, 31]:
        if n in left_map:
            continue
        lib_y = 38.1 - (n - 1) * 2.54
        labels.append(no_connect(mcu_x - 31.75, mcu_y - lib_y))

    gpio_lock = {
        32: "USB_5V",
        33: "GND",
        34: "USB_D-",
        35: "USB_D+",
        36: "TMC_UART",  # P0.14
        37: "STEP1_EN",  # P0.13
        38: "STEP2_STEP",  # P0.16
        39: "STEP2_DIR",  # P0.15
        40: "nRESET",  # P0.18
        41: "STEP2_EN",  # P0.17
        43: "STEP1_STEP",  # P0.21
        44: "STEP1_DIR",  # P0.20
        45: "D0",  # P0.23
        46: "D1",  # P0.22
        47: "D2",  # P1.00
        48: "D3",  # P0.24
        49: "CHG_STAT",  # P0.25
        51: "SWDIO",
        53: "SWDCLK",
        55: "GND",
    }
    # Right bank pin Y: pin32 at -38.1, then +2.54 each
    for n, net in gpio_lock.items():
        lib_y = -38.1 + (n - 32) * 2.54
        px = mcu_x + 31.75
        labels.append(global_label(net, px, mcu_y - lib_y, 180, "output"))
    for n in list(range(32, 62)):
        if n in gpio_lock:
            continue
        lib_y = -38.1 + (n - 32) * 2.54
        labels.append(no_connect(mcu_x + 31.75, mcu_y - lib_y))

    # ========== TMC2209 U2 / U3 ==========
    tmc_pins = [str(i) for i in range(1, 30)]

    def place_tmc(ref: str, x: float, y: float, suffix: str) -> None:
        parts.append(
            place_symbol(
                "jlc:TMC2209-LA",
                ref,
                "TMC2209-LA",
                "jlc:QFN-28_L5.0-W5.0-P0.50-BL-EP",
                x,
                y,
                tmc_pins,
            )
        )
        # Left pins 1..15: y = 17.78 - (n-1)*2.54
        # Dual UART: U2 addr 0 (MS1=MS2=GND), U3 addr 1 (MS1=+3V3, MS2=GND)
        ms1 = "GND" if suffix == "1" else "+3V3"
        left = {
            1: f"B2_{suffix}",  # OB2
            2: f"STEP{suffix}_EN",
            3: "GND",
            4: f"CPO{suffix}",
            5: f"CPI{suffix}",
            6: f"VCP{suffix}",
            7: "GND",  # SPREAD low = stealthChop default
            8: f"5VOUT{suffix}",  # local regulator out — not board +5V
            9: ms1,
            10: "GND",  # MS2
            13: "GND",  # CLK → GND for internal osc
            14: "TMC_UART",
            15: "+3V3",
        }
        for n, net in left.items():
            lib_y = 17.78 - (n - 1) * 2.54
            labels.append(global_label(net, x - 15.24, y - lib_y, 0, "input"))
        for n in (11, 12):  # DIAG, INDEX unused
            lib_y = 17.78 - (n - 1) * 2.54
            labels.append(no_connect(x - 15.24, y - lib_y))
        right_y = {
            16: -16.51,
            17: -13.97,
            18: -11.43,
            19: -8.89,
            20: -6.35,
            21: -3.81,
            22: -1.27,
            23: 1.27,
            24: 3.81,
            25: 6.35,
            26: 8.89,
            27: 11.43,
            28: 13.97,
            29: 16.51,
        }
        right = {
            16: f"STEP{suffix}_STEP",
            17: f"VREF_{suffix}",
            18: "GND",
            19: f"STEP{suffix}_DIR",
            20: "GND",  # STDBY → GND = active
            21: f"A2_{suffix}",  # OA2
            22: f"VM{suffix}",
            23: f"BRA_{suffix}",
            24: f"A1_{suffix}",  # OA1
            26: f"B1_{suffix}",  # OB1
            27: f"BRB_{suffix}",
            28: f"VM{suffix}",
            29: "GND",  # EP
        }
        for n, net in right.items():
            labels.append(
                global_label(net, x + 15.24, y - right_y[n], 180, "output")
            )
        labels.append(no_connect(x + 15.24, y - right_y[25]))  # NC pin

    place_tmc("U2", 203.2, 114.3, "1")
    place_tmc("U3", 203.2, 177.8, "2")

    def place_cap(
        ref: str,
        value: str,
        footprint: str,
        net_a: str,
        net_b: str,
        x: float,
        y: float,
        polarized: bool = False,
    ) -> None:
        """Two-pin cap; pin1 = net_a (+ for polarized), pin2 = net_b."""
        lib = "Device:C_Polarized" if polarized else "Device:C"
        parts.append(
            place_symbol(lib, ref, value, footprint, x, y, ["1", "2"])
        )
        labels.append(global_label(net_a, x, y - 3.81, 90, "passive"))
        labels.append(global_label(net_b, x, y + 3.81, 270, "passive"))

    fp0402 = "AdeptBT:C_0402_1005Metric"
    fp0603 = "AdeptBT:C_0603_1608Metric"
    fp0805 = "AdeptBT:C_0805_2012Metric"
    fp_elec = "AdeptBT:CP_Elec_6.3x5.3"

    # U1 +3V3 (Raytac DEC4-style 1µF + local 100nF) — docs/DECOUPLING.md
    place_cap("C1", "100n", fp0402, "+3V3", "GND", 165.1, 63.5)
    place_cap("C2", "1u", fp0603, "+3V3", "GND", 170.18, 63.5)
    # USB VBUS
    place_cap("C3", "100n", fp0402, "USB_5V", "GND", 195.58, 215.9)
    place_cap("C4", "10u", fp0805, "USB_5V", "GND", 200.66, 215.9)

    # U2 / U3 TMC2209 (datasheet charge pump + VS + 5VOUT + VCC_IO)
    for suffix, base_x, base_y, c0 in [
        ("1", 241.3, 101.6, 10),
        ("2", 241.3, 165.1, 20),
    ]:
        place_cap(
            f"C{c0}",
            "22n/50V",
            fp0603,
            f"CPO{suffix}",
            f"CPI{suffix}",
            base_x,
            base_y,
        )
        place_cap(
            f"C{c0 + 1}",
            "100n",
            fp0402,
            f"VCP{suffix}",
            f"VM{suffix}",
            base_x + 7.62,
            base_y,
        )
        place_cap(
            f"C{c0 + 2}",
            "4.7u",
            fp0805,
            f"5VOUT{suffix}",
            "GND",
            base_x,
            base_y + 12.7,
        )
        place_cap(
            f"C{c0 + 3}",
            "100n",
            fp0402,
            "+3V3",
            "GND",
            base_x + 7.62,
            base_y + 12.7,
        )
        place_cap(
            f"C{c0 + 4}",
            "100n",
            fp0402,
            f"VM{suffix}",
            "GND",
            base_x,
            base_y + 25.4,
        )
        place_cap(
            f"C{c0 + 5}",
            "100u/25V",
            fp_elec,
            f"VM{suffix}",
            "GND",
            base_x + 10.16,
            base_y + 25.4,
            polarized=True,
        )

    # VIN entry
    place_cap("C30", "100n", fp0402, "VIN", "GND", 88.9, 215.9)
    place_cap(
        "C31", "100u/25V", fp_elec, "VIN", "GND", 99.06, 215.9, polarized=True
    )

    # ========== Power path (VIN_RAW → protect → VIN → buck/LDO/charger) ==========
    # F1 PPTC — Device:Fuse pins at (0,±3.81)
    parts.append(
        place_symbol(
            "Device:Fuse",
            "F1",
            "PPTC_2A",
            "AdeptBT:Fuse_1812_4532Metric",
            25.4,
            165.1,
            ["1", "2"],
        )
    )
    labels.append(label_pin("VIN_RAW", 25.4, 165.1, 0, 3.81, 90))
    labels.append(label_pin("VIN_F", 25.4, 165.1, 0, -3.81, 270))

    # Q1 P-FET reverse — lib G/S/D remapped to pads 1/2/3
    qx, qy = 38.1, 165.1
    parts.append(
        place_symbol(
            "Device:Q_PMOS",
            "Q1",
            "AO3407",
            "AdeptBT:SOT-23",
            qx,
            qy,
            ["1", "2", "3"],
        )
    )
    labels.append(label_pin("GND", qx, qy, -5.08, 0, 0))  # G
    labels.append(label_pin("VIN_F", qx, qy, 2.54, -5.08, 90))  # S
    labels.append(label_pin("VIN", qx, qy, 2.54, 5.08, 270))  # D

    # D1 SMBJ24A — Device:D pin1=K left, pin2=A right; K→VIN, A→GND
    dx, dy = 50.8, 165.1
    parts.append(
        place_symbol(
            "Device:D",
            "D1",
            "SMBJ24A",
            "AdeptBT:D_SMB",
            dx,
            dy,
            ["1", "2"],
        )
    )
    labels.append(label_pin("VIN", dx, dy, -3.81, 0, 0))  # K
    labels.append(label_pin("GND", dx, dy, 3.81, 0, 180))  # A

    # U4 AP63205WU (AP63200 pinout): 1 FB, 2 EN, 3 IN, 4 GND, 5 SW, 6 BST
    # EN→VIN so buck starts before +3V3 exists; FB→+5V (fixed 5 V).
    u4x, u4y = 76.2, 165.1
    parts.append(
        place_symbol(
            "Regulator_Switching:AP63205WU",
            "U4",
            "AP63205WU-7",
            "AdeptBT:TSOT-23-6",
            u4x,
            u4y,
            ["1", "2", "3", "4", "5", "6"],
        )
    )
    labels.append(label_pin("+5V", u4x, u4y, 10.16, -2.54, 180))  # FB
    labels.append(label_pin("VIN", u4x, u4y, -10.16, -2.54, 0))  # EN
    labels.append(label_pin("VIN", u4x, u4y, -10.16, 2.54, 0))  # IN
    labels.append(label_pin("GND", u4x, u4y, 0, -7.62, 90))
    labels.append(label_pin("SW", u4x, u4y, 10.16, 2.54, 180))
    labels.append(label_pin("BST", u4x, u4y, 10.16, 0, 180))

    parts.append(
        place_symbol(
            "Device:L",
            "L1",
            "4.7uH",
            "AdeptBT:L_6.3x6.3_H3",
            101.6,
            165.1,
            ["1", "2"],
        )
    )
    labels.append(label_pin("SW", 101.6, 165.1, 0, 3.81, 90))
    labels.append(label_pin("+5V", 101.6, 165.1, 0, -3.81, 270))

    # Buck caps (AP63205 DS / EVM)
    place_cap("C40", "10u", fp0805, "VIN", "GND", 63.5, 152.4)
    place_cap("C402", "100n", fp0402, "VIN", "GND", 68.58, 152.4)
    place_cap("C41", "22u", fp0805, "+5V", "GND", 101.6, 152.4)
    place_cap("C412", "22u", fp0805, "+5V", "GND", 106.68, 152.4)
    place_cap("C42", "100n", fp0402, "BST", "SW", 91.44, 152.4)

    # U6 AMS1117-3.3: 1 GND (0,-7.62), 2 VO (7.62,0), 3 VI (-7.62,0)
    u6x, u6y = 127.0, 165.1
    parts.append(
        place_symbol(
            "Regulator_Linear:AMS1117-3.3",
            "U6",
            "AMS1117-3.3",
            "AdeptBT:SOT-223-3_TabPin2",
            u6x,
            u6y,
            ["1", "2", "3"],
        )
    )
    labels.append(label_pin("GND", u6x, u6y, 0, -7.62, 90))
    labels.append(label_pin("+3V3", u6x, u6y, 7.62, 0, 180))
    labels.append(label_pin("+5V", u6x, u6y, -7.62, 0, 0))
    place_cap("C50", "10u", fp0805, "+5V", "GND", 119.38, 152.4)
    place_cap("C51", "22u", fp0805, "+3V3", "GND", 134.62, 152.4)

    # U5 MCP73871 — power path + PROG1; unused prog/therm tied per DS
    u5x, u5y = 165.1, 165.1
    mcp_pins = [str(i) for i in range(1, 22)]
    parts.append(
        place_symbol(
            "Battery_Management:MCP73871",
            "U5",
            "MCP73871",
            "AdeptBT:QFN-20-1EP_4x4mm_P0.5mm_EP2.5x2.5mm",
            u5x,
            u5y,
            mcp_pins,
        )
    )
    labels.append(label_pin("+5V", u5x, u5y, 0, 22.86, 270))  # IN
    labels.append(label_pin("GND", u5x, u5y, 0, -22.86, 90))  # VSS
    labels.append(label_pin("VBAT", u5x, u5y, 17.78, 7.62, 180))  # VBAT
    labels.append(label_pin("VBAT", u5x, u5y, 17.78, 2.54, 180))  # VBAT_SENSE
    labels.append(label_pin("+5V", u5x, u5y, 17.78, 15.24, 180))  # OUT
    labels.append(label_pin("CHG_STAT", u5x, u5y, 17.78, -10.16, 180))  # STAT1
    labels.append(label_pin("+5V", u5x, u5y, -17.78, -15.24, 0))  # CE high
    labels.append(label_pin("PROG1", u5x, u5y, -17.78, 5.08, 0))
    labels.append(label_pin("GND", u5x, u5y, -17.78, 10.16, 0))  # SEL=USB/AC low
    labels.append(label_pin("GND", u5x, u5y, -17.78, 2.54, 0))  # PROG2 off
    labels.append(label_pin("GND", u5x, u5y, -17.78, 0, 0))  # PROG3 off
    labels.append(label_pin("+5V", u5x, u5y, -17.78, -10.16, 0))  # ~TE high = timer en
    labels.append(label_pin("+5V", u5x, u5y, -17.78, 15.24, 0))  # VPCC
    labels.append(label_pin("GND", u5x, u5y, -17.78, -5.08, 0))  # THERM → GND (no NTC)
    labels.append(no_connect(*pin_xy(u5x, u5y, 17.78, -5.08)))  # ~PG
    labels.append(no_connect(*pin_xy(u5x, u5y, 17.78, -12.7)))  # STAT2
    # PROG1 ≈ 2kΩ → ~500 mA (IPROG≈1000/RPROG1)
    rpx, rpy = 134.62, 170.18
    parts.append(
        place_symbol(
            "Device:R",
            "RPROG1",
            "2k",
            "AdeptBT:R_0603_1608Metric",
            rpx,
            rpy,
            ["1", "2"],
        )
    )
    labels.append(global_label("PROG1", rpx, rpy - 3.81, 90, "passive"))
    labels.append(global_label("GND", rpx, rpy + 3.81, 270, "passive"))
    place_cap("C60", "4.7u", fp0805, "VBAT", "GND", 182.88, 142.24)
    place_cap("C61", "4.7u", fp0805, "+5V", "GND", 188.0, 142.24)

    # TMC sense Rs — 0.11Ω (common TMC2209 module; ~1 A RMS w/ VREF)
    fp_rs = "AdeptBT:R_1206_3216Metric"
    for ref, net, x, y in [
        ("RSA1", "BRA_1", 241.3, 88.9),
        ("RSB1", "BRB_1", 254.0, 88.9),
        ("RSA2", "BRA_2", 241.3, 152.4),
        ("RSB2", "BRB_2", 254.0, 152.4),
    ]:
        parts.append(
            place_symbol("Device:R", ref, "0.12", fp_rs, x, y, ["1", "2"])
        )
        labels.append(global_label(net, x, y - 3.81, 90, "passive"))
        labels.append(global_label("GND", x, y + 3.81, 270, "passive"))

    # ========== Discrete outs ==========
    # Q2 / Q3 NPN — pads 1=B, 2=E, 3=C; base via series R from MCU GPIO
    for ref, base_net, out, qx in [
        ("Q2", "OUT1_B", "OUT1", 38.1),
        ("Q3", "OUT2_B", "OUT2", 63.5),
    ]:
        qy = 215.9
        parts.append(
            place_symbol(
                "Device:Q_NPN",
                ref,
                "MMBT2222A",
                "Package_TO_SOT_SMD:SOT-23",
                qx,
                qy,
                ["1", "2", "3"],
            )
        )
        labels.append(label_pin(base_net, qx, qy, -5.08, 0, 0))  # B
        labels.append(label_pin(out, qx, qy, 2.54, 5.08, 90))  # C
        labels.append(label_pin("GND", qx, qy, 2.54, -5.08, 270))  # E

    # Flyback diodes (K toward V+, A toward OUT)
    for ref, net, x in [("D2", "OUT1", 38.1), ("D3", "OUT2", 63.5)]:
        dy = 241.3
        parts.append(
            place_symbol(
                "Device:D",
                ref,
                "1N4148W",
                "Diode_SMD:D_SOD-123",
                x,
                dy,
                ["1", "2"],
            )
        )
        labels.append(label_pin("V+", x, dy, -3.81, 0, 0))  # K
        labels.append(label_pin(net, x, dy, 3.81, 0, 180))  # A

    # Base resistors: MCU OUTn_DRV → Rn → OUTn_B → Q base
    for ref, drv, base, x in [
        ("R2", "OUT1_DRV", "OUT1_B", 25.4),
        ("R3", "OUT2_DRV", "OUT2_B", 50.8),
    ]:
        ry = 203.2
        parts.append(
            place_symbol(
                "Device:R",
                ref,
                "1k",
                "Resistor_SMD:R_0603_1608Metric",
                x,
                ry,
                ["1", "2"],
            )
        )
        labels.append(label_pin(drv, x, ry, 0, 3.81, 90))
        labels.append(label_pin(base, x, ry, 0, -3.81, 270))

    # Status LEDs — Device:LED pin1=K left, pin2=A right (refs must end in a digit).
    # PWR1: +3V3→A, K→R4→GND; CHG1: +3V3→A, K→R5→CHG_STAT (OC); USR1: LED_USER→A, K→R6→GND
    led_fp = "LED_SMD:LED_0603_1608Metric"
    r_fp = "Resistor_SMD:R_0603_1608Metric"
    for ref, value, anode, cathode_tail, lx in [
        ("PWR1", "PWR", "+3V3", "GND", 177.8),
        ("CHG1", "CHG", "+3V3", "CHG_STAT", 190.5),
        ("USR1", "USR", "LED_USER", "GND", 203.2),
    ]:
        ly = 241.3
        k_net = f"Net_{ref}_K"
        parts.append(
            place_symbol("Device:LED", ref, value, led_fp, lx, ly, ["1", "2"])
        )
        labels.append(label_pin(k_net, lx, ly, -3.81, 0, 0))  # K
        labels.append(label_pin(anode, lx, ly, 3.81, 0, 180))  # A
        rref = {"PWR1": "R4", "CHG1": "R5", "USR1": "R6"}[ref]
        ry = ly + 10.16
        parts.append(place_symbol("Device:R", rref, "1k", r_fp, lx, ry, ["1", "2"]))
        labels.append(label_pin(k_net, lx, ry, 0, 3.81, 90))
        labels.append(label_pin(cathode_tail, lx, ry, 0, -3.81, 270))

    # USB-C CC Rd 5.1k (UFP sink)
    for ref, net, x in [("RCC1", "CC1", 215.9), ("RCC2", "CC2", 228.6)]:
        ry = 241.3
        parts.append(
            place_symbol("Device:R", ref, "5.1k", r_fp, x, ry, ["1", "2"])
        )
        labels.append(label_pin(net, x, ry, 0, 3.81, 90))
        labels.append(label_pin("GND", x, ry, 0, -3.81, 270))

    # TMC VREF set resistors (placeholder; tune for motor current)
    for ref, net, x, y in [
        ("RVREF1", "VREF_1", 266.7, 101.6),
        ("RVREF2", "VREF_2", 266.7, 165.1),
    ]:
        parts.append(
            place_symbol("Device:R", ref, "10k", r_fp, x, y, ["1", "2"])
        )
        labels.append(label_pin(net, x, y, 0, 3.81, 90))
        labels.append(label_pin("GND", x, y, 0, -3.81, 270))

    # Power symbols + PWR_FLAG (pin at instance origin)
    pwr_refs = [
        ("#PWR01", "power:GND", "GND", 25.4, 254.0),
        ("#PWR02", "power:+3V3", "+3V3", 38.1, 254.0),
        ("#PWR03", "power:+5V", "+5V", 50.8, 254.0),
    ]
    for ref, lib, net, x, y in pwr_refs:
        parts.append(place_symbol(lib, ref, net, "", x, y, ["1"]))
        labels.append(global_label(net, x, y, 0, "input"))
    # PWR_FLAG only on nets without a regulator Power-output pin (else pin_to_pin).
    for i, (net, x) in enumerate(
        [("GND", 63.5), ("VIN", 76.2), ("USB_5V", 88.9), ("VIN_RAW", 101.6)],
        start=1,
    ):
        y = 266.7
        parts.append(
            place_symbol("power:PWR_FLAG", f"#FLG{i:02d}", "PWR_FLAG", "", x, y, ["1"])
        )
        labels.append(global_label(net, x, y, 0, "input"))

    notes = text_block(
        "AdeptBT rev 0.12 — JLCPCB-first schematic\\n"
        "MCU U1 Raytac MDBT50Q-1MV2  |  U2/U3 TMC2209-LA  |  U4 AP63205  |  U5 MCP73871  |  U6 AMS1117\\n"
        "Power: VIN_RAW→F1 PPTC→Q1 AO3407→D1 SMBJ24A→VIN→buck→+5V→LDO→+3V3; charger on +5V/VBAT\\n"
        "Jumpers JP_V+1 (3V3/V+/VIN), JP_VM1/2 (VIN/VM); holes M1–M4; CC Rd 5.1k\\n"
        "GPIO lock: AIN0-3=P0.02-05; OUT1/2=P0.06/08; TMC_UART=P0.14; CHG_STAT=P0.25",
        20,
        10,
        1.4,
    )

    # Fix MCU OUT labels: re-emit note that OUT1/OUT2 on MCU are GPIO (drive bases)
    # Replace earlier left_map OUT1/OUT2 — already placed; add legend

    body = "\n".join([notes] + parts + labels)

    sch = f"""(kicad_sch
\t(version 20260306)
\t(generator "gen_adeptbt_sch")
\t(generator_version "0.12")
\t(uuid "{SHEET_UUID}")
\t(paper "A2")
\t(title_block
\t\t(title "AdeptBT")
\t\t(date "2026-11-23")
\t\t(rev "0.12")
\t\t(company "coconnor55")
\t\t(comment 1 "JLCPCB: Raytac C5118826, TMC C465949, TE C3816695, MCP73871 C5121473, AP63205 C2071056")
\t\t(comment 2 "Power path + sense Rs; CC Rd; stackup docs/STACKUP.md")
\t)
\t(lib_symbols
{lib_syms}
\t)
{body}
\t(sheet_instances
\t\t(path "/"
\t\t\t(page "1")
\t\t)
\t)
\t(embedded_fonts no)
)
"""
    OUT.write_text(sch)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
