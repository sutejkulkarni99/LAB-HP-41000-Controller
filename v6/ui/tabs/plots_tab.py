"""PlotsTab — Unified multi-instrument time-series analysis and publication export with responsive layout."""
import time
from typing import Dict, Any, List

from ..qt_compat import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QPushButton, QToolButton, QMessageBox,
    QScrollArea, QFrame, QSplitter, Qt, pyqtSignal
)
try:
    import pyqtgraph as pg
    HAVE_PYQTGRAPH = True
except ImportError:
    HAVE_PYQTGRAPH = False

from ..plots.export import PlotPresentationDialog
from ..styles.tokens import (
    DARK_ACCENT_VOLTAGE, DARK_ACCENT_CURRENT, DARK_ACCENT_POWER,
    SCOPE_CH1_COLOR, SCOPE_CH2_COLOR
)


class PlotsTab(QWidget):
    """
    Synchronized multi-instrument time-series plotter displaying telemetry traces
    from both the LAB-HP power supply and the RTB2000 oscilloscope on a single shared
    time axis, with vector publication export capabilities (PDF, PNG, SVG).
    """

    export_requested = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_dark = True
        self.pub_mode_active = False

        self.t_data: List[float] = []
        self.v_data: List[float] = []
        self.i_data: List[float] = []
        self.p_data: List[float] = []
        self.ch1_vrms_data: List[float] = []
        self.ch2_vrms_data: List[float] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Toolbar wrapped in scrollable/flexible horizontal container
        tb_scroll = QScrollArea()
        tb_scroll.setWidgetResizable(True)
        tb_scroll.setFixedHeight(44)
        tb_scroll.setFrameShape(QFrame.Shape.NoFrame)

        tb_widget = QWidget()
        tb = QHBoxLayout(tb_widget)
        tb.setContentsMargins(4, 2, 4, 2)
        tb.setSpacing(10)

        tb.addWidget(QLabel("Traces:"))

        self.chkV = QCheckBox("PSU V")
        self.chkV.setChecked(True)
        self.chkV.setStyleSheet(f"color: {DARK_ACCENT_VOLTAGE}; font-weight: bold;")
        self.chkV.stateChanged.connect(self._refresh_visibility)
        tb.addWidget(self.chkV)

        self.chkI = QCheckBox("PSU I")
        self.chkI.setChecked(True)
        self.chkI.setStyleSheet(f"color: {DARK_ACCENT_CURRENT}; font-weight: bold;")
        self.chkI.stateChanged.connect(self._refresh_visibility)
        tb.addWidget(self.chkI)

        self.chkP = QCheckBox("PSU P")
        self.chkP.setChecked(True)
        self.chkP.setStyleSheet(f"color: {DARK_ACCENT_POWER}; font-weight: bold;")
        self.chkP.stateChanged.connect(self._refresh_visibility)
        tb.addWidget(self.chkP)

        self.chkCH1 = QCheckBox("Scope CH1 Vrms")
        self.chkCH1.setChecked(True)
        self.chkCH1.setStyleSheet(f"color: {SCOPE_CH1_COLOR}; font-weight: bold;")
        self.chkCH1.stateChanged.connect(self._refresh_visibility)
        tb.addWidget(self.chkCH1)

        self.chkCH2 = QCheckBox("Scope CH2 Vrms")
        self.chkCH2.setChecked(False)
        self.chkCH2.setStyleSheet(f"color: {SCOPE_CH2_COLOR}; font-weight: bold;")
        self.chkCH2.stateChanged.connect(self._refresh_visibility)
        tb.addWidget(self.chkCH2)

        tb.addStretch()

        self.btn_autorange = QToolButton()
        self.btn_autorange.setText("Auto-Range")
        self.btn_autorange.clicked.connect(self._autorange)
        tb.addWidget(self.btn_autorange)

        self.btn_pub_mode = QToolButton()
        self.btn_pub_mode.setText("📌 Pub Mode")
        self.btn_pub_mode.setCheckable(True)
        self.btn_pub_mode.clicked.connect(self._toggle_pub_mode)
        tb.addWidget(self.btn_pub_mode)

        self.btn_settings = QToolButton()
        self.btn_settings.setText("⚙ Settings...")
        self.btn_settings.clicked.connect(self._open_settings_dialog)
        tb.addWidget(self.btn_settings)

        self.btn_export = QPushButton("Export Plot...")
        self.btn_export.setObjectName("primary")
        self.btn_export.clicked.connect(self._open_settings_dialog)
        tb.addWidget(self.btn_export)

        tb_scroll.setWidget(tb_widget)
        layout.addWidget(tb_scroll)

        # Summary statistics banner
        self.lbl_stats = QLabel("Session Duration: 0.0s  |  Peak V: 0.00 V  |  Peak I: 0.0000 A  |  Peak P: 0.0 W  |  CH1 Max: 0.00 V")
        self.lbl_stats.setStyleSheet("""
            background-color: #0E1220;
            border: 1px solid #1B2238;
            border-radius: 6px;
            color: #E8ECF5;
            font-size: 8.5pt;
            font-family: monospace;
            padding: 5px 10px;
            font-weight: 600;
        """)
        layout.addWidget(self.lbl_stats)

        # Canvas Setup
        if HAVE_PYQTGRAPH:
            self.plot_widget = pg.PlotWidget()
            self.plot_widget.showGrid(x=True, y=True, alpha=0.15)
            self.plot_widget.setLabel('bottom', 'Elapsed Time', units='s')
            self.plot_widget.setLabel('left', 'Magnitude')
            self.plot_widget.addLegend(offset=(10, 10))

            pen_v = pg.mkPen(color=DARK_ACCENT_VOLTAGE, width=2.0)
            pen_i = pg.mkPen(color=DARK_ACCENT_CURRENT, width=2.0)
            pen_p = pg.mkPen(color=DARK_ACCENT_POWER, width=2.0)
            pen_ch1 = pg.mkPen(color=SCOPE_CH1_COLOR, width=2.0)
            pen_ch2 = pg.mkPen(color=SCOPE_CH2_COLOR, width=2.0)

            self.curve_v = self.plot_widget.plot(name="PSU Voltage (V)", pen=pen_v)
            self.curve_i = self.plot_widget.plot(name="PSU Current (A)", pen=pen_i)
            self.curve_p = self.plot_widget.plot(name="PSU Power (W)", pen=pen_p)
            self.curve_ch1 = self.plot_widget.plot(name="Scope CH1 Vrms (V)", pen=pen_ch1)
            self.curve_ch2 = self.plot_widget.plot(name="Scope CH2 Vrms (V)", pen=pen_ch2)

            layout.addWidget(self.plot_widget, 1)
        else:
            self.plot_widget = QLabel("PyQtGraph not available.")
            layout.addWidget(self.plot_widget, 1)

        # HUD inspection label
        self.lbl_hud = QLabel("Cursor: Hover over plot trace to inspect multi-instrument values at matching timecode.")
        self.lbl_hud.setStyleSheet("font-size: 8pt; font-family: monospace; color: #8B94AD;")
        layout.addWidget(self.lbl_hud)

    def append_data(self, t: float, psu_vals: Dict[str, float], scope_vals: Dict[str, float]):
        self.t_data.append(t)
        v = psu_vals.get("voltage", 0.0)
        i = psu_vals.get("current", 0.0)
        p = psu_vals.get("power", 0.0)
        ch1 = scope_vals.get("ch1_vrms", 0.0)
        ch2 = scope_vals.get("ch2_vrms", 0.0)

        self.v_data.append(v)
        self.i_data.append(i)
        self.p_data.append(p)
        self.ch1_vrms_data.append(ch1)
        self.ch2_vrms_data.append(ch2)

        # Keep buffer bounded to last 5000 points
        if len(self.t_data) > 5000:
            self.t_data = self.t_data[-5000:]
            self.v_data = self.v_data[-5000:]
            self.i_data = self.i_data[-5000:]
            self.p_data = self.p_data[-5000:]
            self.ch1_vrms_data = self.ch1_vrms_data[-5000:]
            self.ch2_vrms_data = self.ch2_vrms_data[-5000:]

        if HAVE_PYQTGRAPH and not self.pub_mode_active:
            self.curve_v.setData(self.t_data, self.v_data)
            self.curve_i.setData(self.t_data, self.i_data)
            self.curve_p.setData(self.t_data, self.p_data)
            self.curve_ch1.setData(self.t_data, self.ch1_vrms_data)
            self.curve_ch2.setData(self.t_data, self.ch2_vrms_data)

        dur = self.t_data[-1] - self.t_data[0] if self.t_data else 0.0
        max_v = max(self.v_data) if self.v_data else 0.0
        max_i = max(self.i_data) if self.i_data else 0.0
        max_p = max(self.p_data) if self.p_data else 0.0
        max_ch1 = max(self.ch1_vrms_data) if self.ch1_vrms_data else 0.0

        self.lbl_stats.setText(
            f"Session Duration: {dur:.1f}s  |  Peak V: {max_v:.2f} V  |  Peak I: {max_i:.4f} A  |  Peak P: {max_p:.1f} W  |  CH1 Max: {max_ch1:.2f} V"
        )

    def _refresh_visibility(self):
        if HAVE_PYQTGRAPH:
            self.curve_v.setVisible(self.chkV.isChecked())
            self.curve_i.setVisible(self.chkI.isChecked())
            self.curve_p.setVisible(self.chkP.isChecked())
            self.curve_ch1.setVisible(self.chkCH1.isChecked())
            self.curve_ch2.setVisible(self.chkCH2.isChecked())

    def _autorange(self):
        if HAVE_PYQTGRAPH:
            self.plot_widget.autoRange()

    def _toggle_pub_mode(self):
        self.pub_mode_active = self.btn_pub_mode.isChecked()
        if self.pub_mode_active:
            self.btn_pub_mode.setText("🔒 Pub Mode (Locked)")
        else:
            self.btn_pub_mode.setText("📌 Pub Mode")

    def _open_settings_dialog(self):
        dlg = PlotPresentationDialog(self)
        if dlg.exec():
            opts = dlg.get_options()
            QMessageBox.information(self, "Export Options Configured", f"Export settings updated for {opts['ext']} format.")

    def set_theme(self, is_dark: bool):
        self.is_dark = is_dark
        if HAVE_PYQTGRAPH:
            bg = "#05070E" if is_dark else "#F8FAFC"
            fg = "#E8ECF5" if is_dark else "#0F172A"
            self.plot_widget.setBackground(bg)
            self.plot_widget.getAxis('bottom').setPen(fg)
            self.plot_widget.getAxis('left').setPen(fg)
