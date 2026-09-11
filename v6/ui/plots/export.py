"""Export & Plot Presentation Pipeline — Multi-format archival rendering (PDF, PNG, JPEG, SVG, LaTeX)."""
import os
import re
import json
import math
import time
import datetime
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List

try:
    import numpy as np
    HAVE_NUMPY = True
except ImportError:
    HAVE_NUMPY = False

from ..qt_compat import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel,
    QLineEdit, QSpinBox, QComboBox, QPushButton, QCheckBox, QListWidget,
    QDialogButtonBox, QMessageBox, QFileDialog, QAbstractItemView,
    Qt, QPointF, QRectF,
    QFont, QColor, QPainter, QPen, QBrush, QImage, QPixmap, QPdfWriter, QPageSize, QPageLayout
)
try:
    from PyQt6.QtSvg import QSvgGenerator
    HAVE_SVG = True
except ImportError:
    HAVE_SVG = False

try:
    import pyqtgraph as pg
    HAVE_PYQTGRAPH = True
except ImportError:
    HAVE_PYQTGRAPH = False

TEMPLATE_DIR = Path.home() / ".labhp_v6_templates"
try:
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

# =============================================================================
# TRACE STYLING OPTIONS & PARSERS
# =============================================================================
PLOT_STYLE_OPTIONS = [
    "Continuous: Solid Line (Default)",
    "Continuous: Dashed Line",
    "Continuous: Dotted Line",
    "Continuous: Dash-Dot Line",
    "Continuous: Step Plot (Sample & Hold)",
    "Discrete: Plus Marker (+)",
    "Discrete: Cross Marker (x)",
    "Discrete: Star Marker (*)",
    "Discrete: Circle Marker (o)",
    "Discrete: Square Marker (s)",
    "Discrete: Triangle Marker (^)",
    "Discrete: Diamond Marker (d)",
    "Combined: Line with Circle Markers",
    "Combined: Line with Plus Markers",
    "Combined: Line with Cross Markers",
    "Combined: Line with Star Markers"
]

def parse_plot_style(style_str: str):
    s = (style_str or "").strip()
    pg_symbol = None
    mpl_linestyle = "-"
    mpl_marker = None
    is_step = False

    if "Dashed" in s: mpl_linestyle = "--"
    elif "Dotted" in s: mpl_linestyle = ":"
    elif "Dash-Dot" in s: mpl_linestyle = "-."
    elif "Step" in s:
        is_step = True
        mpl_linestyle = "-"

    if "Plus" in s: pg_symbol, mpl_marker = "+", "+"
    elif "Cross" in s: pg_symbol, mpl_marker = "x", "x"
    elif "Star" in s: pg_symbol, mpl_marker = "star", "*"
    elif "Circle" in s: pg_symbol, mpl_marker = "o", "o"
    elif "Square" in s: pg_symbol, mpl_marker = "s", "s"
    elif "Triangle" in s: pg_symbol, mpl_marker = "t", "^"
    elif "Diamond" in s: pg_symbol, mpl_marker = "d", "D"

    if "Discrete" in s:
        mpl_linestyle = "None"

    return pg_symbol, mpl_linestyle, mpl_marker, is_step

def apply_pyqtgraph_curve_style(curve, color_hex: str, line_width: float, style_str: str, marker_size: int = 6):
    if not curve or not HAVE_PYQTGRAPH:
        return
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QColor

    pg_symbol, mpl_ls, _, is_step = parse_plot_style(style_str)

    if "Discrete" in (style_str or ""):
        pen = None
    else:
        q_pen_style = Qt.PenStyle.SolidLine
        if "Dashed" in (style_str or ""): q_pen_style = Qt.PenStyle.DashLine
        elif "Dotted" in (style_str or ""): q_pen_style = Qt.PenStyle.DotLine
        elif "Dash-Dot" in (style_str or ""): q_pen_style = Qt.PenStyle.DashDotLine
        pen = pg.mkPen(color=color_hex, width=line_width, style=q_pen_style)

    curve.setPen(pen)

    if pg_symbol:
        curve.setSymbol(pg_symbol)
        curve.setSymbolSize(marker_size)
        qcol = QColor(color_hex)
        curve.setSymbolPen(pg.mkPen(color=color_hex, width=1.2))
        curve.setSymbolBrush(pg.mkBrush(qcol))
    else:
        curve.setSymbol(None)

def get_matplotlib_plot_kwargs(color_hex: str, line_width: float, style_str: str, marker_size: int = 6) -> dict:
    pg_symbol, mpl_ls, mpl_marker, is_step = parse_plot_style(style_str)
    kw = {
        "color": color_hex,
        "linewidth": line_width if mpl_ls != "None" else 0,
        "linestyle": mpl_ls,
    }
    if is_step: kw["drawstyle"] = "steps-post"
    if mpl_marker:
        kw["marker"] = mpl_marker
        kw["markersize"] = marker_size
        kw["markeredgecolor"] = color_hex
        kw["markerfacecolor"] = color_hex
    return kw

# =============================================================================
# SMART LAYOUT HELPERS
# =============================================================================
def calculate_lowest_density_quadrant(t_data: list, traces_dict: dict) -> tuple:
    if not t_data or not traces_dict:
        return "upper right", "Top-Right"

    t_min = min(t_data)
    t_max = max(t_data)
    t_span = (t_max - t_min) or 1.0

    all_y = []
    for k, y_series in traces_dict.items():
        if not y_series: continue
        for idx in range(min(len(t_data), len(y_series))):
            y_val = y_series[idx]
            if y_val is not None and not math.isnan(y_val) and not math.isinf(y_val):
                all_y.append(y_val)

    if not all_y:
        return "upper right", "Top-Right"

    y_min = min(all_y)
    y_max = max(all_y)
    y_span = (y_max - y_min) or 1.0

    counts = {
        ("upper right", "Top-Right"): 0,
        ("upper left", "Top-Left"): 0,
        ("lower right", "Bottom-Right"): 0,
        ("lower left", "Bottom-Left"): 0,
    }

    step = max(1, len(t_data) // 500)
    for k, y_series in traces_dict.items():
        if not y_series: continue
        n = min(len(t_data), len(y_series))
        for idx in range(0, n, step):
            t_val = t_data[idx]
            y_val = y_series[idx]
            if y_val is None or math.isnan(y_val) or math.isinf(y_val): continue
            norm_x = (t_val - t_min) / t_span
            norm_y = (y_val - y_min) / y_span
            is_top = (norm_y >= 0.5)
            is_right = (norm_x >= 0.5)

            if is_top and is_right: counts[("upper right", "Top-Right")] += 1
            elif is_top and not is_right: counts[("upper left", "Top-Left")] += 1
            elif not is_top and is_right: counts[("lower right", "Bottom-Right")] += 1
            else: counts[("lower left", "Bottom-Left")] += 1

    return min(counts.keys(), key=lambda k: counts[k])

def calculate_percentile_limits(traces_dict: dict, p_low=5.0, p_high=95.0, margin=0.08):
    all_vals = []
    for k, series in traces_dict.items():
        if not series: continue
        for v in series:
            if v is not None and not math.isnan(v) and not math.isinf(v):
                all_vals.append(float(v))

    if len(all_vals) < 10:
        return None

    try:
        if HAVE_NUMPY:
            arr = np.array(all_vals)
            y_low = float(np.percentile(arr, p_low))
            y_high = float(np.percentile(arr, p_high))
        else:
            sorted_vals = sorted(all_vals)
            n = len(sorted_vals)
            y_low = sorted_vals[int(n * (p_low / 100.0))]
            y_high = sorted_vals[int(n * (p_high / 100.0))]

        span = y_high - y_low
        if span <= 0:
            span = max(abs(y_high) * 0.1, 1.0)
        return (y_low - margin * span, y_high + margin * span)
    except Exception:
        return None

# =============================================================================
# PUBLICATION PRESETS
# =============================================================================
PUBLICATION_PRESETS = {
    "Custom (User Defined)": {},
    "Nature Research / Springer (Single Column)": {
        "title": "", "show_title": False, "font_family": "Arial, Helvetica, sans-serif",
        "font_size": 8, "line_width": 1.0, "marker_size": 4, "grid_style": "None",
        "export_dpi": 600, "export_theme": "Publication Clean Light (White)",
        "transparent_pdf": True, "show_watermark": False, "export_companion_meta": True,
    },
    "IEEE Transactions (Standard Column)": {
        "title": "", "show_title": False, "font_family": "Times New Roman, serif",
        "font_size": 9, "line_width": 1.0, "marker_size": 4, "grid_style": "Both X & Y",
        "export_dpi": 600, "export_theme": "Publication Clean Light (White)",
        "transparent_pdf": False, "show_watermark": False, "export_companion_meta": True,
    },
    "APS Physical Review (Two Column)": {
        "title": "", "show_title": False, "font_family": "Computer Modern, serif",
        "font_size": 10, "line_width": 1.25, "marker_size": 5, "grid_style": "Both X & Y",
        "export_dpi": 600, "export_theme": "Publication Clean Light (White)",
        "transparent_pdf": True, "show_watermark": False, "export_companion_meta": True,
    },
    "Industrial Laboratory Archival (Full Metadata)": {
        "title": "Laboratory Instrumentation Telemetry", "show_title": True,
        "font_family": "Default (Sans-Serif)", "font_size": 11, "line_width": 2.0,
        "marker_size": 6, "grid_style": "Both X & Y", "export_dpi": 300,
        "export_theme": "Match Active GUI Theme", "transparent_pdf": False,
        "show_watermark": True, "watermark_text": "ETPS LAB-HP & RTB2000 Telemetry",
        "export_companion_meta": True,
    },
}

# =============================================================================
# PLOT PRESENTATION DIALOG (Inherited verbatim from v5)
# =============================================================================
class PlotPresentationDialog(QDialog):
    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chart Presentation & Publication Settings")
        self.setMinimumWidth(560)
        self.settings = dict(settings)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Preset & Template
        grp_tmpl = QGroupBox("Publication Presets & Template System")
        g_tmpl = QGridLayout(grp_tmpl)
        g_tmpl.addWidget(QLabel("Preset:"), 0, 0)
        self.combo_preset = QComboBox()
        self.combo_preset.addItems(list(PUBLICATION_PRESETS.keys()))
        curr = self.settings.get("publication_preset", "Custom (User Defined)")
        if curr in PUBLICATION_PRESETS: self.combo_preset.setCurrentText(curr)
        self.combo_preset.currentIndexChanged.connect(self._on_preset_changed)
        g_tmpl.addWidget(self.combo_preset, 0, 1, 1, 3)

        self.btn_save_tmpl = QPushButton("💾 Save Template...")
        self.btn_save_tmpl.clicked.connect(self._save_template)
        g_tmpl.addWidget(self.btn_save_tmpl, 1, 2)

        self.btn_load_tmpl = QPushButton("📂 Load File...")
        self.btn_load_tmpl.clicked.connect(self._load_template)
        g_tmpl.addWidget(self.btn_load_tmpl, 1, 3)
        layout.addWidget(grp_tmpl)

        # Title & Typography
        grp_title = QGroupBox("Plot Title, Axes & Typography")
        g1 = QGridLayout(grp_title)
        g1.addWidget(QLabel("Title Text:"), 0, 0)
        self.txt_title = QLineEdit(self.settings.get("title", "Laboratory Instrumentation Telemetry"))
        g1.addWidget(self.txt_title, 0, 1)

        self.chk_show_title = QCheckBox("Show Title on Canvas & Export")
        self.chk_show_title.setChecked(self.settings.get("show_title", True))
        g1.addWidget(self.chk_show_title, 1, 0, 1, 2)

        g1.addWidget(QLabel("Font Family:"), 2, 0)
        self.combo_font = QComboBox()
        self.combo_font.addItems([
            "Default (Sans-Serif)", "Arial, Helvetica, sans-serif",
            "Times New Roman, serif", "Computer Modern, serif", "JetBrains Mono, monospace"
        ])
        self.combo_font.setCurrentText(self.settings.get("font_family", "Default (Sans-Serif)"))
        g1.addWidget(self.combo_font, 2, 1)

        g1.addWidget(QLabel("Font Size:"), 3, 0)
        self.spin_font_size = QSpinBox()
        self.spin_font_size.setRange(6, 18)
        self.spin_font_size.setValue(int(self.settings.get("font_size", 10)))
        self.spin_font_size.setSuffix(" pt")
        g1.addWidget(self.spin_font_size, 3, 1)

        g1.addWidget(QLabel("X-Axis Label:"), 4, 0)
        self.txt_xlabel = QLineEdit(self.settings.get("x_label", "Elapsed Time"))
        g1.addWidget(self.txt_xlabel, 4, 1)

        g1.addWidget(QLabel("Y-Axis Label:"), 5, 0)
        self.txt_ylabel = QLineEdit(self.settings.get("y_label", "Magnitude"))
        g1.addWidget(self.txt_ylabel, 5, 1)

        self.chk_auto_limits = QCheckBox("Smart Outlier Suppression (5-95% Percentile Limits)")
        self.chk_auto_limits.setChecked(self.settings.get("auto_limits_percentile", False))
        g1.addWidget(self.chk_auto_limits, 6, 0, 1, 2)
        layout.addWidget(grp_title)

        # Legend & Trace Styling
        grp_legend = QGroupBox("Legend Positioning & Trace Styling")
        g3 = QGridLayout(grp_legend)
        self.chk_show_legend = QCheckBox("Display Legend")
        self.chk_show_legend.setChecked(self.settings.get("show_legend", True))
        g3.addWidget(self.chk_show_legend, 0, 0, 1, 2)

        g3.addWidget(QLabel("Legend Position:"), 1, 0)
        self.combo_legend_loc = QComboBox()
        self.combo_legend_loc.addItems([
            "Auto (Lowest Density)", "Top-Right", "Top-Left", "Bottom-Right", "Bottom-Left",
            "Top-Center", "Bottom-Center", "Hidden"
        ])
        self.combo_legend_loc.setCurrentText(self.settings.get("legend_loc", "Top-Right"))
        g3.addWidget(self.combo_legend_loc, 1, 1)

        g3.addWidget(QLabel("Plot Style:"), 2, 0)
        self.combo_plot_style = QComboBox()
        self.combo_plot_style.addItems(PLOT_STYLE_OPTIONS)
        self.combo_plot_style.setCurrentText(self.settings.get("plot_style", "Continuous: Solid Line (Default)"))
        g3.addWidget(self.combo_plot_style, 2, 1)

        g3.addWidget(QLabel("Line Width:"), 3, 0)
        self.combo_line_width = QComboBox()
        self.combo_line_width.addItems(["0.75 px (Hairline)", "1.0 px (Fine)", "1.5 px (Normal)", "2.0 px (Standard)", "2.5 px (Thick)", "3.0 px (Bold)"])
        lw_str = f"{float(self.settings.get('line_width', 2.0)):.2f}".rstrip('0').rstrip('.')
        for idx in range(self.combo_line_width.count()):
            if lw_str in self.combo_line_width.itemText(idx):
                self.combo_line_width.setCurrentIndex(idx)
                break
        g3.addWidget(self.combo_line_width, 3, 1)
        layout.addWidget(grp_legend)

        # Export Defaults
        grp_export = QGroupBox("Export Defaults & Archival Formats")
        g4 = QGridLayout(grp_export)
        g4.addWidget(QLabel("Export Color Theme:"), 0, 0)
        self.combo_export_theme = QComboBox()
        self.combo_export_theme.addItems(["Match Active GUI Theme", "Dark Mode (Slate)", "Publication Clean Light (White)"])
        self.combo_export_theme.setCurrentText(self.settings.get("export_theme", "Match Active GUI Theme"))
        g4.addWidget(self.combo_export_theme, 0, 1)

        g4.addWidget(QLabel("Export DPI:"), 1, 0)
        self.combo_export_dpi = QComboBox()
        self.combo_export_dpi.addItems(["150 DPI (Standard Screen)", "300 DPI (Print)", "600 DPI (Archival)", "1200 DPI (Ultra)"])
        dpi_str = str(self.settings.get("export_dpi", 300))
        for idx in range(self.combo_export_dpi.count()):
            if dpi_str in self.combo_export_dpi.itemText(idx):
                self.combo_export_dpi.setCurrentIndex(idx)
                break
        g4.addWidget(self.combo_export_dpi, 1, 1)

        self.chk_transparent = QCheckBox("Transparent Background (PDF / PNG)")
        self.chk_transparent.setChecked(self.settings.get("transparent_pdf", False))
        g4.addWidget(self.chk_transparent, 2, 0, 1, 2)

        self.chk_companion_meta = QCheckBox("Generate Companion .meta JSON File")
        self.chk_companion_meta.setChecked(self.settings.get("export_companion_meta", True))
        g4.addWidget(self.chk_companion_meta, 3, 0, 1, 2)
        layout.addWidget(grp_export)

        bbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        layout.addWidget(bbox)

    def _on_preset_changed(self, idx: int):
        p_name = self.combo_preset.currentText()
        cfg = PUBLICATION_PRESETS.get(p_name)
        if cfg:
            if "title" in cfg: self.txt_title.setText(str(cfg["title"]))
            if "show_title" in cfg: self.chk_show_title.setChecked(bool(cfg["show_title"]))
            if "font_size" in cfg: self.spin_font_size.setValue(int(cfg["font_size"]))
            if "font_family" in cfg: self.combo_font.setCurrentText(str(cfg["font_family"]))
            if "export_theme" in cfg: self.combo_export_theme.setCurrentText(str(cfg["export_theme"]))
            if "auto_limits_percentile" in cfg: self.chk_auto_limits.setChecked(bool(cfg["auto_limits_percentile"]))
            if "transparent_pdf" in cfg: self.chk_transparent.setChecked(bool(cfg["transparent_pdf"]))
            if "export_companion_meta" in cfg: self.chk_companion_meta.setChecked(bool(cfg["export_companion_meta"]))

    def _save_template(self):
        p, _ = QFileDialog.getSaveFileName(self, "Save Template", str(TEMPLATE_DIR / "template.json"), "JSON (*.json)")
        if p:
            try:
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(self.get_settings(), f, indent=2)
                QMessageBox.information(self, "Saved", f"Template saved to:\n{p}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save:\n{e}")

    def _load_template(self):
        p, _ = QFileDialog.getOpenFileName(self, "Load Template", str(TEMPLATE_DIR), "JSON (*.json)")
        if p and os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    d = json.load(f)
                if "title" in d: self.txt_title.setText(str(d["title"]))
                if "font_size" in d: self.spin_font_size.setValue(int(d["font_size"]))
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load:\n{e}")

    def get_settings(self) -> dict:
        lw = 2.0
        try: lw = float(self.combo_line_width.currentText().split()[0])
        except Exception: pass

        dpi = 300
        try: dpi = int(self.combo_export_dpi.currentText().split()[0])
        except Exception: pass

        return {
            "publication_preset": self.combo_preset.currentText(),
            "title": self.txt_title.text().strip(),
            "show_title": self.chk_show_title.isChecked(),
            "font_family": self.combo_font.currentText(),
            "font_size": self.spin_font_size.value(),
            "x_label": self.txt_xlabel.text().strip(),
            "y_label": self.txt_ylabel.text().strip(),
            "auto_limits_percentile": self.chk_auto_limits.isChecked(),
            "show_legend": self.chk_show_legend.isChecked(),
            "legend_loc": self.combo_legend_loc.currentText(),
            "plot_style": self.combo_plot_style.currentText(),
            "line_width": lw,
            "export_theme": self.combo_export_theme.currentText(),
            "export_dpi": dpi,
            "transparent_pdf": self.chk_transparent.isChecked(),
            "export_companion_meta": self.chk_companion_meta.isChecked(),
        }
