#!/usr/bin/env python3
"""Generate AdeptBT KiCad 8 PCB + companion schematic skeleton."""

from __future__ import annotations

import uuid
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "hardware"

# Credit-card outline (mm)
W, H = 85.6, 53.98
M2_R = 1.1  # hole radius ~2.2 mm dia
EDGE = 3.5  # M2 hole center from edges


def uid() -> str:
    return str(uuid.uuid4())


def rect_outline(w: float, h: float) -> str:
    return f"""  (gr_rect
    (start 0 0)
    (end {w} {h})
    (stroke (width 0.15) (type solid))
    (fill none)
    (layer "Edge.Cuts")
    (uuid "{uid()}")
  )"""


def mounting_hole(x: float, y: float, ref: str) -> str:
    # Simplified NPTH hole as footprint-like pad via gr_circle + hole in Edge? 
    # Use standard MountingHole footprint inline as via-less pad circle on Edge + Dwgs
    return f"""  (footprint "MountingHole:MountingHole_2.2mm_M2"
    (layer "F.Cu")
    (uuid "{uid()}")
    (at {x} {y})
    (property "Reference" "{ref}"
      (at 0 2.5 0)
      (layer "F.SilkS")
      (uuid "{uid()}")
      (effects (font (size 0.8 0.8) (thickness 0.12)))
    )
    (property "Value" "M2"
      (at 0 -2.5 0)
      (layer "F.Fab")
      (uuid "{uid()}")
      (effects (font (size 0.7 0.7) (thickness 0.1)))
    )
    (property "Footprint" "MountingHole:MountingHole_2.2mm_M2"
      (at 0 0 0)
      (layer "F.Fab")
      (hide yes)
      (uuid "{uid()}")
      (effects (font (size 1 1) (thickness 0.15)))
    )
    (attr board_only exclude_from_pos_files exclude_from_bom)
    (pad "" np_thru_hole circle
      (at 0 0)
      (size 2.2 2.2)
      (drill 2.2)
      (layers "*.Cu" "*.Mask")
      (uuid "{uid()}")
    )
  )"""


def silk_text(x: float, y: float, text: str, size: float = 1.0, angle: float = 0) -> str:
    return f"""  (gr_text "{text}"
    (at {x} {y} {angle})
    (layer "F.SilkS")
    (uuid "{uid()}")
    (effects (font (size {size} {size}) (thickness {size * 0.15})) (justify left bottom))
  )"""


def silk_text_c(x: float, y: float, text: str, size: float = 1.0, angle: float = 0) -> str:
    return f"""  (gr_text "{text}"
    (at {x} {y} {angle})
    (layer "F.SilkS")
    (uuid "{uid()}")
    (effects (font (size {size} {size}) (thickness {size * 0.15})) (justify center))
  )"""


def terminal_6pin(x: float, y: float, ref: str, labels: list[str], angle: float = 0) -> str:
    """Approximate Phoenix MKDS 1/6-3.81 SMD — 6 pads at 3.81 mm, body ~7.5 mm deep."""
    pitch = 3.81
    pad_w, pad_h = 2.0, 2.8
    body_w = pitch * 5 + 4.0
    body_d = 7.5
    pads = []
    silk = []
    for i in range(6):
        px = (i - 2.5) * pitch
        pads.append(
            f"""    (pad "{i+1}" smd rect
      (at {px:.3f} 0)
      (size {pad_w} {pad_h})
      (layers "F.Cu" "F.Paste" "F.Mask")
      (uuid "{uid()}")
    )"""
        )
        silk.append(
            f"""    (fp_text user "{labels[i]}"
      (at {px:.3f} {-pad_h/2 - 1.1:.3f} 0)
      (layer "F.SilkS")
      (uuid "{uid()}")
      (effects (font (size 0.65 0.65) (thickness 0.08)) (justify center))
    )"""
        )
    return f"""  (footprint "AdeptBT:Terminal_Screw_1x06_P3.81mm_SMD"
    (layer "F.Cu")
    (uuid "{uid()}")
    (at {x} {y} {angle})
    (property "Reference" "{ref}"
      (at 0 {body_d/2 + 1.5:.2f} 0)
      (layer "F.SilkS")
      (uuid "{uid()}")
      (effects (font (size 1 1) (thickness 0.15)))
    )
    (property "Value" "MKDS_1x6"
      (at 0 {body_d/2 + 2.8:.2f} 0)
      (layer "F.Fab")
      (uuid "{uid()}")
      (effects (font (size 0.8 0.8) (thickness 0.1)))
    )
    (property "Footprint" "AdeptBT:Terminal_Screw_1x06_P3.81mm_SMD"
      (at 0 0 0)
      (layer "F.Fab")
      (hide yes)
      (uuid "{uid()}")
      (effects (font (size 1 1) (thickness 0.15)))
    )
    (attr smd)
    (fp_rect
      (start {-body_w/2:.2f} {-body_d/2:.2f})
      (end {body_w/2:.2f} {body_d/2:.2f})
      (stroke (width 0.12) (type solid))
      (fill none)
      (layer "F.SilkS")
      (uuid "{uid()}")
    )
    (fp_rect
      (start {-body_w/2 - 0.25:.2f} {-body_d/2 - 0.25:.2f})
      (end {body_w/2 + 0.25:.2f} {body_d/2 + 0.25:.2f})
      (stroke (width 0.05) (type solid))
      (fill none)
      (layer "F.CrtYd")
      (uuid "{uid()}")
    )
{chr(10).join(pads)}
{chr(10).join(silk)}
  )"""


def header(x: float, y: float, ref: str, n: int, labels: list[str], angle: float = 0) -> str:
    pitch = 2.54
    pads = []
    for i in range(n):
        py = (i - (n - 1) / 2) * pitch
        pads.append(
            f"""    (pad "{i+1}" thru_hole circle
      (at 0 {py:.3f})
      (size 1.7 1.7)
      (drill 1.0)
      (layers "*.Cu" "*.Mask")
      (uuid "{uid()}")
    )"""
        )
    return f"""  (footprint "Connector_PinHeader_2.54mm:PinHeader_1x{n:02d}_P2.54mm_Vertical"
    (layer "F.Cu")
    (uuid "{uid()}")
    (at {x} {y} {angle})
    (property "Reference" "{ref}"
      (at 2.5 0 0)
      (layer "F.SilkS")
      (uuid "{uid()}")
      (effects (font (size 0.9 0.9) (thickness 0.12)) (justify left))
    )
    (property "Value" "{'-'.join(labels)}"
      (at -2.8 0 0)
      (layer "F.Fab")
      (uuid "{uid()}")
      (effects (font (size 0.6 0.6) (thickness 0.08)) (justify right))
    )
    (property "Footprint" "PinHeader_1x{n:02d}"
      (at 0 0 0)
      (layer "F.Fab")
      (hide yes)
      (uuid "{uid()}")
      (effects (font (size 1 1) (thickness 0.15)))
    )
    (attr through_hole)
{chr(10).join(pads)}
  )"""


def module_mdbt50q(x: float, y: float) -> str:
    """Castellated approximation 15.5 x 10.5 mm — keepout silk for antenna end."""
    bw, bh = 15.5, 10.5
    return f"""  (footprint "AdeptBT:Raytac_MDBT50Q"
    (layer "F.Cu")
    (uuid "{uid()}")
    (at {x} {y})
    (property "Reference" "U1"
      (at 0 {-bh/2 - 1.5:.2f} 0)
      (layer "F.SilkS")
      (uuid "{uid()}")
      (effects (font (size 1 1) (thickness 0.15)))
    )
    (property "Value" "MDBT50Q-1MV2"
      (at 0 {bh/2 + 1.5:.2f} 0)
      (layer "F.Fab")
      (uuid "{uid()}")
      (effects (font (size 0.8 0.8) (thickness 0.1)))
    )
    (property "Footprint" "AdeptBT:Raytac_MDBT50Q"
      (at 0 0 0)
      (layer "F.Fab")
      (hide yes)
      (uuid "{uid()}")
      (effects (font (size 1 1) (thickness 0.15)))
    )
    (attr smd)
    (fp_rect
      (start {-bw/2} {-bh/2})
      (end {bw/2} {bh/2})
      (stroke (width 0.12) (type solid))
      (fill none)
      (layer "F.SilkS")
      (uuid "{uid()}")
    )
    (fp_text user "ANT keepout"
      (at {bw/2 + 4} 0 90)
      (layer "F.SilkS")
      (uuid "{uid()}")
      (effects (font (size 0.7 0.7) (thickness 0.1)))
    )
    (pad "1" smd rect (at {-bw/2} -4) (size 1.2 0.8) (layers "F.Cu" "F.Paste" "F.Mask") (uuid "{uid()}"))
    (pad "2" smd rect (at {-bw/2} -2) (size 1.2 0.8) (layers "F.Cu" "F.Paste" "F.Mask") (uuid "{uid()}"))
    (pad "3" smd rect (at {-bw/2} 0) (size 1.2 0.8) (layers "F.Cu" "F.Paste" "F.Mask") (uuid "{uid()}"))
    (pad "4" smd rect (at {-bw/2} 2) (size 1.2 0.8) (layers "F.Cu" "F.Paste" "F.Mask") (uuid "{uid()}"))
    (pad "5" smd rect (at {-bw/2} 4) (size 1.2 0.8) (layers "F.Cu" "F.Paste" "F.Mask") (uuid "{uid()}"))
  )"""


def tmc2209(x: float, y: float, ref: str) -> str:
    s = 5.0  # QFN-28 ~5x5
    return f"""  (footprint "Package_DFN_QFN:QFN-28-1EP_5x5mm_P0.5mm"
    (layer "F.Cu")
    (uuid "{uid()}")
    (at {x} {y})
    (property "Reference" "{ref}"
      (at 0 -4 0)
      (layer "F.SilkS")
      (uuid "{uid()}")
      (effects (font (size 0.9 0.9) (thickness 0.12)))
    )
    (property "Value" "TMC2209"
      (at 0 4 0)
      (layer "F.Fab")
      (uuid "{uid()}")
      (effects (font (size 0.7 0.7) (thickness 0.1)))
    )
    (property "Footprint" "QFN-28"
      (at 0 0 0)
      (layer "F.Fab")
      (hide yes)
      (uuid "{uid()}")
      (effects (font (size 1 1) (thickness 0.15)))
    )
    (attr smd)
    (fp_rect
      (start {-s/2} {-s/2})
      (end {s/2} {s/2})
      (stroke (width 0.12) (type solid))
      (fill none)
      (layer "F.SilkS")
      (uuid "{uid()}")
    )
    (pad "29" smd rect (at 0 0) (size 3.2 3.2) (layers "F.Cu" "F.Paste" "F.Mask") (uuid "{uid()}"))
  )"""


def usbc(x: float, y: float) -> str:
    return f"""  (footprint "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12"
    (layer "F.Cu")
    (uuid "{uid()}")
    (at {x} {y} 270)
    (property "Reference" "J_USB"
      (at 0 -6 270)
      (layer "F.SilkS")
      (uuid "{uid()}")
      (effects (font (size 0.9 0.9) (thickness 0.12)))
    )
    (property "Value" "USB-C"
      (at 0 6 270)
      (layer "F.Fab")
      (uuid "{uid()}")
      (effects (font (size 0.8 0.8) (thickness 0.1)))
    )
    (property "Footprint" "USB_C"
      (at 0 0 0)
      (layer "F.Fab")
      (hide yes)
      (uuid "{uid()}")
      (effects (font (size 1 1) (thickness 0.15)))
    )
    (attr smd)
    (fp_rect
      (start -4.5 -4)
      (end 4.5 4)
      (stroke (width 0.12) (type solid))
      (fill none)
      (layer "F.SilkS")
      (uuid "{uid()}")
    )
  )"""


def jst_ph(x: float, y: float) -> str:
    return f"""  (footprint "Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal"
    (layer "F.Cu")
    (uuid "{uid()}")
    (at {x} {y})
    (property "Reference" "J_BAT"
      (at 0 -3.5 0)
      (layer "F.SilkS")
      (uuid "{uid()}")
      (effects (font (size 0.8 0.8) (thickness 0.1)))
    )
    (property "Value" "BAT"
      (at 0 3.5 0)
      (layer "F.Fab")
      (uuid "{uid()}")
      (effects (font (size 0.7 0.7) (thickness 0.1)))
    )
    (property "Footprint" "JST_PH"
      (at 0 0 0)
      (layer "F.Fab")
      (hide yes)
      (uuid "{uid()}")
      (effects (font (size 1 1) (thickness 0.15)))
    )
    (attr smd)
    (pad "1" smd rect (at -1 0) (size 1.0 3.0) (layers "F.Cu" "F.Paste" "F.Mask") (uuid "{uid()}"))
    (pad "2" smd rect (at 1 0) (size 1.0 3.0) (layers "F.Cu" "F.Paste" "F.Mask") (uuid "{uid()}"))
    (fp_text user "+" (at -1 -2.2) (layer "F.SilkS") (uuid "{uid()}")
      (effects (font (size 0.8 0.8) (thickness 0.12))))
    (fp_text user "-" (at 1 -2.2) (layer "F.SilkS") (uuid "{uid()}")
      (effects (font (size 0.8 0.8) (thickness 0.12))))
  )"""


def build_pcb() -> str:
    # Layout (origin top-left, Y down in KiCad typically from top):
    # Long edge Y=0: steppers (into board +Y)
    # Long edge Y=H: power/outs (into board -Y) — place near H
    # Short edge X=0: USB-C
    # Center: U1, U2, U3, power

    step_labels = ["A1", "A2", "B1", "B2", "VM", "GND"]
    pwr_labels = ["VIN", "GND", "V+", "OUT1", "V+", "OUT2"]
    an_labels = ["AIN0", "AIN1", "AIN2", "AIN3", "3V3", "5V", "GND"]
    dg_labels = ["D0", "D1", "D2", "D3", "3V3", "GND"]
    swd_labels = ["SWDIO", "SWCLK", "GND", "3V3", "RST"]

    # Terminal centers: body depth ~7.5 → pad row ~3.5 from edge
    y_step = 4.0
    y_pwr = H - 4.0
    # Two steppers along top long edge
    x_s1 = 22.0
    x_s2 = 58.0
    x_pwr = W / 2

    parts = [
        rect_outline(W, H),
        mounting_hole(EDGE, EDGE, "H1"),
        mounting_hole(W - EDGE, EDGE, "H2"),
        mounting_hole(EDGE, H - EDGE, "H3"),
        mounting_hole(W - EDGE, H - EDGE, "H4"),
        silk_text_c(W / 2, H / 2 - 8, "AdeptBT", 2.2),
        silk_text_c(W / 2, H / 2 - 5.5, "coconnor55", 1.0),
        silk_text(2, y_step + 6, "STEPPER1", 0.9),
        silk_text(2, y_step + 7.5, "A1 A2 B1 B2 VM GND", 0.7),
        silk_text(45, y_step + 6, "STEPPER2", 0.9),
        silk_text(2, y_pwr - 7, "PWR/OUT", 0.9),
        silk_text(2, y_pwr - 8.5, "VIN GND V+ OUT1 V+ OUT2", 0.7),
        silk_text(2, 20, "USB-C", 0.8, 90),
        terminal_6pin(x_s1, y_step, "J_STEP1", step_labels, 0),
        terminal_6pin(x_s2, y_step, "J_STEP2", step_labels, 0),
        terminal_6pin(x_pwr, y_pwr, "J_PWR", pwr_labels, 180),
        usbc(1.5, H / 2),
        module_mdbt50q(42, 28),
        tmc2209(22, 22, "U2"),
        tmc2209(22, 34, "U3"),
        jst_ph(70, 28),
        header(78, 22, "J_AN", 7, an_labels, 0),
        header(78, 38, "J_DG", 6, dg_labels, 0),
        header(55, 40, "J_SWD", 5, swd_labels, 90),
        silk_text(74, 12, "ANALOG", 0.8),
        silk_text(74, 48, "DIGITAL", 0.8),
        silk_text(48, 48, "SWD", 0.8),
        silk_text(66, 32, "BAT", 0.8),
        # Jumper legends
        silk_text(32, 40, "JP: V+ 3V3/5V/VIN", 0.7),
        silk_text(32, 41.5, "JP: VM1/VM2 to VIN", 0.7),
        silk_text(32, 43, "JP: AIN direct/div5", 0.7),
    ]

    # Layer stack note as comment in file header
    layers = """  (layers
    (0 "F.Cu" signal)
    (1 "In1.Cu" signal)
    (2 "In2.Cu" signal)
    (31 "B.Cu" signal)
    (32 "B.Adhes" user "B.Adhesive")
    (33 "F.Adhes" user "F.Adhesive")
    (34 "B.Paste" user)
    (35 "F.Paste" user)
    (36 "B.SilkS" user "B.Silkscreen")
    (37 "F.SilkS" user "F.Silkscreen")
    (38 "B.Mask" user)
    (39 "F.Mask" user)
    (40 "Dwgs.User" user "User.Drawings")
    (41 "Cmts.User" user "User.Comments")
    (42 "Eco1.User" user "User.Eco1")
    (43 "Eco2.User" user "User.Eco2")
    (44 "Edge.Cuts" user)
    (45 "F.CrtYd" user "F.Courtyard")
    (46 "B.CrtYd" user "B.Courtyard")
    (47 "F.Fab" user)
    (48 "B.Fab" user)
  )"""

    return f"""(kicad_pcb
  (version 20240108)
  (generator "gen_adeptbt_pcb")
  (generator_version "8.0")
  (general
    (thickness 1.6)
    (legacy_teardrops no)
  )
  (paper "A4")
  (title_block
    (title "AdeptBT")
    (date "2026-11-22")
    (rev "0.1")
    (company "coconnor55")
    (comment 1 "Credit-card nRF52840 dual TMC2209")
    (comment 2 "Placeholders: refine footprints from vendor drawings before fab")
  )
{layers}
  (setup
    (pad_to_mask_clearance 0.05)
    (allow_soldermask_bridges_in_footprints no)
    (pcbplotparams
      (layerselection 0x00010fc_ffffffff)
      (plot_on_all_layers_selection 0x0000000_00000000)
      (disableapertmacros no)
      (usegerberextensions no)
      (usegerberattributes yes)
      (usegerberadvancedattributes yes)
      (creategerberjobfile yes)
      (dashed_line_dash_ratio 12.000000)
      (dashed_line_gap_ratio 3.000000)
      (svgprecision 4)
      (plotframeref no)
      (viasonmask no)
      (mode 1)
      (useauxorigin no)
      (hpglpennumber 1)
      (hpglpenspeed 20)
      (hpglpendiameter 15.000000)
      (pdf_front_fp_property_popups yes)
      (pdf_back_fp_property_popups yes)
      (dxfpolygonmode yes)
      (dxfimperialunits yes)
      (dxfusepcbnewfont yes)
      (psnegative no)
      (psa4output no)
      (plotreference yes)
      (plotvalue yes)
      (plotfptext yes)
      (plotinvisibletext no)
      (sketchpadsonfab no)
      (subtractmaskfromsilk no)
      (outputformat 1)
      (mirror no)
      (drillshape 1)
      (scaleselection 1)
      (outputdirectory "gerbers/")
    )
  )
  (net 0 "")
{chr(10).join(parts)}
)
"""


def build_schematic() -> str:
    """Hierarchical-style single-sheet schematic as documentation + symbols placeholders."""
    # KiCad 8 schematic format — keep readable block diagram with text + power ports
    return f"""(kicad_sch
  (version 20231120)
  (generator "gen_adeptbt_pcb")
  (generator_version "8.0")
  (uuid "{uid()}")
  (paper "A3")
  (title_block
    (title "AdeptBT")
    (date "2026-11-22")
    (rev "0.1")
    (company "coconnor55")
    (comment 1 "Functional schematic — wire symbols to footprints in KiCad before fab")
  )
  (lib_symbols)
  (text "AdeptBT — functional schematic (rev 0.1)"
    (exclude_from_sim no) (at 20 10 0)
    (effects (font (size 3 3)) (justify left bottom))
    (uuid "{uid()}")
  )
  (text "POWER\\nUSB-C 5V --OR-- VIN 5-18V (PPTC+P-FET+TVS)\\n  -> Buck 5V\\n  -> Charger 400-500mA -> BAT JST\\n  -> LDO 3.3V -> U1 MDBT50Q-1MV2\\nJumpers: V+ = 3V3|5V|VIN ; VM1/VM2 = VIN|ext"
    (exclude_from_sim no) (at 20 25 0)
    (effects (font (size 1.5 1.5)) (justify left top))
    (uuid "{uid()}")
  )
  (text "MCU U1 Raytac MDBT50Q-1MV2\\nUSB D+/D- from USB-C\\nSWD header\\nUART/STEP/DIR/EN -> U2 U3 TMC2209\\nGPIO -> Q2 Q3 2N2222 (OUT1 OUT2) + flyback\\nAIN0-3 -> analog header (+ dividers)\\nD0-3 -> digital header\\nLEDs: PWR CHG USER"
    (exclude_from_sim no) (at 20 55 0)
    (effects (font (size 1.5 1.5)) (justify left top))
    (uuid "{uid()}")
  )
  (text "MOTION\\nU2 TMC2209 -> J_STEP1 A1 A2 B1 B2 VM GND\\nU3 TMC2209 -> J_STEP2 A1 A2 B1 B2 VM GND\\nVM via jumper to VIN or external (<=24V ext protect)"
    (exclude_from_sim no) (at 140 25 0)
    (effects (font (size 1.5 1.5)) (justify left top))
    (uuid "{uid()}")
  )
  (text "CONNECTORS\\nJ_STEP1/2: 6-pin screw 3.81mm SMD\\nJ_PWR: VIN GND V+ OUT1 V+ OUT2\\nJ_AN: AIN0-3 3V3 5V GND\\nJ_DG: D0-3 3V3 GND\\nJ_BAT: JST-PH\\nJ_USB: USB-C\\nJ_SWD: SWDIO SWCLK GND 3V3 RST"
    (exclude_from_sim no) (at 140 55 0)
    (effects (font (size 1.5 1.5)) (justify left top))
    (uuid "{uid()}")
  )
  (text "See docs/DESIGN.md and docs/BOM.md. Open hardware/adeptbt.kicad_pcb in KiCad 8+,\\nreplace placeholder footprints with vendor parts, complete netlist, pour GND, DRC, then Gerbers."
    (exclude_from_sim no) (at 20 95 0)
    (effects (font (size 1.3 1.3)) (justify left top))
    (uuid "{uid()}")
  )
  (sheet_instances
    (path "/" (page "1"))
  )
)
"""


def build_pro() -> str:
    return """{
  "board": {
    "design_settings": {
      "defaults": {},
      "diff_pair_dimensions": [],
      "drc_exclusions": [],
      "rules": {},
      "track_widths": [],
      "via_dimensions": []
    },
    "layers": [
      ["F.Cu", 0],
      ["In1.Cu", 1],
      ["In2.Cu", 2],
      ["B.Cu", 3]
    ]
  },
  "boards": [],
  "cvpcb": { "equivalence_files": [] },
  "libraries": {
    "pinned_footprint_libs": [],
    "pinned_symbol_libs": []
  },
  "meta": {
    "filename": "adeptbt.kicad_pro",
    "version": 1
  },
  "net_settings": {
    "classes": [
      { "bus_width": 12, "clearance": 0.2, "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25,
        "diff_pair_width": 0.2, "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1,
        "name": "Default", "pcb_color": "rgba(0,0,0,0.000)", "schematic_color": "rgba(0,0,0,0.000)",
        "track_width": 0.25, "via_diameter": 0.6, "via_drill": 0.3, "wire_width": 6 }
    ],
    "meta": { "version": 2 },
    "net_colors": null,
    "netclass_assignments": null,
    "netclass_patterns": []
  },
  "pcbnew": {
    "last_paths": { "gencad": "", "idf": "", "netlist": "", "specctra_dsn": "", "step": "", "vrml": "" },
    "page_layout_descr_file": ""
  },
  "schematic": {
    "annotate_start_num": 0,
    "drawing": {
      "dashed_lines_dash_length_ratio": 12.0,
      "dashed_lines_gap_length_ratio": 3.0,
      "default_line_thickness": 6.0,
      "default_text_size": 50.0,
      "field_names": [],
      "intersheets_ref_own_page": false,
      "intersheets_ref_prefix": "",
      "intersheets_ref_short": false,
      "intersheets_ref_show": false,
      "intersheets_ref_suffix": "",
      "junction_size_choice": 3,
      "label_size_ratio": 0.375,
      "operating_point_overlay_i_precision": 3,
      "operating_point_overlay_i_range": "~A",
      "operating_point_overlay_v_precision": 3,
      "operating_point_overlay_v_range": "~V",
      "overbar_offset_ratio": 1.23,
      "pin_symbol_size": 25.0,
      "text_offset_ratio": 0.15
    },
    "legacy_lib_dir": "",
    "legacy_lib_list": [],
    "meta": { "version": 1 },
    "net_format_name": "",
    "page_layout_descr_file": "",
    "plot_directory": "",
    "spice_current_sheet_as_root": false,
    "spice_external_command": "spice \\"%I\\"",
    "spice_save_all_currents": false,
    "spice_save_all_dissipations": false,
    "spice_save_all_voltages": false,
    "subpart_first_id": 65,
    "subpart_id_separator": 0
  },
  "sheets": [["adeptbt.kicad_sch", ""]],
  "text_variables": {}
}
"""


def build_silk_svg() -> str:
    """Human-readable silkscreen preview."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="856" height="540" viewBox="0 0 85.6 53.98">
  <rect width="85.6" height="53.98" fill="#1a1a1a" stroke="#c0c0c0" stroke-width="0.2"/>
  <text x="42.8" y="26" text-anchor="middle" fill="#f0e6d0" font-family="Helvetica" font-size="3">AdeptBT</text>
  <text x="42.8" y="29" text-anchor="middle" fill="#aaa" font-family="Helvetica" font-size="1.2">coconnor55</text>
  <!-- steppers top -->
  <rect x="10" y="0.5" width="24" height="7.5" fill="none" stroke="#f0e6d0" stroke-width="0.15"/>
  <text x="22" y="3" text-anchor="middle" fill="#f0e6d0" font-size="1.2">STEPPER1</text>
  <text x="22" y="5.5" text-anchor="middle" fill="#ccc" font-size="0.9">A1 A2 B1 B2 VM GND</text>
  <rect x="46" y="0.5" width="24" height="7.5" fill="none" stroke="#f0e6d0" stroke-width="0.15"/>
  <text x="58" y="3" text-anchor="middle" fill="#f0e6d0" font-size="1.2">STEPPER2</text>
  <text x="58" y="5.5" text-anchor="middle" fill="#ccc" font-size="0.9">A1 A2 B1 B2 VM GND</text>
  <!-- power bottom -->
  <rect x="28" y="45.5" width="30" height="7.5" fill="none" stroke="#f0e6d0" stroke-width="0.15"/>
  <text x="43" y="48.5" text-anchor="middle" fill="#f0e6d0" font-size="1.2">VIN GND V+ OUT1 V+ OUT2</text>
  <!-- USB left -->
  <rect x="0.3" y="22" width="3" height="10" fill="none" stroke="#7ec8e3" stroke-width="0.15"/>
  <text x="4" y="28" fill="#7ec8e3" font-size="1.1" transform="rotate(-90 4,28)">USB-C</text>
  <!-- headers right -->
  <text x="74" y="18" fill="#c8e67e" font-size="1.1">ANALOG</text>
  <text x="74" y="42" fill="#c8e67e" font-size="1.1">DIGITAL</text>
  <circle cx="3.5" cy="3.5" r="1.1" fill="none" stroke="#888" stroke-width="0.15"/>
  <circle cx="82.1" cy="3.5" r="1.1" fill="none" stroke="#888" stroke-width="0.15"/>
  <circle cx="3.5" cy="50.48" r="1.1" fill="none" stroke="#888" stroke-width="0.15"/>
  <circle cx="82.1" cy="50.48" r="1.1" fill="none" stroke="#888" stroke-width="0.15"/>
</svg>
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "gerbers").mkdir(exist_ok=True)
    (OUT / "adeptbt.kicad_pcb").write_text(build_pcb())
    (OUT / "adeptbt.kicad_sch").write_text(build_schematic())
    (OUT / "adeptbt.kicad_pro").write_text(build_pro())
    (OUT / "silkscreen_preview.svg").write_text(build_silk_svg())
    print(f"Wrote KiCad project under {OUT}")


if __name__ == "__main__":
    main()
