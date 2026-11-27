#!/usr/bin/env bash
# Open Freerouting GUI on the post-via DSN and leave it open (no batch -do).
# Watch the route, then File → Save as … .ses (or Export Specctra Session).
# After you save + quit, run: tools/import_freeroute_ses.sh
#
#   tools/freeroute_gui.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
JAVA="${JAVA_HOME:+$JAVA_HOME/bin/java}"
if [[ -z "${JAVA:-}" || ! -x "${JAVA}" ]]; then
  if [[ -x /opt/homebrew/opt/openjdk@27/bin/java ]]; then
    JAVA=/opt/homebrew/opt/openjdk@27/bin/java
  else
    JAVA="$(command -v java)"
  fi
fi
JAR="$ROOT/tools/freerouting/freerouting-2.5.0.jar"
DSN="$ROOT/hardware/exports/adeptbt_after_gnd_vias.dsn"

if [[ ! -f "$DSN" ]]; then
  echo "missing $DSN — run tools/gnd_pad_vias.py --wipe and export DSN first" >&2
  exit 1
fi

# Ensure class names Freerouting can ignore / widen (incl. GND not under Signal)
export DSN_PATH="$DSN"
python3 - <<'PY'
from pathlib import Path
import re
import os
p = Path(os.environ["DSN_PATH"])
t = p.read_text()
for a, b in (
    ("(class Signal,GND ", "(class GND "),
    ("(class PowerMotor,Signal ", "(class PowerMotor "),
    ("(class PowerHV,Signal ", "(class PowerHV "),
    ("(class PowerLV,Signal ", "(class PowerLV "),
    ("(class Signal,Analog ", "(class Analog "),
):
    t = t.replace(a, b)
if not re.search(r"\(class GND[\s]", t):
    m = re.search(
        r"\(class Signal\b(.*?)\n      \(circuit\n(.*?)\n      \(rule\n(.*?)\n      \)\n    \)",
        t,
        re.S,
    )
    if not m:
        raise SystemExit("DSN: cannot split GND out of Signal class")
    nets = re.sub(r"(?<![\w-])GND(?![\w-])", "", m.group(1))
    nets = re.sub(r"  +", " ", nets)
    signal = (
        f"(class Signal{nets}\n"
        f"      (circuit\n{m.group(2)}\n"
        f"      (rule\n{m.group(3)}\n"
        f"      )\n"
        f"    )"
    )
    gnd = (
        "(class GND GND\n"
        "      (circuit\n"
        '        (use_via "Via[0-3]_600:300_um")\n'
        "      )\n"
        "      (rule\n"
        "        (width 250)\n"
        "        (clearance 200)\n"
        "      )\n"
        "    )"
    )
    t = t[: m.start()] + gnd + "\n    " + signal + t[m.end() :]
p.write_text(t)
if not re.search(r"\(class GND[\s]", t):
    raise SystemExit("DSN still missing class GND")
print("DSN class names OK (GND + PowerMotor):", p)
PY

echo "Opening Freerouting GUI (stays open — no batch -do)."
echo "Start autorouter from the UI. Save a .ses when done, then quit."
echo "SES path suggestion: $ROOT/hardware/exports/adeptbt_after_gnd_vias.ses"
exec "$JAVA" -jar "$JAR" \
  -de "$DSN" \
  --gui.enabled=true
