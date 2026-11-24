#!/usr/bin/env python3
"""Priority Manhattan router for AdeptBT (path B).

Order: critical short nets → PowerHV → PowerLV → remaining signals.
GND is left to zones. Skips antenna keepout. Uses KiCad pcbnew.

  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \\
    tools/route_priority.py
"""

from __future__ import annotations

import math
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PCB = ROOT / "hardware" / "adeptbt.kicad_pcb"

# docs/STACKUP.md / tools/pour_gnd.py
ANT_KEEP = (7.5, 46.0, 22.5, 53.8)
BOARD_MARGIN = 0.4
CLEARANCE = 0.2

POWER_HV = {"VIN", "VIN_RAW", "VIN_F", "VM1", "VM2"}
POWER_LV = {"+5V", "+3V3", "USB_5V", "VBAT", "V+", "SW", "BST"}
PRIORITY_FIRST = ["BST", "SW", "VIN_F", "VIN_RAW"]

WIDTH = {
    "PowerHV": 0.6,
    "PowerLV": 0.4,
    "Signal": 0.25,
}
VIA = {
    "PowerHV": (0.8, 0.4),
    "PowerLV": (0.7, 0.35),
    "Signal": (0.6, 0.3),
}


def mm(x: float) -> int:
    import pcbnew

    return int(pcbnew.FromMM(x))


def to_mm(v) -> float:
    import pcbnew

    return pcbnew.ToMM(v)


def net_class(name: str) -> str:
    if name in POWER_HV or name.startswith("VIN"):
        return "PowerHV"
    if name in POWER_LV:
        return "PowerLV"
    return "Signal"


def track_width(name: str) -> float:
    return WIDTH[net_class(name)]


def in_ant(x: float, y: float, pad: float = 0.0) -> bool:
    x0, y0, x1, y1 = ANT_KEEP
    return (x0 - pad) <= x <= (x1 + pad) and (y0 - pad) <= y <= (y1 + pad)


def seg_hits_ant(x0, y0, x1, y1) -> bool:
    # sample along segment
    n = max(2, int(math.hypot(x1 - x0, y1 - y0) / 0.5))
    for i in range(n + 1):
        t = i / n
        if in_ant(x0 + t * (x1 - x0), y0 + t * (y1 - y0), 0.3):
            return True
    return False


def point_ok(x: float, y: float, board_bb) -> bool:
    if in_ant(x, y, 0.3):
        return False
    return (
        board_bb[0] + BOARD_MARGIN <= x <= board_bb[2] - BOARD_MARGIN
        and board_bb[1] + BOARD_MARGIN <= y <= board_bb[3] - BOARD_MARGIN
    )


class Obstacles:
    """Foreign-pad disks for crude clearance checks."""

    def __init__(self):
        self.disks: list[tuple[float, float, float, str]] = []  # x,y,r,net

    def add_pad(self, x, y, size_mm, net):
        r = max(size_mm) / 2 + CLEARANCE
        self.disks.append((x, y, r, net))

    def hit(self, x0, y0, x1, y1, net, ignore_xy: list[tuple[float, float]] | None = None) -> bool:
        """Return True if segment comes too close to a foreign pad.

        Pads near ignore_xy (route endpoints) are skipped so we can enter/leave pads.
        """
        ignore = ignore_xy or []
        n = max(2, int(math.hypot(x1 - x0, y1 - y0) / 0.4))
        for i in range(n + 1):
            t = i / n
            x = x0 + t * (x1 - x0)
            y = y0 + t * (y1 - y0)
            # skip samples glued to endpoints
            if any(math.hypot(x - ix, y - iy) < 0.7 for ix, iy in ignore):
                continue
            for ox, oy, r, onet in self.disks:
                if onet == net:
                    continue
                if any(math.hypot(ox - ix, oy - iy) < 0.55 for ix, iy in ignore):
                    continue
                if math.hypot(x - ox, y - oy) < r:
                    return True
        return False


def pad_size_mm(pad) -> tuple[float, float]:
    import pcbnew

    s = pad.GetSize()
    return to_mm(s.x), to_mm(s.y)


def collect_pads(board):
    by_net = defaultdict(list)
    obs = Obstacles()
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        for pad in fp.Pads():
            net = pad.GetNetname()
            if not net:
                continue
            c = pad.GetCenter()
            x, y = to_mm(c.x), to_mm(c.y)
            sx, sy = pad_size_mm(pad)
            by_net[net].append(
                {
                    "ref": ref,
                    "num": pad.GetNumber(),
                    "x": x,
                    "y": y,
                    "pad": pad,
                    "net": net,
                }
            )
            obs.add_pad(x, y, (sx, sy), net)
    return by_net, obs


def mst_edges(pads: list[dict]) -> list[tuple[dict, dict, float]]:
    if len(pads) < 2:
        return []
    unused = pads[1:]
    used = [pads[0]]
    edges = []
    while unused:
        best = None
        for u in used:
            for i, v in enumerate(unused):
                d = math.hypot(u["x"] - v["x"], u["y"] - v["y"])
                if best is None or d < best[0]:
                    best = (d, u, i, v)
        d, u, i, v = best
        edges.append((u, v, d))
        used.append(unused.pop(i))
    return edges


def add_track(board, netitem, x0, y0, x1, y1, width, layer):
    import pcbnew

    if math.hypot(x1 - x0, y1 - y0) < 0.05:
        return None
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(mm(x0), mm(y0)))
    t.SetEnd(pcbnew.VECTOR2I(mm(x1), mm(y1)))
    t.SetWidth(mm(width))
    t.SetLayer(layer)
    t.SetNet(netitem)
    board.Add(t)
    return t


def add_via(board, netitem, x, y, dia, drill):
    import pcbnew

    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    v.SetWidth(mm(dia))
    v.SetDrill(mm(drill))
    v.SetNet(netitem)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    board.Add(v)
    return v


def try_manhattan(
    board,
    netitem,
    net,
    a,
    b,
    width,
    layer,
    obs: Obstacles,
    board_bb,
    existing_seg_check,
) -> bool:
    """HV then VH; return True if routed."""
    import pcbnew

    x0, y0 = a["x"], a["y"]
    x1, y1 = b["x"], b["y"]
    if not point_ok(x0, y0, board_bb) or not point_ok(x1, y1, board_bb):
        return False

    ends = [(x0, y0), (x1, y1)]

    def ok_seg(xa, ya, xb, yb):
        if seg_hits_ant(xa, ya, xb, yb):
            return False
        if obs.hit(xa, ya, xb, yb, net, ends):
            return False
        if existing_seg_check(xa, ya, xb, yb, net):
            return False
        return True

    # direct if axis-aligned
    if abs(y0 - y1) < 0.05:
        if ok_seg(x0, y0, x1, y0):
            add_track(board, netitem, x0, y0, x1, y0, width, layer)
            return True
        return False
    if abs(x0 - x1) < 0.05:
        if ok_seg(x0, y0, x0, y1):
            add_track(board, netitem, x0, y0, x0, y1, width, layer)
            return True
        return False

    # elbow at (x1, y0)
    if point_ok(x1, y0, board_bb) and ok_seg(x0, y0, x1, y0) and ok_seg(x1, y0, x1, y1):
        add_track(board, netitem, x0, y0, x1, y0, width, layer)
        add_track(board, netitem, x1, y0, x1, y1, width, layer)
        return True
    # elbow at (x0, y1)
    if point_ok(x0, y1, board_bb) and ok_seg(x0, y0, x0, y1) and ok_seg(x0, y1, x1, y1):
        add_track(board, netitem, x0, y0, x0, y1, width, layer)
        add_track(board, netitem, x0, y1, x1, y1, width, layer)
        return True
    # two-bend: via mid x or mid y
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    for path in (
        [(x0, y0), (mx, y0), (mx, y1), (x1, y1)],
        [(x0, y0), (x0, my), (x1, my), (x1, y1)],
    ):
        if all(point_ok(px, py, board_bb) for px, py in path[1:-1]) and all(
            ok_seg(path[i][0], path[i][1], path[i + 1][0], path[i + 1][1])
            for i in range(len(path) - 1)
        ):
            for i in range(len(path) - 1):
                add_track(
                    board,
                    netitem,
                    path[i][0],
                    path[i][1],
                    path[i + 1][0],
                    path[i + 1][1],
                    width,
                    layer,
                )
            return True
    return False


def try_via_bridge(board, netitem, net, a, b, width, obs, board_bb, existing_seg_check):
    """F to elbow via, B to target (or reverse)."""
    import pcbnew

    x0, y0 = a["x"], a["y"]
    x1, y1 = b["x"], b["y"]
    dia, drill = VIA[net_class(net)]
    elbows = [(x1, y0), (x0, y1)]

    ends = [(x0, y0), (x1, y1)]

    def ok_seg(xa, ya, xb, yb):
        if seg_hits_ant(xa, ya, xb, yb):
            return False
        if obs.hit(xa, ya, xb, yb, net, ends):
            return False
        if existing_seg_check(xa, ya, xb, yb, net):
            return False
        return True

    for ex, ey in elbows:
        if not point_ok(ex, ey, board_bb):
            continue
        if in_ant(ex, ey, 0.5):
            continue
        # F: a → elbow, via, B: elbow → b
        if ok_seg(x0, y0, ex, ey) and ok_seg(ex, ey, x1, y1):
            add_track(board, netitem, x0, y0, ex, ey, width, pcbnew.F_Cu)
            add_via(board, netitem, ex, ey, dia, drill)
            add_track(board, netitem, ex, ey, x1, y1, width, pcbnew.B_Cu)
            return True
    return False


def existing_tracks_checker(board):
    """Build checker against already-placed tracks (other nets)."""
    segs = []
    for t in board.GetTracks():
        if t.GetClass() != "PCB_TRACK":
            continue
        net = t.GetNetname()
        s, e = t.GetStart(), t.GetEnd()
        w = to_mm(t.GetWidth())
        segs.append((to_mm(s.x), to_mm(s.y), to_mm(e.x), to_mm(e.y), w, net))

    def hit(x0, y0, x1, y1, net):
        # sample vs foreign track centerlines
        n = max(2, int(math.hypot(x1 - x0, y1 - y0) / 0.4))
        pts = [
            (x0 + i / n * (x1 - x0), y0 + i / n * (y1 - y0)) for i in range(n + 1)
        ]
        for xa, ya, xb, yb, w, onet in segs:
            if onet == net:
                continue
            # expand clearance
            r = w / 2 + CLEARANCE
            m = max(2, int(math.hypot(xb - xa, yb - ya) / 0.4))
            for j in range(m + 1):
                tx = xa + j / m * (xb - xa)
                ty = ya + j / m * (yb - ya)
                for px, py in pts:
                    if math.hypot(px - tx, py - ty) < r:
                        return True
        return False

    def refresh():
        segs.clear()
        for t in board.GetTracks():
            if t.GetClass() != "PCB_TRACK":
                continue
            net = t.GetNetname()
            s, e = t.GetStart(), t.GetEnd()
            w = to_mm(t.GetWidth())
            segs.append((to_mm(s.x), to_mm(s.y), to_mm(e.x), to_mm(e.y), w, net))

    return hit, refresh


def net_sort_key(item):
    name, pads = item
    if name == "GND":
        return (99, 0, name)
    if name in PRIORITY_FIRST:
        return (0, PRIORITY_FIRST.index(name), name)
    if name in POWER_HV or name.startswith("VIN"):
        return (1, -len(pads), name)
    if name in POWER_LV:
        return (2, -len(pads), name)
    return (3, len(pads), name)


def bump_rev(board) -> str:
    import pcbnew

    # title block / board rev property
    props = board.GetProperties() if hasattr(board, "GetProperties") else None
    # file-level: edit after save via regex is more reliable for KiCad 10
    return ""


def stitch_gnd_at_caps(board, gnd) -> int:
    """Via next to each C* pad on GND (toward board center of pad)."""
    import pcbnew

    n = 0
    for fp in board.GetFootprints():
        if not fp.GetReference().startswith("C"):
            continue
        for pad in fp.Pads():
            if pad.GetNetname() != "GND":
                continue
            c = pad.GetCenter()
            x, y = to_mm(c.x), to_mm(c.y)
            # offset 1.2 mm toward board center
            cx, cy = 85.6 / 2, 53.98 / 2
            dx, dy = cx - x, cy - y
            L = math.hypot(dx, dy) or 1.0
            vx, vy = x + 1.2 * dx / L, y + 1.2 * dy / L
            if in_ant(vx, vy, 0.6):
                continue
            if not (BOARD_MARGIN < vx < 85.6 - BOARD_MARGIN and BOARD_MARGIN < vy < 53.98 - BOARD_MARGIN):
                continue
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(pcbnew.VECTOR2I(mm(vx), mm(vy)))
            v.SetWidth(mm(0.6))
            v.SetDrill(mm(0.3))
            v.SetNet(gnd)
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            board.Add(v)
            n += 1
    return n


def main() -> int:
    try:
        import pcbnew
    except ImportError:
        print(
            "Need KiCad Python:\n"
            "  /Applications/KiCad/KiCad.app/Contents/Frameworks/"
            "Python.framework/Versions/Current/bin/python3 tools/route_priority.py",
            file=sys.stderr,
        )
        return 2

    board = pcbnew.LoadBoard(str(PCB))
    bb = board.GetBoardEdgesBoundingBox()
    board_bb = (to_mm(bb.GetLeft()), to_mm(bb.GetTop()), to_mm(bb.GetRight()), to_mm(bb.GetBottom()))

    by_net, obs = collect_pads(board)
    hit_tracks, refresh_tracks = existing_tracks_checker(board)

    routed = 0
    failed = 0
    skipped_gnd = 0

    for net, pads in sorted(by_net.items(), key=net_sort_key):
        if net == "GND":
            skipped_gnd = len(pads)
            continue
        if len(pads) < 2:
            continue
        netitem = board.FindNet(net)
        if netitem is None:
            continue
        width = track_width(net)
        edges = mst_edges(pads)
        for a, b, d in edges:
            if d < 0.15:
                continue  # same pad / stacked
            # Local stubs only — long spans need interactive / freeroute cleanup.
            if d > 4.0:
                failed += 1
                continue
            ok = try_manhattan(
                board, netitem, net, a, b, width, pcbnew.F_Cu, obs, board_bb, hit_tracks
            )
            if not ok:
                ok = try_manhattan(
                    board, netitem, net, a, b, width, pcbnew.B_Cu, obs, board_bb, hit_tracks
                )
            if not ok:
                ok = try_via_bridge(
                    board, netitem, net, a, b, width, obs, board_bb, hit_tracks
                )
            if ok:
                routed += 1
                refresh_tracks()
            else:
                failed += 1

    # Stitch vias: use pour_gnd.py fixed list only (cap-adjacent autos cause hole DRC).
    vias = 0

    # refill GND zones
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())

    pcbnew.SaveBoard(str(PCB), board)

    # bump rev in file
    text = PCB.read_text()
    m = re.search(r'\(rev "([0-9]+)\.([0-9]+)"\)', text)
    if m:
        major, minor = int(m.group(1)), int(m.group(2))
        new = f"{major}.{minor + 1}"
        text = text.replace(f'(rev "{m.group(1)}.{m.group(2)}")', f'(rev "{new}")', 1)
        # silk title if present
        text = re.sub(
            r'AdeptBT rev [0-9.]+',
            f"AdeptBT rev {new}",
            text,
            count=1,
        )
        PCB.write_text(text)
    else:
        new = "?"

    print(
        f"route_priority: routed_edges={routed} failed={failed} "
        f"gnd_pads={skipped_gnd} stitch_vias={vias} rev={new} → {PCB}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
