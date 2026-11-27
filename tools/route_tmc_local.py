#!/usr/bin/env python3
"""Place + short-route the TMC2209 neighborhoods (U2 / U3), then lock copper.

Hand-equivalent stubs Freerouting tends to convolute: sense, VS ceramic,
charge-pump, VCP, 5VOUT, VCC_IO, VREF, EP thermal vias, and nearby GND vias.
Bulk electrolytics (C15/C25) are nudged only slightly; long VM/coil runs are
left for Freerouting.

Idempotent: tracks/vias this script creates are locked. Re-run with the
default --replace to rip only locked copper, then rebuild.

Must run with KiCad's Python (pcbnew):

  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \\
    tools/route_tmc_local.py

Options:
  --dry-run     print targets / connections, do not write
  --no-replace  keep existing locked copper (add only)
  --no-bump     do not increment PCB rev
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PCB = ROOT / "hardware" / "adeptbt.kicad_pcb"

# Track widths (mm) by net role — BRA/BRB carry phase current to Rsense.
W_HV = 0.8
W_SENSE = 0.25
W_LV = 0.4
W_SIG = 0.25
# QFN west pads are 0.5 mm pitch — leave them necked or adjacent nets short.
W_EXIT = 0.2
EXIT_MM = 1.8  # clear package before widening / turning

VIA_DRILL = 0.3
VIA_DIA = 0.6
EP_VIA_DRILL = 0.3
EP_VIA_DIA = 0.5

# Absolute placement targets (x, y, ang_deg) — minimal nudges vs east-VCP layout.
# U2/U3 stay put; satellites move only to shorten pad→pad stubs.
# U2 @−90: coil edge north toward J_STEP1; sense on NE/NW flanks.
PLACE = {
    # Synced to user board (2026-11-26 16:11). Do not invent coords.
    "U2": (66.287, 19.5, -90.0),
    "U3": (73.0, 34.75, 90.0),
    "RSA1": (73.037, 15.25, 0.0),
    "RSB1": (61.288, 15.5, 180.0),
    "RSA2": (67.75, 39.0, 180.0),
    "RSB2": (77.5, 40.25, 0.0),
    "C14": (72.267, 17.0, 0.0),
    "C15": (80.325, 18.75, 90.0),
    "C24": (77.5, 38.25, 0.0),
    "C25": (61.25, 34.0, 90.0),
    "C10": (59.538, 19.75, -90.0),
    "C11": (59.538, 22.25, 0.0),
    "C20": (80.0, 35.0, 90.0),
    "C21": (77.5, 37.0, 180.0),
    "C12": (63.538, 24.75, 180.0),
    "C13": (72.787, 21.25, 0.0),
    "C22": (77.25, 30.5, 0.0),
    "C23": (73.5, 30.0, 180.0),
    "RVREF1": (73.287, 19.75, 0.0),
    "RVREF2": (67.0, 33.25, 180.0),
}

# (ref_a, pad_a, ref_b, pad_b, width_mm) — pad-to-pad short runs on F.Cu
# One VM stub per ceramic/bulk (not both VS pins) to avoid fat copper under the QFN.
CONNECTIONS = [
    # U2 sense / VS / pump / VCP / regs / VREF
    ("U2", "23", "RSA1", "1", W_SENSE),
    ("U2", "27", "RSB1", "1", W_SENSE),
    ("U2", "22", "C14", "1", W_HV),
    ("U2", "4", "C10", "1", W_SIG),
    ("U2", "5", "C10", "2", W_SIG),
    ("U2", "6", "C11", "1", W_SIG),
    ("U2", "28", "C11", "2", W_HV),  # VCP return to south VM — not via C14/C10
    ("U2", "8", "C12", "1", W_LV),
    ("U2", "15", "C13", "1", W_LV),
    ("U2", "17", "RVREF1", "1", W_SIG),
    # Bulk @+90: VM pad is south — tie to south VS pin, not C14 (north)
    ("U2", "28", "C15", "1", W_HV),
    # U3
    ("U3", "23", "RSA2", "1", W_SENSE),
    ("U3", "27", "RSB2", "1", W_SENSE),
    ("U3", "22", "C24", "1", W_HV),
    ("U3", "4", "C20", "1", W_SIG),
    ("U3", "5", "C20", "2", W_SIG),
    ("U3", "6", "C21", "1", W_SIG),
    ("U3", "28", "C21", "2", W_HV),
    ("U3", "8", "C22", "1", W_LV),
    ("U3", "15", "C23", "1", W_LV),
    ("U3", "17", "RVREF2", "1", W_SIG),
    ("U3", "28", "C25", "1", W_HV),
]

# GND via next to (ref, pad) — offset mm in board XY from pad center.
# Keep clear of 0.5–0.8 mm local tracks (no vias on QFN edge pins).
GND_VIA_AT = [
    # Sense @180: GND pad is west — via further west
    ("RSA1", "2", -1.2, 0.0),
    ("RSB1", "2", -1.2, 0.0),
    ("RSA2", "2", -1.2, 0.0),
    ("RSB2", "2", -1.2, 0.0),
    # C14/C24 @+90: GND pad is north — via further north
    ("C14", "2", 0.0, -1.2),
    ("C24", "2", 0.0, -1.2),
    # east of GND pads (away from IC / power pin)
    ("C12", "2", 1.2, 0.0),
    ("C13", "2", 1.2, 0.0),
    ("C22", "2", 1.2, 0.0),
    ("C23", "2", 1.2, 0.0),
    ("RVREF1", "2", 0.0, -1.2),
    ("RVREF2", "2", 0.0, -1.2),
    # C15/C25 @+90: GND pad is north — via further north
    ("C15", "2", 0.0, -1.6),
    ("C25", "2", 0.0, -1.6),
]

# EP thermal via grid offsets from U2/U3 origin (pad 29 center) — 1 mm pitch
EP_VIA_OFFSETS = [
    (-0.9, -0.9),
    (0.9, -0.9),
    (-0.9, 0.9),
    (0.9, 0.9),
]


def mm(x: float) -> int:
    import pcbnew

    return int(pcbnew.FromMM(x))


def to_mm(v) -> float:
    import pcbnew

    return float(pcbnew.ToMM(v))


def bump_rev(path: Path) -> str:
    text = path.read_text()
    m = re.search(r'\(rev "([0-9]+)\.([0-9]+)"\)', text)
    if not m:
        return "?"
    new = f"{int(m.group(1))}.{int(m.group(2)) + 1}"
    text = text.replace(f'(rev "{m.group(1)}.{m.group(2)}")', f'(rev "{new}")', 1)
    text = re.sub(
        r'\(gr_text "AdeptBT rev [0-9.]+"',
        f'(gr_text "AdeptBT rev {new}"',
        text,
        count=1,
    )
    path.write_text(text)
    return new


def pad_xy(board, ref: str, pad_num: str):
    import pcbnew

    fp = board.FindFootprintByReference(ref)
    if fp is None:
        raise KeyError(f"missing footprint {ref}")
    for pad in fp.Pads():
        if pad.GetNumber() == pad_num:
            p = pad.GetPosition()
            return to_mm(p.x), to_mm(p.y), pad
    raise KeyError(f"{ref} pad {pad_num}")


def set_fp(board, ref: str, x: float, y: float, ang: float) -> None:
    import pcbnew

    fp = board.FindFootprintByReference(ref)
    if fp is None:
        raise KeyError(f"missing footprint {ref}")
    fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    fp.SetOrientationDegrees(ang)


def clear_locked_copper(board) -> tuple[int, int]:
    doomed = [t for t in board.GetTracks() if t.IsLocked()]
    for t in doomed:
        board.Remove(t)
    # vias are in GetTracks() in KiCad 6+
    return len(doomed), 0


def add_seg(board, x1, y1, x2, y2, width, net, locked=True):
    import pcbnew

    if abs(x1 - x2) < 1e-4 and abs(y1 - y2) < 1e-4:
        return 0
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
    t.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
    t.SetWidth(mm(width))
    t.SetLayer(pcbnew.F_Cu)
    t.SetNet(net)
    if locked:
        t.SetLocked(True)
    board.Add(t)
    return 1


def add_manhattan(board, x1, y1, x2, y2, width, net, locked=True) -> int:
    """F.Cu prefer horizontal first, then vertical (board H/V convention)."""
    n = 0
    if abs(x1 - x2) < 1e-4 or abs(y1 - y2) < 1e-4:
        return add_seg(board, x1, y1, x2, y2, width, net, locked)
    n += add_seg(board, x1, y1, x2, y1, width, net, locked)
    n += add_seg(board, x2, y1, x2, y2, width, net, locked)
    return n


def add_from_qfn_west(board, x1, y1, x2, y2, width, net, locked=True) -> int:
    """Necked leave from west QFN pad, then to target (sense / thin nets)."""
    n = 0
    x_exit = x1 - EXIT_MM
    n += add_seg(board, x1, y1, x_exit, y1, W_EXIT, net, locked)
    if abs(y2 - y1) > 1e-4:
        n += add_seg(board, x_exit, y1, x_exit, y2, W_EXIT, net, locked)
    n += add_seg(board, x_exit, y2, x2, y2, width, net, locked)
    return n


def add_bulk_vm_south(board, x_ic, y_ic, x_cap, y_cap, width, net, locked=True) -> int:
    """IC west VM → bulk: necked exit, then fat run at bulk-pad Y (south)."""
    n = 0
    x_exit = x_ic - EXIT_MM
    y_run = y_cap
    n += add_seg(board, x_ic, y_ic, x_exit, y_ic, W_EXIT, net, locked)
    n += add_seg(board, x_exit, y_ic, x_exit, y_run, W_EXIT, net, locked)
    n += add_seg(board, x_exit, y_run, x_cap, y_run, width, net, locked)
    return n


def add_ceramic_vm_from_ic(board, x_ic, y_ic, x_cap, y_cap, width, net, locked=True) -> int:
    """C14/C24 @+90: pad1 VM faces IC — enter from south only (never past into GND)."""
    n = 0
    x_exit = x_ic - EXIT_MM
    n += add_seg(board, x_ic, y_ic, x_exit, y_ic, W_EXIT, net, locked)
    n += add_seg(board, x_exit, y_ic, x_exit, y_cap, W_EXIT, net, locked)
    n += add_seg(board, x_exit, y_cap, x_cap, y_cap, width, net, locked)
    return n


def add_vm_around_south(board, x_ic, y_ic, x_cap, y_cap, width, net, locked=True) -> int:
    """West VM pad → SE part (C11/C21): necked west, south, east — not through QFN."""
    n = 0
    x_exit = x_ic - EXIT_MM
    y_south = max(y_ic + 1.5, y_cap)
    n += add_seg(board, x_ic, y_ic, x_exit, y_ic, W_EXIT, net, locked)
    n += add_seg(board, x_exit, y_ic, x_exit, y_south, W_EXIT, net, locked)
    n += add_seg(board, x_exit, y_south, x_cap, y_south, width, net, locked)
    if abs(y_south - y_cap) > 1e-4:
        n += add_seg(board, x_cap, y_south, x_cap, y_cap, width, net, locked)
    return n


def add_via(board, x, y, net, drill=VIA_DRILL, dia=VIA_DIA, locked=True) -> int:
    import pcbnew

    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    v.SetDrill(mm(drill))
    v.SetWidth(mm(dia))
    v.SetNet(net)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    if locked:
        v.SetLocked(True)
    board.Add(v)
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-replace", action="store_true")
    ap.add_argument("--no-bump", action="store_true")
    args = ap.parse_args()

    try:
        import pcbnew
    except ImportError:
        print(
            "Need KiCad Python with pcbnew. Run:\n"
            "  /Applications/KiCad/KiCad.app/Contents/Frameworks/"
            "Python.framework/Versions/Current/bin/python3 tools/route_tmc_local.py",
            file=sys.stderr,
        )
        return 2

    if not PCB.exists():
        print(f"missing {PCB}", file=sys.stderr)
        return 1

    board = pcbnew.LoadBoard(str(PCB))
    gnd = board.FindNet("GND")
    if gnd is None or gnd.GetNetCode() <= 0:
        print("GND net missing — update PCB from schematic first", file=sys.stderr)
        return 1

    if args.dry_run:
        for ref, (x, y, ang) in sorted(PLACE.items()):
            print(f"PLACE {ref:8} → ({x:.3f}, {y:.3f}) ang={ang:g}")
        for a, pa, b, pb, w in CONNECTIONS:
            print(f"CONN  {a}.{pa} ↔ {b}.{pb}  w={w}")
        print(f"GND vias={len(GND_VIA_AT)}  EP vias/IC={len(EP_VIA_OFFSETS)}")
        return 0

    replace = not args.no_replace
    cleared = 0
    if replace:
        cleared, _ = clear_locked_copper(board)

    moved = 0
    for ref, (x, y, ang) in PLACE.items():
        set_fp(board, ref, x, y, ang)
        moved += 1

    # Rebuild connectivity after moves
    if hasattr(board, "BuildConnectivity"):
        board.BuildConnectivity()

    segs = 0
    west_pads = {"22", "23", "24", "26", "27", "28"}
    bulk_south = {("U2", "28", "C15", "1"), ("U3", "28", "C25", "1")}
    ceramic_ic = {("U2", "22", "C14", "1"), ("U3", "22", "C24", "1")}
    vm_se = {("U2", "28", "C11", "2"), ("U3", "28", "C21", "2")}
    for a, pa, b, pb, w in CONNECTIONS:
        x1, y1, pada = pad_xy(board, a, pa)
        x2, y2, padb = pad_xy(board, b, pb)
        net = pada.GetNet()
        if net is None or net.GetNetCode() <= 0:
            net = padb.GetNet()
        if net is None or net.GetNetCode() <= 0:
            print(f"skip {a}.{pa}-{b}.{pb}: no net", file=sys.stderr)
            continue
        if (a, pa, b, pb) in bulk_south:
            segs += add_bulk_vm_south(board, x1, y1, x2, y2, w, net, locked=True)
        elif (a, pa, b, pb) in ceramic_ic:
            segs += add_ceramic_vm_from_ic(board, x1, y1, x2, y2, w, net, locked=True)
        elif (a, pa, b, pb) in vm_se:
            segs += add_vm_around_south(board, x1, y1, x2, y2, w, net, locked=True)
        elif a in ("U2", "U3") and pa in west_pads:
            segs += add_from_qfn_west(board, x1, y1, x2, y2, w, net, locked=True)
        else:
            segs += add_manhattan(board, x1, y1, x2, y2, w, net, locked=True)

    vias = 0
    # Via next to GND pad + short dogbone (no pour yet — vias alone look disconnected)
    for ref, pad_num, dx, dy in GND_VIA_AT:
        x, y, _ = pad_xy(board, ref, pad_num)
        vx, vy = x + dx, y + dy
        vias += add_via(board, vx, vy, gnd)
        segs += add_seg(board, x, y, vx, vy, W_SIG, gnd, locked=True)

    for uref in ("U2", "U3"):
        ux, uy, _ = pad_xy(board, uref, "29")
        for dx, dy in EP_VIA_OFFSETS:
            vias += add_via(
                board, ux + dx, uy + dy, gnd, drill=EP_VIA_DRILL, dia=EP_VIA_DIA
            )

    pcbnew.SaveBoard(str(PCB), board)
    rev = "?" if args.no_bump else bump_rev(PCB)
    print(
        f"route_tmc_local: moved={moved} cleared_locked={cleared} "
        f"segs={segs} vias={vias} rev={rev} → {PCB}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
