#!/usr/bin/env python3
"""Dump footprint placements from hardware/adeptbt.kicad_pcb.

Read-only. The board file is owned by pcbnew; do not feed this into
tools/gen_adeptbt_pcb.py (that script is stopped).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PCB = ROOT / "hardware" / "adeptbt.kicad_pcb"


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else PCB
    text = path.read_text()
    refs: list[tuple[str, float, float, float]] = []
    for part in re.split(r"(?=\(footprint )", text):
        if not part.lstrip().startswith("(footprint"):
            continue
        ref_m = re.search(r'\(property "Reference" "([^"]+)"', part)
        at_m = re.search(r"\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)", part)
        if not ref_m or not at_m:
            continue
        refs.append(
            (
                ref_m.group(1),
                float(at_m.group(1)),
                float(at_m.group(2)),
                float(at_m.group(3) or 0),
            )
        )
    refs.sort(key=lambda r: r[0])
    for ref, x, y, ang in refs:
        print(f"{ref:8s} {x:8.3f} {y:8.3f} ang={ang:g}")
    print(f"# {len(refs)} footprints from {path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
