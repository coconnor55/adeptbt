#!/usr/bin/env python3
"""Place GND vias (+ short dogbones) for SMD GND pads — no signal routing.

PTH GND pads already reach inner planes; skip them.

QFN with exposed pad (`QFN_EP_THERMAL`: U2/U3/U5):
  - thermal via array **in** the EP
  - short F.Cu ties from package GND pins → EP (axis-aligned only)
  - no per-pin vias under the package

Other internal/EP pads (not in that set): skip vias.

Other SMD GND pads get one via just outside the pad + F.Cu dogbone:
  - small parts (≤2 SMD pads): step **away** from the footprint origin
  - larger parts: step **toward** the origin (under the body)
  - `VIA_DIR_EXCEPT`: fixed board-XY direction (TE screws → edge)

Re-runnable: without --wipe, strip prior *locked* GND vias/tracks (script copper)
then place again — hand routes stay. With --wipe, clear all copper first.
Vias/dogbones are locked so Freerouting (ignore GND) will not rip them.

Skip any via that would violate copper clearance or hole clearance vs foreign
pads/NPTH (same rules as board DRC minima). Also skip vias whose copper or
hole overlaps the source SMD pad (no via-in-pad / pad-edge vias).

  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \\
    tools/gnd_pad_vias.py [--wipe] [--no-bump]

--wipe  remove all tracks, vias, and zones first
"""

from __future__ import annotations

import argparse
import math
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PCB = ROOT / "hardware" / "adeptbt.kicad_pcb"

VIA_DRILL = 0.3
VIA_DIA = 0.6
EP_VIA_DRILL = 0.3
EP_VIA_DIA = 0.5
DOG_W = 0.25
TIE_W = 0.25  # QFN pin → EP
# Internal/EP pad if both sides ≥ this (mm)
EP_MIN = 2.4
# ≤ this many SMD pads → "small": via outside, not under the body
SMALL_SMD_PADS = 2
BOARD_W = 85.6
BOARD_H = 53.98
EDGE_MARGIN = 0.55  # keep via center on-board
# Match Board Setup / netclass minima used by DRC on this board (+ slack)
CLEAR_CU = 0.20
CLEAR_HOLE = 0.25
CLEAR_SLACK = 0.05  # keep DRC actual ≥ rule (circle pad model is optimistic)
# Keep via copper/hole fully off the source SMD pad (no via-in-pad / edge clip)
PAD_VIA_CLEAR = 0.10
# keep vias out of U1 antenna keepout (STACKUP / ant_keepout)
ANT = (5.5, 50.0, 20.5, 53.8)

# EP thermal array + pin→EP copper; no per-pin vias (TMC2209, MCP73871)
QFN_EP_THERMAL = frozenset({"U2", "U3", "U5"})

# ref → unit vector in board XY (KiCad Y-down). TE screw GNDs toward outline.
VIA_DIR_EXCEPT: dict[str, tuple[float, float]] = {
    "J_STEP1": (0.0, -1.0),  # north edge
    "J_STEP2": (0.0, 1.0),  # south edge
    "J_PWR1": (0.0, -1.0),  # north edge
}


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


def in_ant(x: float, y: float) -> bool:
    x0, y0, x1, y1 = ANT
    return x0 <= x <= x1 and y0 <= y <= y1


def wipe_copper(board) -> tuple[int, int]:
    nt = len(list(board.GetTracks()))
    nz = len(list(board.Zones()))
    for t in list(board.GetTracks()):
        board.Remove(t)
    for z in list(board.Zones()):
        board.Remove(z)
    return nt, nz


def pad_drill_mm(pad) -> float:
    import pcbnew

    if hasattr(pad, "GetDrillSizeX"):
        return to_mm(pad.GetDrillSizeX())
    return to_mm(pad.GetDrillSize().x)


def smd_pad_count(fp) -> int:
    return sum(1 for p in fp.Pads() if pad_drill_mm(p) <= 0.05)


def add_via(board, x, y, net, drill=VIA_DRILL, dia=VIA_DIA, locked=True) -> bool:
    import pcbnew

    if in_ant(x, y):
        return False
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    v.SetDrill(mm(drill))
    v.SetWidth(mm(dia))
    v.SetNet(net)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    if locked:
        v.SetLocked(True)
    board.Add(v)
    return True


def add_dog(board, x1, y1, x2, y2, net, width=DOG_W, locked=True) -> int:
    return add_track(board, x1, y1, x2, y2, net, width=width, layer="F.Cu", locked=locked)


def add_track(
    board, x1, y1, x2, y2, net, width=DOG_W, layer="F.Cu", locked=True
) -> int:
    import pcbnew

    if abs(x1 - x2) < 1e-4 and abs(y1 - y2) < 1e-4:
        return 0
    layer_id = pcbnew.F_Cu if layer == "F.Cu" else pcbnew.B_Cu
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
    t.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
    t.SetWidth(mm(width))
    t.SetLayer(layer_id)
    t.SetNet(net)
    if locked:
        t.SetLocked(True)
    board.Add(t)
    return 1


def via_too_close(placed: list[tuple[float, float]], x: float, y: float, min_d=0.65) -> bool:
    for px, py in placed:
        if math.hypot(px - x, py - y) < min_d:
            return True
    return False


def clamp_on_board(x: float, y: float) -> tuple[float, float]:
    m = EDGE_MARGIN
    return (
        min(BOARD_W - m, max(m, x)),
        min(BOARD_H - m, max(m, y)),
    )


def strip_locked_gnd(board) -> tuple[int, int]:
    """Remove prior script copper only (locked GND vias + locked GND tracks)."""
    n_via = n_trk = 0
    for t in list(board.GetTracks()):
        if t.GetNetname() != "GND":
            continue
        if not t.IsLocked():
            continue
        if t.GetClass() == "PCB_VIA":
            n_via += 1
        else:
            n_trk += 1
        board.Remove(t)
    return n_via, n_trk


def _foreign_pads(board):
    """Cache of (x, y, pad_r, hole_r) for non-GND pads."""
    out = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname() == "GND":
                continue
            px = to_mm(pad.GetPosition().x)
            py = to_mm(pad.GetPosition().y)
            sx = to_mm(pad.GetSize().x)
            sy = to_mm(pad.GetSize().y)
            pad_r = 0.5 * math.hypot(sx, sy)  # bounding circle
            hole = pad_drill_mm(pad)
            hole_r = hole * 0.5 if hole > 0.05 else 0.0
            out.append((px, py, pad_r, hole_r))
    return out


def _foreign_copper(board):
    """Non-GND tracks/vias: segs (x1,y1,x2,y2,half_w), vias (x,y,r)."""
    import pcbnew

    segs: list[tuple[float, float, float, float, float]] = []
    vias: list[tuple[float, float, float]] = []
    for t in board.GetTracks():
        if t.GetNetname() == "GND":
            continue
        if t.GetClass() == "PCB_VIA":
            try:
                r = to_mm(t.GetWidth(pcbnew.F_Cu)) * 0.5
            except TypeError:
                r = to_mm(t.GetWidth()) * 0.5
            vias.append((to_mm(t.GetX()), to_mm(t.GetY()), r))
            continue
        segs.append(
            (
                to_mm(t.GetStart().x),
                to_mm(t.GetStart().y),
                to_mm(t.GetEnd().x),
                to_mm(t.GetEnd().y),
                to_mm(t.GetWidth()) * 0.5,
            )
        )
    return segs, vias


def _dist_point_seg(
    px: float, py: float, x1: float, y1: float, x2: float, y2: float
) -> float:
    dx, dy = x2 - x1, y2 - y1
    len2 = dx * dx + dy * dy
    if len2 < 1e-18:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / len2))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def via_clear_ok(
    foreign, x: float, y: float, dia: float, drill: float, copper=None
) -> bool:
    """False if via copper/hole would violate clearance vs a foreign pad or NPTH."""
    via_r = dia * 0.5
    drill_r = drill * 0.5
    need_cu = via_r + CLEAR_CU + CLEAR_SLACK
    need_hole = drill_r + CLEAR_HOLE + CLEAR_SLACK
    for px, py, pad_r, hole_r in foreign:
        d = math.hypot(px - x, py - y)
        if d < need_cu + pad_r:
            return False
        if hole_r > 0 and d < need_hole + hole_r:
            return False
    if copper:
        segs, vias = copper
        for x1, y1, x2, y2, half_w in segs:
            if _dist_point_seg(x, y, x1, y1, x2, y2) < need_cu + half_w:
                return False
        for vx, vy, vr in vias:
            if math.hypot(vx - x, vy - y) < need_cu + vr:
                return False
    return True


def dogbone_clear_ok(
    foreign, x1: float, y1: float, x2: float, y2: float, width: float = DOG_W
) -> bool:
    """False if the pad→via dogbone would clip a foreign pad."""
    half = width * 0.5
    need = half + CLEAR_CU + CLEAR_SLACK
    for t in (0.15, 0.35, 0.5, 0.65, 0.85):
        x = x1 + (x2 - x1) * t
        y = y1 + (y2 - y1) * t
        for px, py, pad_r, _hole in foreign:
            if math.hypot(px - x, py - y) < need + pad_r:
                return False
    return True


def dist_point_to_pad_rect(
    vx: float, vy: float, px: float, py: float, sx: float, sy: float
) -> float:
    """Signed distance from point to axis-aligned pad rect (negative = inside)."""
    dx = abs(vx - px) - sx * 0.5
    dy = abs(vy - py) - sy * 0.5
    if dx < 0.0 and dy < 0.0:
        return max(dx, dy)  # both negative; closer to zero = nearer edge
    if dx < 0.0:
        dx = 0.0
    if dy < 0.0:
        dy = 0.0
    return math.hypot(dx, dy)


def via_clears_own_pad(
    px: float,
    py: float,
    sx: float,
    sy: float,
    vx: float,
    vy: float,
    dia: float,
    drill: float,
) -> bool:
    """False if via copper or drill intersects the source SMD pad (+ PAD_VIA_CLEAR)."""
    d = dist_point_to_pad_rect(vx, vy, px, py, sx, sy)
    need = max(dia * 0.5, drill * 0.5) + PAD_VIA_CLEAR
    return d >= need


def pad_exit_along(sx: float, sy: float, ux: float, uy: float) -> float:
    """Distance from pad center to rect edge along unit vector (ux, uy)."""
    tx = (sx * 0.5 / abs(ux)) if abs(ux) > 1e-9 else 1e9
    ty = (sy * 0.5 / abs(uy)) if abs(uy) > 1e-9 else 1e9
    return min(tx, ty)


def pick_via_xy(
    board,
    foreign,
    copper,
    placed: list[tuple[float, float]],
    px: float,
    py: float,
    sx: float,
    sy: float,
    ux: float,
    uy: float,
    step: float,
    dia: float,
    drill: float,
) -> tuple[float, float] | None:
    """Try primary/longer/perpendicular offsets; None if nothing clears DRC minima."""
    cands: list[tuple[float, float]] = []
    if abs(ux) >= 1e-9 or abs(uy) >= 1e-9:
        for scale in (1.0, 1.35, 1.7, 2.2, 2.8, 3.5):
            s = step * scale
            cands.append((px + ux * s, py + uy * s))
            cands.append((px - uy * s, py + ux * s))
            cands.append((px + uy * s, py - ux * s))
    else:
        cands.append((px, py))
    seen: set[tuple[float, float]] = set()
    for raw_x, raw_y in cands:
        vx, vy = clamp_on_board(raw_x, raw_y)
        key = (round(vx, 3), round(vy, 3))
        if key in seen:
            continue
        seen.add(key)
        if in_ant(vx, vy):
            continue
        if via_too_close(placed, vx, vy):
            continue
        if not via_clears_own_pad(px, py, sx, sy, vx, vy, dia, drill):
            continue
        if not via_clear_ok(foreign, vx, vy, dia, drill, copper=copper):
            continue
        if not dogbone_clear_ok(foreign, px, py, vx, vy):
            continue
        return vx, vy
    return None


def find_ep_pad(fp):
    """Largest GND pad with both sides ≥ EP_MIN, or None."""
    best = None
    best_area = 0.0
    for pad in fp.Pads():
        if pad.GetNetname() != "GND":
            continue
        if pad_drill_mm(pad) > 0.05:
            continue
        sx, sy = to_mm(pad.GetSize().x), to_mm(pad.GetSize().y)
        if sx < EP_MIN or sy < EP_MIN:
            continue
        area = sx * sy
        if area > best_area:
            best, best_area = pad, area
    return best


def ep_via_offsets(sx: float, sy: float) -> list[tuple[float, float]]:
    """Thermal via grid inside EP. ~1 mm pitch; 3×3 if EP large enough."""
    margin = 0.55
    if sx >= 3.2 and sy >= 3.2:
        step = min(sx / 2 - margin, sy / 2 - margin, 1.0)
        return [(x, y) for x in (-step, 0.0, step) for y in (-step, 0.0, step)]
    inset = max(margin, min(sx, sy) * 0.22)
    return [
        (-inset, -inset),
        (inset, -inset),
        (-inset, inset),
        (inset, inset),
    ]


def via_offset_dir(
    ref: str, fx: float, fy: float, px: float, py: float, small: bool
) -> tuple[float, float]:
    if ref in VIA_DIR_EXCEPT:
        return VIA_DIR_EXCEPT[ref]
    dx, dy = fx - px, fy - py
    dist = math.hypot(dx, dy)
    if dist < 0.05:
        return 0.0, 0.0
    ux, uy = dx / dist, dy / dist
    if small:
        return -ux, -uy  # outside the body
    return ux, uy  # under / into the body


def add_manhattan_tie(board, px: float, py: float, ex: float, ey: float, net) -> int:
    """Pin → EP with only horizontal and/or vertical segments (no diagonals)."""
    n = 0
    if abs(px - ex) < 1e-4 and abs(py - ey) < 1e-4:
        return 0
    if abs(px - ex) < 1e-4:
        return add_dog(board, px, py, ex, ey, net, width=TIE_W)
    if abs(py - ey) < 1e-4:
        return add_dog(board, px, py, ex, ey, net, width=TIE_W)
    # Enter from the pin's side: longer axis first (orthogonal to the pad row).
    if abs(px - ex) >= abs(py - ey):
        n += add_dog(board, px, py, ex, py, net, width=TIE_W)
        n += add_dog(board, ex, py, ex, ey, net, width=TIE_W)
    else:
        n += add_dog(board, px, py, px, ey, net, width=TIE_W)
        n += add_dog(board, px, ey, ex, ey, net, width=TIE_W)
    return n


def place_qfn_ep(
    board, fp, gnd, placed: list[tuple[float, float]], foreign, copper, dry_run: bool
) -> tuple[int, int, int]:
    """EP via array + axis-aligned pin→EP ties. Returns (n_via, n_tie, n_pin_gnd)."""
    ep = find_ep_pad(fp)
    if ep is None:
        print(f"warn: {fp.GetReference()} in QFN_EP_THERMAL but no EP pad", file=sys.stderr)
        return 0, 0, 0
    ex, ey = to_mm(ep.GetPosition().x), to_mm(ep.GetPosition().y)
    sx, sy = to_mm(ep.GetSize().x), to_mm(ep.GetSize().y)
    n_via = 0
    n_tie = 0
    n_pin = 0
    ref = fp.GetReference()

    for dx, dy in ep_via_offsets(sx, sy):
        vx, vy = ex + dx, ey + dy
        if via_too_close(placed, vx, vy, min_d=0.55):
            continue
        if not via_clear_ok(foreign, vx, vy, EP_VIA_DIA, EP_VIA_DRILL, copper=copper):
            continue
        if dry_run:
            print(f"via[ep] {ref} EP @({vx:.2f},{vy:.2f})")
            placed.append((vx, vy))
            n_via += 1
            continue
        if add_via(board, vx, vy, gnd, drill=EP_VIA_DRILL, dia=EP_VIA_DIA):
            placed.append((vx, vy))
            n_via += 1

    for pad in fp.Pads():
        if pad.GetNetname() != "GND":
            continue
        if pad_drill_mm(pad) > 0.05:
            continue
        psx, psy = to_mm(pad.GetSize().x), to_mm(pad.GetSize().y)
        if psx >= EP_MIN and psy >= EP_MIN:
            continue  # EP itself
        n_pin += 1
        px, py = to_mm(pad.GetPosition().x), to_mm(pad.GetPosition().y)
        if dry_run:
            print(f"tie[ep] {ref} p{pad.GetNumber()} ({px:.2f},{py:.2f}) → EP H/V ({ex:.2f},{ey:.2f})")
            n_tie += 1
            continue
        n_tie += add_manhattan_tie(board, px, py, ex, ey, gnd)

    return n_via, n_tie, n_pin


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wipe", action="store_true", help="clear all tracks/vias/zones first")
    ap.add_argument("--no-bump", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    try:
        import pcbnew
    except ImportError:
        print(
            "Need KiCad Python with pcbnew:\n"
            "  …/KiCad.app/…/python3 tools/gnd_pad_vias.py --wipe",
            file=sys.stderr,
        )
        return 2

    board = pcbnew.LoadBoard(str(PCB))
    gnd = board.FindNet("GND")
    if gnd is None or gnd.GetNetCode() <= 0:
        print("GND net missing — update PCB from schematic first", file=sys.stderr)
        return 1

    wiped = (0, 0)
    if args.wipe:
        wiped = wipe_copper(board)
        pcbnew.SaveBoard(str(PCB), board)
        env = os.environ.copy()
        env["GND_PAD_VIAS_WIPED"] = f"{wiped[0]},{wiped[1]}"
        cmd = [sys.executable, str(Path(__file__).resolve())]
        if args.no_bump:
            cmd.append("--no-bump")
        if args.dry_run:
            cmd.append("--dry-run")
        return subprocess.call(cmd, env=env)

    if "GND_PAD_VIAS_WIPED" in os.environ:
        parts = os.environ["GND_PAD_VIAS_WIPED"].split(",")
        wiped = (int(parts[0]), int(parts[1]))

    stripped = (0, 0)
    if wiped == (0, 0) and not args.dry_run and "GND_PAD_VIAS_STRIPPED" not in os.environ:
        # Refresh script copper without ripping hand routes (coils, etc.).
        # Same SWIG rule as --wipe: Remove() then place must be a child process.
        stripped = strip_locked_gnd(board)
        pcbnew.SaveBoard(str(PCB), board)
        env = os.environ.copy()
        env["GND_PAD_VIAS_STRIPPED"] = f"{stripped[0]},{stripped[1]}"
        cmd = [sys.executable, str(Path(__file__).resolve())]
        if args.no_bump:
            cmd.append("--no-bump")
        return subprocess.call(cmd, env=env)

    if "GND_PAD_VIAS_STRIPPED" in os.environ:
        parts = os.environ["GND_PAD_VIAS_STRIPPED"].split(",")
        stripped = (int(parts[0]), int(parts[1]))

    placed: list[tuple[float, float]] = []
    foreign = _foreign_pads(board)
    copper = _foreign_copper(board)
    n_via = 0
    n_dog = 0
    n_smd = 0
    n_skip_pth = 0
    n_skip_ep = 0
    n_skip_clr = 0
    n_ep_via = 0
    n_ep_tie = 0

    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref in QFN_EP_THERMAL:
            ev, et, npin = place_qfn_ep(
                board, fp, gnd, placed, foreign, copper, args.dry_run
            )
            n_ep_via += ev
            n_ep_tie += et
            n_via += ev
            n_dog += et
            n_smd += npin + (1 if find_ep_pad(fp) else 0)
            continue

        fx, fy = to_mm(fp.GetPosition().x), to_mm(fp.GetPosition().y)
        small = smd_pad_count(fp) <= SMALL_SMD_PADS
        for pad in fp.Pads():
            if pad.GetNetname() != "GND":
                continue
            if pad_drill_mm(pad) > 0.05:
                n_skip_pth += 1
                continue
            n_smd += 1
            px, py = to_mm(pad.GetPosition().x), to_mm(pad.GetPosition().y)
            sx, sy = to_mm(pad.GetSize().x), to_mm(pad.GetSize().y)

            if sx >= EP_MIN and sy >= EP_MIN:
                n_skip_ep += 1
                continue

            ux, uy = via_offset_dir(ref, fx, fy, px, py, small)
            if abs(ux) >= 1e-9 or abs(uy) >= 1e-9:
                edge = pad_exit_along(sx, sy, ux, uy)
            else:
                edge = 0.5 * max(sx, sy)
            step = edge + VIA_DIA * 0.5 + PAD_VIA_CLEAR
            pos = pick_via_xy(
                board,
                foreign,
                copper,
                placed,
                px,
                py,
                sx,
                sy,
                ux,
                uy,
                step,
                VIA_DIA,
                VIA_DRILL,
            )
            if pos is None:
                n_skip_clr += 1
                continue
            vx, vy = pos
            if ref in VIA_DIR_EXCEPT:
                tag = "except"
            elif small:
                tag = "small"
            else:
                tag = "body"
            if args.dry_run:
                print(
                    f"via[{tag}] {ref} p{pad.GetNumber()} "
                    f"pad({px:.2f},{py:.2f}) → ({vx:.2f},{vy:.2f})"
                )
                placed.append((vx, vy))
                n_via += 1
                continue
            if add_via(board, vx, vy, gnd):
                placed.append((vx, vy))
                n_via += 1
                n_dog += add_dog(board, px, py, vx, vy, gnd)

    if args.dry_run:
        print(
            f"dry-run: smd_gnd={n_smd} vias≈{n_via} ep_vias={n_ep_via} "
            f"ep_ties={n_ep_tie} skip_pth={n_skip_pth} skip_ep={n_skip_ep} "
            f"skip_clearance={n_skip_clr}"
        )
        return 0

    pcbnew.SaveBoard(str(PCB), board)
    rev = "?" if args.no_bump else bump_rev(PCB)
    print(
        f"gnd_pad_vias: wiped_tracks={wiped[0]} wiped_zones={wiped[1]} "
        f"stripped_locked_gnd_vias={stripped[0]} stripped_locked_gnd_tracks={stripped[1]} "
        f"smd_gnd={n_smd} vias={n_via} dogbones={n_dog} "
        f"ep_vias={n_ep_via} ep_ties={n_ep_tie} "
        f"skip_pth={n_skip_pth} skip_ep={n_skip_ep} skip_clearance={n_skip_clr} "
        f"rev={rev} → {PCB}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
