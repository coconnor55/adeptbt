#!/usr/bin/env python3
"""Assign GND, pour solid inner planes + outer pours, stitch vias, fill.

Must run with KiCad's Python (pcbnew), not system Python:

  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \\
    tools/pour_gnd.py

Owner: docs/STACKUP.md
"""

from __future__ import annotations

import sys
from pathlib import Path

from board_geom import BOARD_OX, BOARD_OY, BOARD_W, BOARD_H

ROOT = Path(__file__).resolve().parents[1]
PCB = ROOT / "hardware" / "adeptbt.kicad_pcb"
W, H = BOARD_W, BOARD_H

# Stitch vias near decoupling clusters (fab mm + sheet origin) — keep clear of pads.
STITCH_XY = [
    (BOARD_OX + x, BOARD_OY + y)
    for x, y in (
        (14.0, 40.0),  # U1 3V3
        (10.0, 28.0),  # USB
        (65.0, 20.0),  # U2 ceramics
        (65.0, 34.0),  # U3 ceramics
        (76.0, 32.0),  # VS bulk C15
        (60.0, 27.0),  # VS bulk C25
        (16.0, 22.0),  # C31 bulk
        (30.0, 26.0),  # power protect / F1
        (22.0, 34.0),  # U4 buck
        (42.0, 44.0),  # U6 LDO
        (40.0, 28.0),  # U5 charger
        (22.0, 40.0),  # SWD
        (56.0, 28.0),  # sense
    )
]

# Antenna keepout — fab-relative + sheet origin (south of U1 pads; x≤20.5 clears J_SWD)
ANT_KEEP = (
    BOARD_OX + 7.5,
    BOARD_OY + 50.5,
    BOARD_OX + 20.5,
    BOARD_OY + 53.8,
)


def mm(x: float) -> int:
    import pcbnew

    return pcbnew.FromMM(x)


def ensure_gnd(board):
    import pcbnew

    gnd = board.FindNet("GND")
    if gnd is None or gnd.GetNetCode() <= 0:
        gnd = pcbnew.NETINFO_ITEM(board, "GND")
        board.Add(gnd)
        gnd = board.FindNet("GND")
    return gnd


def assign_gnd_pads(board, gnd) -> int:
    """Fill only unassigned pads that are clearly GND. Never overwrite a named net.

    Charge-pump / VCP caps (C10/C11/C20/C21) have pin 2 on CPI/VM — not GND.
    """
    n = 0
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        for pad in fp.Pads():
            existing = pad.GetNetname() or ""
            if existing and existing != "GND":
                continue
            num = pad.GetNumber()
            use = False
            if ref.startswith("H") or ref.startswith("M"):
                use = True
            elif ref in ("J_STEP1", "J_STEP2") and num == "6":
                use = True
            elif ref in ("J_PWR", "J_PWR1") and num == "2":
                use = True
            elif ref in ("J_AN", "J_AN1") and num == "7":
                use = True
            elif ref in ("J_DG", "J_DG1") and num == "6":
                use = True
            elif ref in ("J_SWD", "J_SWD1") and num == "3":
                use = True
            elif ref in ("J_USB", "J_USB1") and (
                num in ("SH",) or num.upper() == "GND"
            ):
                use = True
            elif ref in ("J_BAT", "J_BAT1") and num == "2":
                use = True
            elif ref in ("J_DC", "J_DC1") and num in ("1", "S", "GND"):
                use = True
            elif ref in ("U2", "U3") and num in ("3", "13", "18", "20", "29"):
                use = True
            elif ref == "U1" and (
                num.upper() == "GND" or num in ("1", "3", "33", "55")
            ):
                use = True
            # Do not assign C* pin2 — many are CPI/VM/power, not GND.
            if use:
                pad.SetNet(gnd)
                n += 1
    return n


def clear_gnd_zones(board):
    import pcbnew

    doomed = []
    for z in board.Zones():
        if z.GetNetname() == "GND" or (
            z.GetIsRuleArea() and "ant" in (z.GetZoneName() or "").lower()
        ):
            doomed.append(z)
    for z in doomed:
        board.Remove(z)


def add_rect_zone(board, gnd, layer, name: str, x0, y0, x1, y1, thermal: bool):
    import pcbnew

    z = pcbnew.ZONE(board)
    z.SetNet(gnd)
    z.SetLayer(layer)
    z.SetZoneName(name)
    z.SetLocalClearance(mm(0.2))
    z.SetMinThickness(mm(0.2))
    z.SetPadConnection(
        pcbnew.ZONE_CONNECTION_THERMAL if thermal else pcbnew.ZONE_CONNECTION_FULL
    )
    z.SetThermalReliefGap(mm(0.3))
    z.SetThermalReliefSpokeWidth(mm(0.3))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    outline = z.Outline()
    # SHAPE_LINE_CHAIN
    chain = pcbnew.SHAPE_LINE_CHAIN()
    chain.Append(mm(x0), mm(y0))
    chain.Append(mm(x1), mm(y0))
    chain.Append(mm(x1), mm(y1))
    chain.Append(mm(x0), mm(y1))
    chain.SetClosed(True)
    outline.AddOutline(chain)
    board.Add(z)
    return z


def add_ant_keepout(board):
    import pcbnew

    x0, y0, x1, y1 = ANT_KEEP
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetZoneName("ant_keepout")
    # Ban pour only — existing signal routes near the tip may skim this box.
    if hasattr(z, "SetDoNotAllowCopperPour"):
        z.SetDoNotAllowCopperPour(True)
    if hasattr(z, "SetDoNotAllowTracks"):
        z.SetDoNotAllowTracks(False)
    if hasattr(z, "SetDoNotAllowVias"):
        z.SetDoNotAllowVias(False)
    # all copper layers
    ls = z.GetLayerSet()
    for layer in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
        ls.AddLayer(layer)
    z.SetLayerSet(ls)
    chain = pcbnew.SHAPE_LINE_CHAIN()
    chain.Append(mm(x0), mm(y0))
    chain.Append(mm(x1), mm(y0))
    chain.Append(mm(x1), mm(y1))
    chain.Append(mm(x0), mm(y1))
    chain.SetClosed(True)
    z.Outline().AddOutline(chain)
    board.Add(z)


def stitch_blocked(board, x: float, y: float) -> bool:
    """True if a 0.6 mm stitch via here fails 0.2 mm clearance to non-GND copper."""
    import pcbnew
    import math

    via_r = 0.3
    rule = 0.2
    for t in board.GetTracks():
        net = t.GetNetname()
        if net in ("GND", ""):
            continue
        need = via_r + rule
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition()
            try:
                other_r = pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) * 0.5
            except TypeError:
                other_r = pcbnew.ToMM(t.GetWidth()) * 0.5
            if math.hypot(pcbnew.ToMM(p.x) - x, pcbnew.ToMM(p.y) - y) < need + other_r:
                return True
            continue
        s, e = t.GetStart(), t.GetEnd()
        x0, y0 = pcbnew.ToMM(s.x), pcbnew.ToMM(s.y)
        x1, y1 = pcbnew.ToMM(e.x), pcbnew.ToMM(e.y)
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy
        if L2 < 1e-9:
            dist = math.hypot(x0 - x, y0 - y)
        else:
            tpar = max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / L2))
            dist = math.hypot(x0 + tpar * dx - x, y0 + tpar * dy - y)
        if dist < need + pcbnew.ToMM(t.GetWidth()) * 0.5:
            return True
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if (pad.GetNetname() or "GND") == "GND":
                continue
            c = pad.GetCenter()
            # conservative: treat pad as 0.5 mm radius
            if math.hypot(pcbnew.ToMM(c.x) - x, pcbnew.ToMM(c.y) - y) < via_r + rule + 0.5:
                return True
    return False


def add_stitch_vias(board, gnd) -> int:
    import pcbnew

    n = 0
    skipped = 0
    for x, y in STITCH_XY:
        ax0, ay0, ax1, ay1 = ANT_KEEP
        if ax0 <= x <= ax1 and ay0 <= y <= ay1:
            skipped += 1
            continue
        if stitch_blocked(board, x, y):
            skipped += 1
            continue
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        v.SetDrill(mm(0.3))
        v.SetWidth(mm(0.6))
        v.SetNet(gnd)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        board.Add(v)
        n += 1
    if skipped:
        print(f"pour_gnd: skipped {skipped} stitch vias (ant keepout or non-GND copper)")
    return n


def main() -> int:
    try:
        import pcbnew
    except ImportError:
        print(
            "Need KiCad Python with pcbnew. Run:\n"
            "  /Applications/KiCad/KiCad.app/Contents/Frameworks/"
            "Python.framework/Versions/Current/bin/python3 tools/pour_gnd.py",
            file=sys.stderr,
        )
        return 2

    if not PCB.exists():
        print(f"missing {PCB}", file=sys.stderr)
        return 1

    board = pcbnew.LoadBoard(str(PCB))
    gnd = ensure_gnd(board)
    assigned = assign_gnd_pads(board, gnd)
    clear_gnd_zones(board)

    # F: FULL (fewer islands / starved thermals). B: thermal. Inners: solid.
    margin = 0.25
    x0, y0 = BOARD_OX + margin, BOARD_OY + margin
    x1, y1 = BOARD_OX + W - margin, BOARD_OY + H - margin
    add_rect_zone(board, gnd, pcbnew.F_Cu, "GND_F", x0, y0, x1, y1, False)
    add_rect_zone(board, gnd, pcbnew.B_Cu, "GND_B", x0, y0, x1, y1, True)
    add_rect_zone(board, gnd, pcbnew.In1_Cu, "GND_In1", x0, y0, x1, y1, False)
    add_rect_zone(board, gnd, pcbnew.In2_Cu, "GND_In2", x0, y0, x1, y1, False)
    add_ant_keepout(board)

    vias = add_stitch_vias(board, gnd)

    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())

    pcbnew.SaveBoard(str(PCB), board)
    print(
        f"pour_gnd: GND pads={assigned}  stitch vias={vias}  "
        f"zones filled → {PCB}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
