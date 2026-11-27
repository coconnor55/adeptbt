#!/usr/bin/env bash
# From wiped copper: GND pad vias only → Freeroute all signal nets (ignore GND).
# No scripted/locked signal stubs.
#
# NOTE: -de/-do forces Freerouting **batch** mode; the GUI flashes and exits.
# To watch routing: after vias, use tools/freeroute_gui.sh (no -do), then
# tools/import_freeroute_ses.sh when you have saved a .ses.
#
#   tools/wipe_vias_freeroute.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KPY="/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3"
JAVA="${JAVA_HOME:+$JAVA_HOME/bin/java}"
if [[ -z "${JAVA:-}" || ! -x "${JAVA}" ]]; then
  if [[ -x /opt/homebrew/opt/openjdk@27/bin/java ]]; then
    JAVA=/opt/homebrew/opt/openjdk@27/bin/java
  else
    JAVA="$(command -v java)"
  fi
fi
JAR="$ROOT/tools/freerouting/freerouting-2.5.0.jar"
PCB="$ROOT/hardware/adeptbt.kicad_pcb"
STEM="$ROOT/hardware/exports/adeptbt_after_gnd_vias"
DSN="${STEM}.dsn"
SES="${STEM}.ses"
LOG="${STEM}.freeroute.log"

"$KPY" "$ROOT/tools/gnd_pad_vias.py" --wipe

"$KPY" - <<PY
import pcbnew
import re
from pathlib import Path
board = pcbnew.LoadBoard(r"$PCB")
ok = pcbnew.ExportSpecctraDSN(board, r"$DSN")
path = Path(r"$DSN")
text = path.read_text()
# KiCad exports dual names like "Signal,GND" / "PowerMotor,Signal". Freerouting
# ignore_net_classes matches the full class token; prefer a clean primary name.
rewrites = (
    ("(class Signal,GND ", "(class GND "),
    ("(class PowerMotor,Signal ", "(class PowerMotor "),
    ("(class PowerHV,Signal ", "(class PowerHV "),
    ("(class PowerLV,Signal ", "(class PowerLV "),
    ("(class Signal,Analog ", "(class Analog "),
)
for a, b in rewrites:
    text = text.replace(a, b)
path.write_text(text)
if not re.search(r'\(class GND[\s]', text):
    raise SystemExit(
        "DSN has no '(class GND' after rewrite — cannot ignore GND. "
        "Confirm adeptbt.kicad_pro has netclass GND + pattern GND (before *)."
    )
print(f"DSN ok={ok}; class GND ready for ignore_net_classes", flush=True)
raise SystemExit(0 if ok else 1)
PY

echo "Freerouting (GUI) — watch the window; GND ignored; PowerMotor 0.8 mm; vias locked."
echo "Close the Freerouting window when finished to import the SES."
"$JAVA" -jar "$JAR" \
  -de "$DSN" \
  -do "$SES" \
  --router.autorouter.max_passes=80 \
  --gui.enabled=true \
  2>&1 | tee "$LOG"

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
print(f"import SES ok={ok} tracks={len(list(board.GetTracks()))} rev={new}")
PY

echo "Next (optional): KiCad Python tools/pour_gnd.py — then DRC."