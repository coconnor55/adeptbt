#!/usr/bin/env python3
"""F.SilkS + body collision / off-board check for adeptbt.kicad_pcb.

Checks:
  - silk text vs silk text
  - silk text vs footprint pads
  - silk text vs footprint F.SilkS / F.Fab geometry
  - silk text vs mounting-hole square keepouts
  - all silk text fully on-board (labels never past Edge.Cuts)
  - footprint F.SilkS / F.Fab fully on-board
  - footprint pads fully on-board (copper never past Edge.Cuts)
  - footprint outlines (F.Fab / silk for edge TE) ≥ BODY_CLEAR_MM apart
  - mounting-hole square keepouts enforce screw clearance
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PCB = ROOT / "hardware" / "adeptbt.kicad_pcb"
W, H = 85.6, 53.98
MARGIN = 0.15


def board_xy(fx: float, fy: float, fang: float, lx: float, ly: float) -> tuple[float, float]:
    """Map footprint-local (lx, ly) to board mm. KiCad PCB Y grows down."""
    a = math.radians(fang)
    ca, sa = math.cos(a), math.sin(a)
    return fx + lx * ca + ly * sa, fy - lx * sa + ly * ca


def ref_stem(ref: str) -> str:
    """J_DC1 → J_DC, M2 → M (holes keep full ref in HOLE_REFS)."""
    return re.sub(r"\d+$", "", ref)


def text_bbox(
    x: float, y: float, text: str, size: float, angle: float = 0
) -> tuple[float, float, float, float]:
    tw = max(len(text), 1) * size * 0.65
    th = size
    ang = abs(angle) % 180
    if 45 <= ang <= 135:
        tw, th = th, tw
    return (x - tw / 2, y - th / 2, x + tw / 2, y + th / 2)


def overlaps(a, b, margin: float = MARGIN) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return not (
        ax1 + margin < bx0
        or bx1 + margin < ax0
        or ay1 + margin < by0
        or by1 + margin < ay0
    )


def overlap_area(a, b) -> float:
    x0 = max(a[0], b[0])
    y0 = max(a[1], b[1])
    x1 = min(a[2], b[2])
    y1 = min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return 0.0
    return (x1 - x0) * (y1 - y0)


def on_board(bb, pad: float = 0.05) -> bool:
    x0, y0, x1, y1 = bb
    return x0 >= -pad and y0 >= -pad and x1 <= W + pad and y1 <= H + pad


# Mounting holes: square silk keepout (half-side mm) is the body for clearance
HOLE_REFS = {"M1", "M2", "M3", "M4"}
HOLE_KEEP_HALF = 3.0  # 6×6 mm square around each M2 hole
# Edge connectors: F.CrtYd includes the mating plug — pack on silk/fab outline
EDGE_BODY_OUTLINE = {"J_PWR", "J_STEP1", "J_STEP2", "J_DC", "J_USB", "J_BAT"}
BODY_CLEAR_MM = 1.0  # keep-away between component outlines
PAD_OVERLAP_MM2 = 0.25


def inflate(bb: tuple, d: float) -> tuple[float, float, float, float]:
    return (bb[0] - d, bb[1] - d, bb[2] + d, bb[3] + d)


def hole_keepout_square(fx: float, fy: float) -> tuple[float, float, float, float]:
    h = HOLE_KEEP_HALF
    return (fx - h, fy - h, fx + h, fy + h)


def parse_footprints(text: str):
    parts = re.split(r"(?=\(footprint )", text)
    for part in parts:
        if not part.lstrip().startswith("(footprint"):
            continue
        ref_m = re.search(r'\(property "Reference" "([^"]+)"', part)
        at_m = re.search(r"\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)", part)
        if not ref_m or not at_m:
            continue
        # first (at ...) after footprint header is placement
        yield (
            ref_m.group(1),
            float(at_m.group(1)),
            float(at_m.group(2)),
            float(at_m.group(3) or 0),
            part,
        )


def footprint_pad_boxes(ref, fx, fy, fang, body):
    boxes = []
    # single-line pads: (pad "1" smd rect (at -9.525 0) (size 1.6 3.2)
    for m in re.finditer(
        r'\(pad "([^"]*)"[^(\n]*\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)\s*\(size ([-\d.]+) ([-\d.]+)\)',
        body,
    ):
        lx, ly = float(m.group(2)), float(m.group(3))
        sx, sy = float(m.group(5)), float(m.group(6))
        bx, by = board_xy(fx, fy, fang, lx, ly)
        if abs(abs(fang) % 180 - 90) < 1:
            sx, sy = sy, sx
        boxes.append(
            (
                f"pad:{ref}.{m.group(1) or 'NP'}",
                (bx - sx / 2, by - sy / 2, bx + sx / 2, by + sy / 2),
            )
        )
    # multiline pads
    for m in re.finditer(
        r'\(pad "([^"]*)"[^\n]*\n\s*\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)\n\s*\(size ([-\d.]+) ([-\d.]+)\)',
        body,
    ):
        lx, ly = float(m.group(2)), float(m.group(3))
        sx, sy = float(m.group(5)), float(m.group(6))
        bx, by = board_xy(fx, fy, fang, lx, ly)
        if abs(abs(fang) % 180 - 90) < 1:
            sx, sy = sy, sx
        base = f"pad:{ref}.{m.group(1) or 'NP'}"
        # Duplicate pad numbers (e.g. two MP) keep distinct entries.
        n_dup = sum(1 for n, _ in boxes if n == base or n.startswith(base + "#"))
        name = base if n_dup == 0 else f"{base}#{n_dup}"
        boxes.append(
            (name, (bx - sx / 2, by - sy / 2, bx + sx / 2, by + sy / 2))
        )
    return boxes


def footprint_layer_bbox(fx, fy, fang, body, layer: str):
    """BBox of fp_line / fp_rect on ``layer``.

    Split per graphic so the layer tag cannot be taken from a later object
    (that bug mapped F.CrtYd extents onto F.Fab for USB).
    """
    pts: list[tuple[float, float]] = []
    for part in re.split(r"(?=\(fp_(?:line|rect)\b)", body):
        if part.startswith("(fp_line"):
            kind = "line"
        elif part.startswith("(fp_rect"):
            kind = "rect"
        else:
            continue
        # Only the first layer tag in this graphic
        lay_m = re.search(r'\(layer "([^"]+)"\)', part)
        if not lay_m or lay_m.group(1) != layer:
            continue
        sm = re.search(
            r"\(start ([-\d.]+) ([-\d.]+)\)\s*\(end ([-\d.]+) ([-\d.]+)\)",
            part,
        )
        if not sm:
            sm = re.search(
                r"\(start ([-\d.]+) ([-\d.]+)\)\s*\n\s*\(end ([-\d.]+) ([-\d.]+)\)",
                part,
            )
        if not sm:
            continue
        x0, y0, x1, y1 = map(float, sm.groups())
        if kind == "line":
            pts.append(board_xy(fx, fy, fang, x0, y0))
            pts.append(board_xy(fx, fy, fang, x1, y1))
        else:
            for lx, ly in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
                pts.append(board_xy(fx, fy, fang, lx, ly))
    if not pts:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def main() -> int:
    text = PCB.read_text()
    texts: list[tuple[str, tuple]] = []
    solids: list[tuple[str, tuple]] = []

    for m in re.finditer(
        r'\(gr_text "([^"]+)"\n\s+\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)\n\s+\(layer "([^"]+)"\)[\s\S]*?\(size ([-\d.]+)',
        text,
    ):
        label = m.group(1)
        x, y = float(m.group(2)), float(m.group(3))
        ang = float(m.group(4) or 0)
        layer = m.group(5)
        size = float(m.group(6))
        # Front copper/silk keep-away only; back silk is a different plane.
        if layer != "F.SilkS":
            continue
        texts.append((f"gr:{label}", text_bbox(x, y, label, size, ang)))

    fps = list(parse_footprints(text))
    bodies: list[tuple[str, tuple]] = []
    for ref, fx, fy, fang, body in fps:
        stem = ref_stem(ref)
        # Reference on silk
        hide = False
        rm = re.search(
            r'\(property "Reference" "'
            + re.escape(ref)
            + r'"[\s\S]*?\(layer "F\.SilkS"\)([\s\S]*?)(?=\n\t\(property|\n\t\(fp_|\n\t\(pad|\n\))',
            body,
        )
        if rm:
            block = rm.group(0)
            hide = "(hide yes)" in block
            if not hide:
                am = re.search(r"\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)", block)
                sm = re.search(r"\(size ([-\d.]+)", block)
                if am:
                    lx, ly = float(am.group(1)), float(am.group(2))
                    prop_ang = float(am.group(3) or 0)
                    bx, by = board_xy(fx, fy, fang, lx, ly)
                    size = float(sm.group(1)) if sm else 1.0
                    texts.append(
                        (f"ref:{ref}", text_bbox(bx, by, ref, size, fang + prop_ang))
                    )

        solids.extend(footprint_pad_boxes(ref, fx, fy, fang, body))
        for layer in ("F.SilkS", "F.Fab"):
            bb = footprint_layer_bbox(fx, fy, fang, body, layer)
            if bb:
                solids.append((f"{layer}:{ref}", bb))
        # Body for outline keep-away = physical outline (F.Fab), not IPC courtyard
        # (courtyard already embeds margin; 1 mm is extra between outlines).
        # Edge TE: F.Fab is line stubs — use F.SilkS rect. Holes: square keepout.
        if ref in HOLE_REFS:
            body_bb = hole_keepout_square(fx, fy)
            solids.append((f"keepout:{ref}", body_bb))
        elif stem in EDGE_BODY_OUTLINE:
            # Edge connectors: F.Fab often spans the mating plug — pack on silk.
            body_bb = footprint_layer_bbox(fx, fy, fang, body, "F.SilkS")
            if body_bb is None:
                body_bb = footprint_layer_bbox(fx, fy, fang, body, "F.Fab")
            if body_bb is None:
                pads = footprint_pad_boxes(ref, fx, fy, fang, body)
                if pads:
                    xs0, ys0, xs1, ys1 = zip(*[b for _, b in pads])
                    body_bb = (min(xs0), min(ys0), max(xs1), max(ys1))
        else:
            body_bb = footprint_layer_bbox(fx, fy, fang, body, "F.Fab")
            if body_bb is None:
                body_bb = footprint_layer_bbox(fx, fy, fang, body, "F.SilkS")
            if body_bb is None:
                pads = footprint_pad_boxes(ref, fx, fy, fang, body)
                if pads:
                    xs0, ys0, xs1, ys1 = zip(*[b for _, b in pads])
                    body_bb = (min(xs0), min(ys0), max(xs1), max(ys1))
        if body_bb is not None:
            bodies.append((ref, body_bb))

    off = []
    for n, bb in texts:
        if not on_board(bb):
            off.append(f"TEXT {n} bb=({bb[0]:.2f},{bb[1]:.2f},{bb[2]:.2f},{bb[3]:.2f})")
    for n, bb in solids:
        if n.startswith("pad:") and not on_board(bb):
            off.append(f"PAD {n} x0={bb[0]:.2f}")
        elif n.startswith("F.SilkS:") and not on_board(bb):
            off.append(f"FOOT {n} x0={bb[0]:.2f}")
        elif n.startswith("F.Fab:"):
            # Edge connector F.Fab often draws the plug past Edge.Cuts — not a fab fail.
            foot_ref = n.split(":", 1)[1]
            if ref_stem(foot_ref) in EDGE_BODY_OUTLINE:
                continue
            if not on_board(bb):
                off.append(f"FOOT {n} x0={bb[0]:.2f}")
    # Pads and F.SilkS must stay on-board. Edge F.Fab plug outlines may overhang.

    hits = []
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            if overlaps(texts[i][1], texts[j][1]):
                hits.append(f"{texts[i][0]} × {texts[j][0]}")
    for tn, tb in texts:
        for sn, sb in solids:
            if overlaps(tb, sb):
                hits.append(f"{tn} × {sn}")

    # Outline keep-away: inflate each body by half the clearance and require no overlap.
    half = BODY_CLEAR_MM / 2.0
    body_hits = []
    for i, (ra, ba) in enumerate(bodies):
        ia = inflate(ba, half)
        for rb, bb in bodies[i + 1 :]:
            if overlap_area(ia, inflate(bb, half)) > 0.0:
                raw = overlap_area(ba, bb)
                body_hits.append(
                    f"body:{ra} × body:{rb} (clear<{BODY_CLEAR_MM:g}mm"
                    + (f", overlap {raw:.1f}mm²" if raw > 0 else "")
                    + ")"
                )

    # Copper pad × pad across footprints (catches hole vs TE pad, etc.)
    pads_only = [(n, b) for n, b in solids if n.startswith("pad:")]
    for i, (na, ba) in enumerate(pads_only):
        ref_a = na.split(":", 1)[1].split(".", 1)[0]
        for nb, bb in pads_only[i + 1 :]:
            ref_b = nb.split(":", 1)[1].split(".", 1)[0]
            if ref_a == ref_b:
                continue
            area = overlap_area(ba, bb)
            if area >= PAD_OVERLAP_MM2:
                body_hits.append(f"pad:{ref_a} × pad:{ref_b} ({area:.1f}mm²)")

    # de-dupe
    hits = sorted(set(hits))
    body_hits = sorted(set(body_hits))
    off = sorted(set(off))

    print(f"footprints: {len(fps)}  silk texts: {len(texts)}  solids: {len(solids)}  bodies: {len(bodies)}")
    if off:
        print("OFF BOARD:")
        for n in off:
            print(f"  {n}")
    else:
        print("OFF BOARD: none")
    if hits:
        print(f"COLLISIONS ({len(hits)}):")
        for h in hits[:80]:
            print(f"  {h}")
        if len(hits) > 80:
            print(f"  ... +{len(hits) - 80} more")
    else:
        print("COLLISIONS: none")
    if body_hits:
        print(f"BODY COLLISIONS ({len(body_hits)}):")
        for h in body_hits[:80]:
            print(f"  {h}")
        if len(body_hits) > 80:
            print(f"  ... +{len(body_hits) - 80} more")
    else:
        print("BODY COLLISIONS: none")
    return 1 if off or hits or body_hits else 0


if __name__ == "__main__":
    sys.exit(main())
