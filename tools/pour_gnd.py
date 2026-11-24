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

ROOT = Path(__file__).resolve().parents[1]
PCB = ROOT / "hardware" / "adeptbt.kicad_pcb"
W, H = 85.6, 53.98

# Stitch vias near decoupling clusters (board mm) — keep clear of pads.
STITCH_XY = [
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
]

# Antenna keepout — U1 @ (15.0,44.45) ang 180; tip flush south edge
ANT_KEEP = (7.5, 46.0, 22.5, 53.8)


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
    """Heuristic GND assignment until full sch→pcb netlist import exists."""
    n = 0
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        for pad in fp.Pads():
            num = pad.GetNumber()
            use = False
            if ref.startswith("H"):
                use = True
            elif ref in ("J_STEP1", "J_STEP2") and num == "6":
                use = True
            elif ref == "J_PWR" and num == "2":
                use = True
            elif ref == "J_AN" and num == "7":
                use = True
            elif ref == "J_DG" and num == "6":
                use = True
            elif ref == "J_SWD" and num == "3":
                use = True
            elif ref == "J_USB" and num in ("", "SH", "A1", "B12", "GND"):
                # shield + typical GND pins; empty NPTH left alone if not SH
                use = num in ("SH",) or num.upper() == "GND"
            elif ref == "J_BAT" and num == "2":
                use = True  # JST PH pin 2 = − in common footprints
            elif ref == "J_DC" and num in ("1", "S", "GND"):
                use = True
            elif ref in ("U2", "U3") and num in ("3", "13", "18", "20", "29"):
                use = True
            elif ref == "U1" and (
                num.upper() == "GND"
                or num in ("1", "3", "33", "55")  # common Raytac GND pins
            ):
                use = True
            elif ref.startswith("C") and num == "2":
                use = True  # sch: pin2 = GND
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
    # no copper pour / tracks / vias in keepout
    if hasattr(z, "SetDoNotAllowCopperPour"):
        z.SetDoNotAllowCopperPour(True)
    if hasattr(z, "SetDoNotAllowTracks"):
        z.SetDoNotAllowTracks(True)
    if hasattr(z, "SetDoNotAllowVias"):
        z.SetDoNotAllowVias(True)
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


def add_stitch_vias(board, gnd) -> int:
    import pcbnew

    n = 0
    for x, y in STITCH_XY:
        # skip if inside antenna keepout
        ax0, ay0, ax1, ay1 = ANT_KEEP
        if ax0 <= x <= ax1 and ay0 <= y <= ay1:
            continue
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        v.SetDrill(mm(0.3))
        v.SetWidth(mm(0.6))
        v.SetNet(gnd)
        # through all copper
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        board.Add(v)
        n += 1
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

    # Outer pours: thermal. Inners: solid (full connection).
    margin = 0.25
    add_rect_zone(
        board, gnd, pcbnew.F_Cu, "GND_F", margin, margin, W - margin, H - margin, True
    )
    add_rect_zone(
        board, gnd, pcbnew.B_Cu, "GND_B", margin, margin, W - margin, H - margin, True
    )
    add_rect_zone(
        board, gnd, pcbnew.In1_Cu, "GND_In1", margin, margin, W - margin, H - margin, False
    )
    add_rect_zone(
        board, gnd, pcbnew.In2_Cu, "GND_In2", margin, margin, W - margin, H - margin, False
    )
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
