#!/usr/bin/env bash
# Export Specctra DSN → Freerouting (ignore GND via freerouting.json) → import SES.
# Prefers locked copper from tools/route_tmc_local.py.
#
# Usage (repo root):
#   tools/freeroute_rest.sh
#   tools/freeroute_rest.sh hardware/exports/adeptbt_tmc_local
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STEM="${1:-hardware/exports/adeptbt_tmc_local}"
DSN="$ROOT/${STEM}.dsn"
SES="$ROOT/${STEM}.ses"
LOG="$ROOT/${STEM}.freeroute.log"
PCB="$ROOT/hardware/adeptbt.kicad_pcb"
KPY="/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3"
JAVA="${JAVA_HOME:+$JAVA_HOME/bin/java}"
if [[ -z "${JAVA:-}" || ! -x "$JAVA" ]]; then
  if [[ -x /opt/homebrew/opt/openjdk@27/bin/java ]]; then
    JAVA=/opt/homebrew/opt/openjdk@27/bin/java
  else
    JAVA="$(command -v java)"
  fi
fi
JAR="$ROOT/tools/freerouting/freerouting-2.5.0.jar"

mkdir -p "$(dirname "$DSN")"
"$KPY" - <<PY
import pcbnew
from pathlib import Path
board = pcbnew.LoadBoard(r"$PCB")
ok = pcbnew.ExportSpecctraDSN(board, r"$DSN")
raise SystemExit(0 if ok else 1)
PY

"$JAVA" -jar "$JAR" \
  -de "$DSN" \
  -do "$SES" \
  --router.autorouter.max_passes=40 \
  --gui.enabled=false \
  2>&1 | tee "$LOG"

"$KPY" - <<PY
import pcbnew
from pathlib import Path
pcb = Path(r"$PCB")
ses = Path(r"$SES")
board = pcbnew.LoadBoard(str(pcb))
ok = pcbnew.ImportSpecctraSES(board, str(ses))
pcbnew.SaveBoard(str(pcb), board)
print(f"import SES ok={ok} tracks={len(list(board.GetTracks()))}")
PY
