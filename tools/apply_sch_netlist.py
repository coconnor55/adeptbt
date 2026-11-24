#!/usr/bin/env python3
"""Apply schematic netlist nets onto hardware/adeptbt.kicad_pcb (by reference + pad).

Requires KiCad's bundled Python (pcbnew). Does not move footprints.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCH = ROOT / "hardware" / "adeptbt.kicad_sch"
PCB = ROOT / "hardware" / "adeptbt.kicad_pcb"
NET = ROOT / "hardware" / "exports" / "adeptbt.net"


def parse_nets(netlist: str) -> dict[str, list[tuple[str, str]]]:
    """net name -> [(ref, pin), ...]"""
    out: dict[str, list[tuple[str, str]]] = {}
    for m in re.finditer(
        r'\(net\s+\(code "[^"]*"\)\s+\(name "([^"]*)"\)([\s\S]*?)(?=\n\t\t\(net|\n\t\))',
        netlist,
    ):
        name = m.group(1)
        body = m.group(2)
        nodes = re.findall(r'\(ref "([^"]+)"\)\s+\(pin "([^"]+)"\)', body)
        if name and nodes:
            out[name] = nodes
    return out


# Sch pin → footprint pad(s). SOT-23 AO3407 G/S/D=1/2/3; MMBT2222 B/E/C=1/2/3.
# J_USB1 sch pins match GCT pad names 1:1 (USB_C_GCT_16P); no fan-out aliases.
PAD_ALIASES: dict[str, dict[str, list[str]]] = {
    # Q symbols use numeric pins 1/2/3 (aliases kept for older netlists).
    "Q1": {"G": ["1"], "S": ["2"], "D": ["3"], "1": ["1"], "2": ["2"], "3": ["3"]},
    "Q2": {"B": ["1"], "E": ["2"], "C": ["3"], "1": ["1"], "2": ["2"], "3": ["3"]},
    "Q3": {"B": ["1"], "E": ["2"], "C": ["3"], "1": ["1"], "2": ["2"], "3": ["3"]},
}


def resolve_pads(ref: str, pin: str) -> list[str]:
    return PAD_ALIASES.get(ref, {}).get(pin, [pin])


def main() -> int:
    NET.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        [
            "kicad-cli",
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadsexpr",
            "-o",
            str(NET),
            str(SCH),
        ],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(r.stderr or r.stdout, file=sys.stderr)
        return r.returncode
    if "Failed to load schematic" in (r.stderr + r.stdout):
        print(r.stderr or r.stdout, file=sys.stderr)
        return 1
    if r.stderr.strip():
        print(r.stderr.strip())

    nets = parse_nets(NET.read_text())
    print(f"netlist: {len(nets)} nets from {NET}")

    import pcbnew  # KiCad bundled interpreter only

    board = pcbnew.LoadBoard(str(PCB))
    by_ref = {fp.GetReference(): fp for fp in board.GetFootprints()}

    net_items: dict[str, object] = {}
    assigned = 0
    missing_fp = 0
    missing_pad = 0

    for name, nodes in nets.items():
        if name not in net_items:
            ni = pcbnew.NETINFO_ITEM(board, name)
            board.Add(ni)
            net_items[name] = ni
        ni = net_items[name]
        for ref, pin in nodes:
            fp = by_ref.get(ref)
            if fp is None:
                missing_fp += 1
                continue
            pads = resolve_pads(ref, pin)
            found_any = False
            for pad_num in pads:
                pad = fp.FindPadByNumber(pad_num)
                if pad is None:
                    continue
                pad.SetNet(ni)
                assigned += 1
                found_any = True
            if not found_any:
                missing_pad += 1
                print(f"  no pad {ref}.{pin}->{pads} for net {name}")

    board.BuildConnectivity()
    board.Save(str(PCB))
    print(
        f"assigned {assigned} pad nets; missing_fp={missing_fp} missing_pad={missing_pad}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
