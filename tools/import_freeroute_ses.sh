#!/usr/bin/env bash
# Import Freerouting SES into the PCB (after tools/freeroute_gui.sh).
#
#   tools/import_freeroute_ses.sh [path/to.ses]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KPY="/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3"
PCB="$ROOT/hardware/adeptbt.kicad_pcb"
SES="${1:-$ROOT/hardware/exports/adeptbt_after_gnd_vias.ses}"

"$KPY" - <<PY
import pcbnew
import re
from pathlib import Path
pcb = Path(r"$PCB")
ses = Path(r"$SES")
if not ses.exists() or ses.stat().st_size < 100:
    raise SystemExit(f"missing/empty SES: {ses}")
board = pcbnew.LoadBoard(str(pcb))
ok = pcbnew.ImportSpecctraSES(board, str(ses))
pcbnew.SaveBoard(str(pcb), board)
text = pcb.read_text()
m = re.search(r'\(rev "([0-9]+)\.([0-9]+)"\)', text)
new = f"{int(m.group(1))}.{int(m.group(2)) + 1}"
text = text.replace(f'(rev "{m.group(1)}.{m.group(2)}")', f'(rev "{new}")', 1)
text = re.sub(r'\(gr_text "AdeptBT rev [0-9.]+"', f'(gr_text "AdeptBT rev {new}"', text, count=1)
pcb.write_text(text)
print(f"import SES ok={ok} tracks={len(list(board.GetTracks()))} rev={new} ← {ses}")
PY
