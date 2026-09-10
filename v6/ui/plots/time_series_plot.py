"""TimeSeriesPlotWidget — Real-time laboratory plotting canvas with Pub Mode and multi-format export."""
import os
import json
import time
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog, QMessageBox
    )
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtGui import QColor, QFont, QImage, QPainter
except ImportError:
    class QWidget:
        def __init__(self, parent=None): pass
    class QVBoxLayout:
        def __init__(self, parent=None): pass
    class QHBoxLayout:
        def __init__(self, parent=None): pass
    class QPushButton:
        def __init__(self, text=""): pass
    class QLabel:
        def __init__(self, text=""): pass
    def pyqtSignal(*args, **kwargs):
        class Sig:
            def connect(self, s): pass
            def emit(self, *a): pass
        return Sig()

try:
    import pyqtgraph as pg
    HAVE_PYQTGRAPH = True
except ImportError:
    HAVE_PYQTGRAPH = False

from .export import (
    PlotPresentationDialog, apply_pyqtgraph_curve_style,
    calculate_lowest_density_quadrant, calculate_percentile_limits
)


class TimeSeriesPlotWidget(QWidget):
    """
    High-performance telemetry plot widget supporting real-time oscilloscope
    and power supply waveform rendering with full publication styling and export.
    """

    def __init__(self, title: str = "Telemetry Waveform", parent=None):
        super().__init__(parent)
        self.plot_title = title
        self.is_dark = True
        self.pub_mode = False
        self.auto_scroll = True
        self.presentation_settings = {
            "title": title,
            "show_title": True,
            "font_family": "Default (Sans-Serif)",
            "font_size": 10,
            "x_label": "Time (s)",
            "y_label": "Magnitude",
            "show_legend": True,
            "legend_loc": "Top-Right",
            "plot_style": "Continuous: Solid Line (Default)",
            "line_width": 2.0,
            "export_theme": "Match Active GUI Theme",
            "export_dpi": 300,
            "transparent_pdf": False,
            "export_companion_meta": True,
            "auto_limits_percentile": False,
        }

        self.curves: Dict[str, Any] = {}
        self.trace_colors: Dict[str, str] = {}
        self.data_store: Dict[str, List[float]] = {}
        self.time_store: List[float] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Control Toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(6)

        self.lbl_heading = QLabel(f"<b>{title}</b>")
        self.lbl_heading.setStyleSheet("font-size: 9.5pt; color: #E8EDF2;")
        toolbar.addWidget(self.lbl_heading)

        toolbar.addStretch()

        self.btn_autorange = QPushButton("⛶ Auto-Range")
        self.btn_autorange.setCheckable(True)
        self.btn_autorange.setChecked(True)
        self.btn_autorange.clicked.connect(self._toggle_autorange)
        toolbar.addWidget(self.btn_autorange)

        self.btn_pub_mode = QPushButton("📌 Pub Mode")
        self.btn_pub_mode.setCheckable(True)
        self.btn_pub_mode.clicked.connect(self._toggle_pub_mode)
        toolbar.addWidget(self.btn_pub_mode)

        self.btn_style = QPushButton("⚙ Presentation...")
        self.btn_style.clicked.connect(self._open_presentation_dialog)
        toolbar.addWidget(self.btn_style)

        self.btn_export = QPushButton("📷 Export...")
        self.btn_export.clicked.connect(self._export_dialog)
        toolbar.addWidget(self.btn_export)

        self.btn_clear = QPushButton("🗑 Clear")
        self.btn_clear.clicked.connect(self.clear_data)
        toolbar.addWidget(self.btn_clear)

        layout.addLayout(toolbar)

        # Main Plot Canvas
        if HAVE_PYQTGRAPH:
            self.plot_item = pg.PlotWidget()
            self.plot_item.setBackground("#0F1117")
            self.plot_item.showGrid(x=True, y=True, alpha=0.25)
            self.plot_item.setLabel("bottom", "Time (s)")
            self.legend = self.plot_item.addLegend(offset=(10, 10))
            layout.addWidget(self.plot_item)
        else:
            self.plot_item = QLabel("PyQtGraph not installed. Waveform preview disabled.")
            layout.addWidget(self.plot_item)

    def add_trace(self, trace_id: str, name: str, color_hex: str):
        self.trace_colors[trace_id] = color_hex
        self.data_store[trace_id] = []
        if HAVE_PYQTGRAPH and hasattr(self.plot_item, "plot"):
            pen = pg.mkPen(color=color_hex, width=self.presentation_settings["line_width"])
            curve = self.plot_item.plot(name=name, pen=pen)
            self.curves[trace_id] = curve

    def set_trace_data(self, trace_id: str, t_data: List[float], y_data: List[float]):
        if trace_id not in self.trace_colors:
            self.add_trace(trace_id, trace_id, "#4A9BDB")
        self.time_store = t_data
        self.data_store[trace_id] = y_data

        if HAVE_PYQTGRAPH and trace_id in self.curves:
            self.curves[trace_id].setData(t_data, y_data)

    def append_data_point(self, timestamp: float, trace_values: Dict[str, float]):
        self.time_store.append(timestamp)
        # Cap window at 2000 points to prevent memory creep
        if len(self.time_store) > 2000:
            self.time_store = self.time_store[-2000:]

        for k, v in trace_values.items():
            if k not in self.data_store:
                self.add_trace(k, k, "#3FB58C")
            self.data_store[k].append(v)
            if len(self.data_store[k]) > 2000:
                self.data_store[k] = self.data_store[k][-2000:]
            if HAVE_PYQTGRAPH and k in self.curves:
                self.curves[k].setData(self.time_store, self.data_store[k])

    def clear_data(self):
        self.time_store.clear()
        for k in self.data_store:
            self.data_store[k].clear()
            if HAVE_PYQTGRAPH and k in self.curves:
                self.curves[k].setData([], [])

    def _toggle_autorange(self, checked: bool):
        if HAVE_PYQTGRAPH and hasattr(self.plot_item, "enableAutoRange"):
            self.plot_item.enableAutoRange(enable=checked)

    def _toggle_pub_mode(self, checked: bool):
        self.pub_mode = checked
        if checked:
            self.btn_pub_mode.setText("📌 Pub Mode: ON")
            self.btn_pub_mode.setStyleSheet("background-color: #1E3A5F; border: 1px solid #4A9BDB; color: #FFFFFF;")
            self.set_theme(is_dark=False)
        else:
            self.btn_pub_mode.setText("📌 Pub Mode")
            self.btn_pub_mode.setStyleSheet("")
            self.set_theme(is_dark=self.is_dark)

    def _open_presentation_dialog(self):
        dlg = PlotPresentationDialog(self.presentation_settings, self)
        if dlg.exec():
            self.presentation_settings = dlg.get_settings()
            self._apply_presentation_settings()

    def _apply_presentation_settings(self):
        if not HAVE_PYQTGRAPH:
            return
        lw = self.presentation_settings.get("line_width", 2.0)
        p_style = self.presentation_settings.get("plot_style", "Continuous: Solid Line (Default)")
        for tid, curve in self.curves.items():
            color = self.trace_colors.get(tid, "#4A9BDB")
            apply_pyqtgraph_curve_style(curve, color, lw, p_style)

    def set_theme(self, is_dark: bool):
        self.is_dark = is_dark
        bg = "#0F1117" if is_dark else "#FFFFFF"
        fg = "#94A3B8" if is_dark else "#475569"
        if HAVE_PYQTGRAPH and hasattr(self.plot_item, "setBackground"):
            self.plot_item.setBackground(bg)
            try:
                self.plot_item.getAxis("bottom").setPen(pg.mkPen(fg))
                self.plot_item.getAxis("left").setPen(pg.mkPen(fg))
            except Exception:
                pass

    def _export_dialog(self):
        path, filt = QFileDialog.getSaveFileName(
            self, "Export Telemetry Plot",
            str(Path.home() / f"telemetry_{int(time.time())}.png"),
            "PNG Image (*.png);;PDF Document (*.pdf);;SVG Vector (*.svg);;JPEG Image (*.jpg)"
        )
        if not path:
            return

        try:
            if HAVE_PYQTGRAPH and hasattr(pg, "exporters"):
                exporter = pg.exporters.ImageExporter(self.plot_item.plotItem)
                exporter.parameters()['width'] = 1920
                exporter.export(path)
                QMessageBox.information(self, "Export Successful", f"Saved plot to:\n{path}")
            else:
                QMessageBox.warning(self, "Export Notice", "PyQtGraph ImageExporter is required for raster export.")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export plot:\n{e}")
