#!/usr/bin/env python3
"""Generate AdeptBT schematic (rev 0.3) — symbols + global labels from NETLIST."""

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
                # Rewrite as LibName:Symbol for embedding
                return block
        i += 1
    raise RuntimeError(f"unclosed symbol {name}")


def embed_as(lib_id: str, block: str) -> str:
    """Rename outer (symbol "Name") to Lib:Name; leave unit child names short."""
    block = block.lstrip()
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


def global_label(name: str, x: float, y: float, angle: float = 0, shape: str = "input") -> str:
    return f"""\t(global_label "{name}"
\t\t(shape {shape})
\t\t(at {x} {y} {angle:g})
\t\t(fields_autoplaced yes)
\t\t(effects
\t\t\t(font
\t\t\t\t(size 1.27 1.27)
\t\t\t)
\t\t\t(justify left)
\t\t)
\t\t(uuid "{uid()}")
\t\t(property "Intersheetrefs" "${{INTERSHEET_REFS}}"
\t\t\t(at {x} {y} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(hide yes)
\t\t\t)
\t\t)
\t)"""


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
CONN_Y0 = {2: 0.0, 5: 5.08, 6: 5.08, 7: 7.62}


def label_conn_row(nets: list[str], x: float, y: float) -> list[str]:
    """Labels on Connector_Generic left pin tips (pitch 2.54)."""
    out = []
    y0 = CONN_Y0[len(nets)]
    px = x - 5.08
    for i, net in enumerate(nets):
        # KiCad sheet Y: negate library pin Y for correct binding
        out.append(global_label(net, px, y - y0 + i * 2.54, 0, "input"))
    return out


def main() -> None:
    # --- library symbols ---
    conn_lib = KICAD_SYM / "Connector_Generic.kicad_sym"
    connector_lib = KICAD_SYM / "Connector.kicad_sym"
    device_lib = KICAD_SYM / "Device.kicad_sym"
    power_lib = KICAD_SYM / "power.kicad_sym"

    needed = [
        ("jlc:MDBT50Q-1MV2", extract_symbol(JLC_SYM, "MDBT50Q-1MV2")),
        ("jlc:TMC2209-LA", extract_symbol(JLC_SYM, "TMC2209-LA")),
        ("Connector_Generic:Conn_01x06", extract_symbol(conn_lib, "Conn_01x06")),
        ("Connector_Generic:Conn_01x07", extract_symbol(conn_lib, "Conn_01x07")),
        ("Connector_Generic:Conn_01x05", extract_symbol(conn_lib, "Conn_01x05")),
        ("Connector_Generic:Conn_01x02", extract_symbol(conn_lib, "Conn_01x02")),
        ("Connector:Barrel_Jack", extract_symbol(connector_lib, "Barrel_Jack")),
        ("Device:Q_NPN", extract_symbol(device_lib, "Q_NPN")),
        ("Device:D", extract_symbol(device_lib, "D")),
        ("Device:R", extract_symbol(device_lib, "R")),
        ("Device:C", extract_symbol(device_lib, "C")),
        ("Device:LED", extract_symbol(device_lib, "LED")),
        ("power:GND", extract_symbol(power_lib, "GND")),
        ("power:+3V3", extract_symbol(power_lib, "+3V3")),
        ("power:+5V", extract_symbol(power_lib, "+5V")),
    ]

    lib_syms = "\n".join(embed_as(lid, blk) for lid, blk in needed)

    parts: list[str] = []
    labels: list[str] = []

    # All coords on 1.27 mm schematic grid
    cy = 25.4
    connectors = [
        ("J_STEP1", "STEPPER1", "AdeptBT:TE_2383945-6_1x06_P3.81mm_SMD", 25.4,
         ["A1_1", "A2_1", "B1_1", "B2_1", "VM1", "GND"], 6),
        ("J_STEP2", "STEPPER2", "AdeptBT:TE_2383945-6_1x06_P3.81mm_SMD", 50.8,
         ["A1_2", "A2_2", "B1_2", "B2_2", "VM2", "GND"], 6),
        ("J_PWR", "PWR_OUT", "AdeptBT:TE_2383945-6_1x06_P3.81mm_SMD", 76.2,
         ["VIN_RAW", "GND", "V+", "OUT1", "V+", "OUT2"], 6),
        # TE footprint file name unchanged (same 3.81 mm geometry); value TE 2383941-6
        ("J_AN", "ANALOG", "AdeptBT:PinHeader_1x07_P2.54mm_Vertical", 101.6,
         ["AIN0", "AIN1", "AIN2", "AIN3", "+3V3", "+5V", "GND"], 7),
        ("J_DG", "DIGITAL", "AdeptBT:PinHeader_1x06_P2.54mm_Vertical", 127.0,
         ["D0", "D1", "D2", "D3", "+3V3", "GND"], 6),
        ("J_SWD", "SWD", "AdeptBT:PinHeader_1x05_P2.54mm_Vertical", 152.4,
         ["SWDIO", "SWDCLK", "GND", "+3V3", "nRESET"], 5),
        ("J_BAT", "BAT", "AdeptBT:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal", 177.8,
         ["VBAT", "GND"], 2),
        ("J_USB", "USB-C", "AdeptBT:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal", 203.2,
         ["USB_5V", "USB_D+", "USB_D-", "CC1", "CC2", "GND"], 6),
    ]
    for ref, val, fp, x, nets, n in connectors:
        if ref == "J_PWR":
            val = "TE_2383941-6"
        if ref.startswith("J_STEP"):
            val = "TE_2383941-6"
        lib = f"Connector_Generic:Conn_01x{n:02d}"
        parts.append(place_symbol(lib, ref, val, fp, x, cy, conn_pins(n)))
        labels += label_conn_row(nets, x, cy)

    # J_DC 5.5×2.1 barrel — pin1 tip=VIN_RAW, pin2 sleeve=GND (Y negated)
    dc_x, dc_y = 228.6, 25.4
    parts.append(
        place_symbol(
            "Connector:Barrel_Jack",
            "J_DC",
            "5.5x2.1",
            "AdeptBT:BarrelJack_CUI_PJ-063AH_Horizontal",
            dc_x,
            dc_y,
            ["1", "2"],
        )
    )
    labels.append(global_label("VIN_RAW", dc_x + 7.62, dc_y - 2.54, 180, "output"))
    labels.append(global_label("GND", dc_x + 7.62, dc_y + 2.54, 180, "output"))

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

    right_map = {
        32: "USB_5V",  # VBUS
        33: "GND",
        34: "USB_D-",
        35: "USB_D+",
        36: "TMC_UART",  # P0.14 shared UART
        37: "STEP1_EN",  # P0.13
        38: "STEP2_STEP",  # P0.16
        39: "STEP1_DIR",  # P0.15 — wait remap below
        40: "nRESET",  # P0.18
        41: "STEP2_EN",  # P0.17
        42: "STEP2_DIR",  # P0.19
        43: "STEP1_STEP",  # P0.21
        44: "STEP1_DIR",  # P0.20 — fix conflicts: use clean map
        45: "D0",  # P0.23 — will override with clean map
        46: "D1",  # P0.22
        47: "D2",  # P1.00
        48: "D3",  # P0.24
        49: "CHG_STAT",  # P0.25
        51: "SWDIO",
        53: "SWDCLK",
        55: "GND",
    }
    # Clean GPIO lock (override right_map carefully):
    # P0.11 pin27 TRACEDATA2 — left bank
    # Remap using documented lock — place labels by pin number from datasheet map:
    gpio_lock = {
        # Right bank pin numbers from symbol extract
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
    # From extract: 32 at -38.1, 33 at -35.56, ... so y = -38.1 + (n-32)*2.54
    for n, net in gpio_lock.items():
        lib_y = -38.1 + (n - 32) * 2.54
        px = mcu_x + 31.75
        labels.append(global_label(net, px, mcu_y - lib_y, 180, "output"))

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
        left = {
            1: f"B2_{suffix}",  # OB2
            2: f"STEP{suffix}_EN",
            3: "GND",
            8: "+5V",  # 5VOUT decouple net (local)
            9: f"MS1_{suffix}",
            10: f"MS2_{suffix}",
            13: "GND",  # CLK → GND for internal osc
            14: "TMC_UART",
            15: "+3V3",
        }
        for n, net in left.items():
            lib_y = 17.78 - (n - 1) * 2.54
            labels.append(global_label(net, x - 15.24, y - lib_y, 0, "input"))
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

    place_tmc("U2", 203.2, 114.3, "1")
    place_tmc("U3", 203.2, 177.8, "2")

    # ========== Discrete outs ==========
    # Q2 / Q3 NPN
    for ref, base, out in [("Q2", "OUT1", "OUT1"), ("Q3", "OUT2", "OUT2")]:
        # OUT nets: base driven via R from GPIO; collector is open-drain OUT
        # Use separate net names for clarity: GPIO OUT1 drives base through R
        pass

    # Device:Q_NPN pin numbers are B/C/E
    for ref, drv, out, qx in [
        ("Q2", "OUT1_DRV", "OUT1", 38.1),
        ("Q3", "OUT2_DRV", "OUT2", 63.5),
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
                ["B", "C", "E"],
            )
        )
        labels.append(global_label(drv, qx - 5.08, qy, 0, "input"))  # B
        labels.append(global_label(out, qx + 2.54, qy - 5.08, 90, "passive"))  # C
        labels.append(global_label("GND", qx + 2.54, qy + 5.08, 270, "passive"))  # E

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
        labels.append(global_label("V+", x - 3.81, dy, 0, "passive"))  # K
        labels.append(global_label(net, x + 3.81, dy, 180, "passive"))  # A

    # Base resistors on same net as MCU GPIO (series placeholder for GUI polish)
    for ref, net, x in [("R2", "OUT1_DRV", 25.4), ("R3", "OUT2_DRV", 50.8)]:
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
        labels.append(global_label(net, x, ry - 3.81, 90, "passive"))
        labels.append(global_label(net, x, ry + 3.81, 270, "passive"))

    # Power flags
    pwr_refs = [
        ("#PWR01", "power:GND", "GND", 25.4, 254.0),
        ("#PWR02", "power:+3V3", "+3V3", 38.1, 254.0),
        ("#PWR03", "power:+5V", "+5V", 50.8, 254.0),
    ]
    for ref, lib, net, x, y in pwr_refs:
        parts.append(place_symbol(lib, ref, net, "", x, y, ["1"]))
        if net == "GND":
            labels.append(global_label(net, x, y + 2.54, 270, "input"))
        else:
            labels.append(global_label(net, x, y - 2.54, 90, "input"))

    notes = text_block(
        "AdeptBT rev 0.3 — JLCPCB-first schematic\\n"
        "MCU U1 Raytac MDBT50Q-1MV2 (C5118826)  |  U2/U3 TMC2209-LA (C465949)\\n"
        "J_STEP1/2 + J_PWR: TE 2383941-6 (C3816695)  |  J_DC: 5.5x2.1 barrel\\n"
        "GPIO lock: AIN0-3=P0.02-05; OUT1/2=P0.06/08; shared TMC_UART=P0.14;\\n"
        "  STEP1 STEP/DIR/EN=P0.21/20/13; STEP2 STEP/DIR/EN=P0.16/15/17;\\n"
        "  D0-3=P0.23/22/P1.00/P0.24; LED=P0.07; CHG_STAT=P0.25\\n"
        "Power: VIN_RAW (screw+barrel)→PPTC→P-FET→SMBJ24A→VIN; buck AP63205;\\n"
        "  MCP73871→VBAT; AMS1117→+3V3. Finish discretes in KiCad.",
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
\t(generator_version "0.3")
\t(uuid "{SHEET_UUID}")
\t(paper "A2")
\t(title_block
\t\t(title "AdeptBT")
\t\t(date "2026-11-22")
\t\t(rev "0.3")
\t\t(company "coconnor55")
\t\t(comment 1 "JLCPCB: Raytac C5118826, TMC C465949, TE C3816695, MCP73871 C5121473")
\t\t(comment 2 "VIN to 18V → SMBJ24A; J_DC 5.5x2.1 on VIN_RAW")
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
