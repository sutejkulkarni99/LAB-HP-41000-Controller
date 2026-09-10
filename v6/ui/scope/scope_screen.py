"""ScopeScreen — Oscilloscope graticule display with multi-channel traces and trigger overlay."""
import math
from typing import Dict, List, Optional, Any

try:
    from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtGui import QColor, QFont
except ImportError:
    class QWidget:
        def __init__(self, parent=None): pass
    class QVBoxLayout:
        def __init__(self, parent=None): pass
    class QHBoxLayout:
        def __init__(self, parent=None): pass
    class QLabel:
        def __init__(self, text=""): pass
    class QFrame:
        def __init__(self, parent=None): pass

try:
    import pyqtgraph as pg
    HAVE_PYQTGRAPH = True
except ImportError:
    HAVE_PYQTGRAPH = False

from ..styles.tokens import (
    SCOPE_CH1_COLOR, SCOPE_CH2_COLOR, SCOPE_CH3_COLOR, SCOPE_CH4_COLOR,
    SCOPE_MATH_COLOR, SCOPE_GRID_DARK, SCOPE_GRID_LIGHT
)


class ScopeScreen(QWidget):
    """
    Graticule display canvas replicating professional benchtop oscilloscope screens.
    Renders 10x8 division grid, analog-style channel traces, trigger level lines,
    and live measurement readouts.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_dark = True
        self.ch_curves: Dict[int, Any] = {}
        self.ch_colors = {
            1: SCOPE_CH1_COLOR,
            2: SCOPE_CH2_COLOR,
            3: SCOPE_CH3_COLOR,
            4: SCOPE_CH4_COLOR,
            99: SCOPE_MATH_COLOR
        }

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if HAVE_PYQTGRAPH:
            self.plot_widget = pg.PlotWidget()
            self.plot_widget.setBackground("#0A0D14")
            self.plot_widget.showGrid(x=True, y=True, alpha=0.35)
            self.plot_widget.setLabel("bottom", "Time", units="s")
            self.plot_widget.setLabel("left", "Voltage", units="V")

            # Initialize Channel Curves
            for ch, color in self.ch_colors.items():
                name = f"CH{ch}" if ch != 99 else "MATH"
                pen = pg.mkPen(color=color, width=1.75)
                curve = self.plot_widget.plot(name=name, pen=pen)
                self.ch_curves[ch] = curve

            # Trigger Level Line
            self.trig_line = pg.InfiniteLine(
                pos=0.0, angle=0, pen=pg.mkPen(color="#F59E0B", width=1.0, style=pg.QtCore.Qt.PenStyle.DashLine),
                movable=False, label="T {value:.2f}V"
            )
            self.plot_widget.addItem(self.trig_line)

            layout.addWidget(self.plot_widget)
        else:
            self.lbl_fallback = QLabel("PyQtGraph oscilloscope renderer initializing...")
            layout.addWidget(self.lbl_fallback)

        # Measurement readout footer banner
        self.footer = QFrame()
        self.footer.setStyleSheet("background-color: #14171F; border-top: 1px solid #2F3540; padding: 4px;")
        f_lay = QHBoxLayout(self.footer)
        f_lay.setContentsMargins(8, 2, 8, 2)
        f_lay.setSpacing(16)

        self.lbl_ch1_meas = QLabel("CH1: -- Vrms | -- Vpp | -- Hz")
        self.lbl_ch1_meas.setStyleSheet(f"font-size: 8.5pt; font-family: monospace; font-weight: bold; color: {SCOPE_CH1_COLOR};")
        f_lay.addWidget(self.lbl_ch1_meas)

        self.lbl_ch2_meas = QLabel("CH2: -- Vrms | -- Vpp | -- Hz")
        self.lbl_ch2_meas.setStyleSheet(f"font-size: 8.5pt; font-family: monospace; font-weight: bold; color: {SCOPE_CH2_COLOR};")
        f_lay.addWidget(self.lbl_ch2_meas)

        f_lay.addStretch()

        self.lbl_status = QLabel("TRIGGER: AUTO (READY)")
        self.lbl_status.setStyleSheet("font-size: 8.5pt; font-family: monospace; color: #22C55E;")
        f_lay.addWidget(self.lbl_status)

        layout.addWidget(self.footer)

    def set_channel_data(self, ch: int, time_arr: List[float], volt_arr: List[float]):
        if HAVE_PYQTGRAPH and ch in self.ch_curves:
            self.ch_curves[ch].setData(time_arr, volt_arr)

    def set_trigger_level(self, level: float, source_ch: int = 1):
        if HAVE_PYQTGRAPH and hasattr(self, "trig_line"):
            self.trig_line.setValue(level)
            color = self.ch_colors.get(source_ch, "#F59E0B")
            self.trig_line.setPen(pg.mkPen(color=color, width=1.0, style=pg.QtCore.Qt.PenStyle.DashLine))

    def update_measurements(self, ch1_dict: Dict[str, Any], ch2_dict: Dict[str, Any]):
        c1_rms = ch1_dict.get("vrms", 0.0)
        c1_vpp = ch1_dict.get("vpp", 0.0)
        c1_freq = ch1_dict.get("freq_hz", 0.0)
        self.lbl_ch1_meas.setText(f"CH1: {c1_rms:.3f} Vrms | {c1_vpp:.3f} Vpp | {c1_freq:.1f} Hz")

        c2_rms = ch2_dict.get("vrms", 0.0)
        c2_vpp = ch2_dict.get("vpp", 0.0)
        c2_freq = ch2_dict.get("freq_hz", 0.0)
        self.lbl_ch2_meas.setText(f"CH2: {c2_rms:.3f} Vrms | {c2_vpp:.3f} Vpp | {c2_freq:.1f} Hz")

    def set_theme(self, is_dark: bool):
        self.is_dark = is_dark
        if HAVE_PYQTGRAPH and hasattr(self.plot_widget, "setBackground"):
            bg = "#0A0D14" if is_dark else "#FFFFFF"
            self.plot_widget.setBackground(bg)
        if is_dark:
            self.footer.setStyleSheet("background-color: #14171F; border-top: 1px solid #2F3540; padding: 4px;")
        else:
            self.footer.setStyleSheet("background-color: #F1F5F9; border-top: 1px solid #E2E8F0; padding: 4px;")
