#!/usr/bin/env python3
"""Post-Freerouting leftover cleanup for AdeptBT.

Safe steps only (no speculative Manhattan across dense copper):

1. Widen tracks below board min 0.2 mm
2. Shrink ant_keepout south of U1 pads; allow pads in keepout
3. Set GND_F pad connection to FULL and refill zones

Long leftovers (VM / SWD / D2 / D3 / CHG_STAT) are finished by re-exporting
DSN and running Freerouting again (see hardware/exports/freerouting_leftover.log).
Do not invent crossing routes in this script — that caused shorts.

  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \\
    tools/fix_leftover_nets.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PCB = ROOT / "hardware" / "adeptbt.kicad_pcb"
MIN_WIDTH = 0.2
ANT_OLD = "(xy 5.5 46) (xy 20.5 46) (xy 20.5 53.8) (xy 5.5 53.8)"
ANT_NEW = "(xy 5.5 50.0) (xy 20.5 50.0) (xy 20.5 53.8) (xy 5.5 53.8)"


def mm(x: float) -> int:
    import pcbnew

    return int(pcbnew.FromMM(x))


def to_mm(v) -> float:
    import pcbnew

    return pcbnew.ToMM(v)


def bump_rev() -> str:
    text = PCB.read_text()
    m = re.search(r'\(rev "([0-9]+)\.([0-9]+)"\)', text)
    if not m:
        return "?"
    new = f"{int(m.group(1))}.{int(m.group(2)) + 1}"
    text = text.replace(f'(rev "{m.group(1)}.{m.group(2)}")', f'(rev "{new}")', 1)
    text = re.sub(r'\(gr_text "rev [0-9.]+"', f'(gr_text "rev {new}"', text, count=1)
    if ANT_OLD in text:
        text = text.replace(ANT_OLD, ANT_NEW, 1)
    text = text.replace("(pads not_allowed)", "(pads allowed)", 1)
    # Antenna tip must stay clear of pours (STACKUP.md)
    i = text.find("ant_keepout")
    if i >= 0:
        text = text[:i] + text[i:].replace(
            "copperpour allowed", "copperpour not_allowed", 1
        )
    PCB.write_text(text)
    return new


def main() -> int:
    try:
        import pcbnew
    except ImportError:
        print("Need KiCad bundled Python with pcbnew", file=sys.stderr)
        return 2

    board = pcbnew.LoadBoard(str(PCB))
    widened = 0
    for t in board.GetTracks():
        if t.GetClass() != "PCB_TRACK":
            continue
        if to_mm(t.GetWidth()) < MIN_WIDTH - 1e-6:
            t.SetWidth(mm(MIN_WIDTH))
            widened += 1

    for z in board.Zones():
        if z.GetIsRuleArea():
            continue
        if z.GetNetname() != "GND":
            continue
        if board.GetLayerName(z.GetLayer()) == "F.Cu":
            z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)

    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(PCB), board)
    rev = bump_rev()
    print(f"fix_leftover: widened={widened} gnd_f=FULL rev={rev}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
