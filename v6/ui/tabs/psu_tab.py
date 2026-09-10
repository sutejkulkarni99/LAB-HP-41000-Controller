"""PSUTab — Benchtop Monitor & Control for ETPS LAB-HP 41000 (pixel-identical to v5)."""
import math
from typing import Dict, Any

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
        QLabel, QPushButton, QDoubleSpinBox, QCheckBox, QComboBox,
        QToolButton, QMessageBox
    )
    from PyQt6.QtCore import Qt, pyqtSignal
except ImportError:
    class QWidget:
        def __init__(self, parent=None): pass
    class QVBoxLayout:
        def __init__(self, parent=None): pass
    class QHBoxLayout:
        def __init__(self, parent=None): pass
    class QGridLayout:
        def __init__(self, parent=None): pass
    class QGroupBox:
        def __init__(self, title="", parent=None): pass
    class QLabel:
        def __init__(self, text=""): pass
    class QPushButton:
        def __init__(self, text=""): pass
    class QDoubleSpinBox:
        def __init__(self, parent=None): pass
    class QCheckBox:
        def __init__(self, text=""): pass
    class QComboBox:
        def __init__(self, parent=None): pass
    class QToolButton:
        def __init__(self, parent=None): pass
    def pyqtSignal(*args, **kwargs):
        class Sig:
            def connect(self, s): pass
            def emit(self, *a): pass
        return Sig()

from ..widgets.metric_card import ModernMetricCard
from ..plots.time_series_plot import TimeSeriesPlotWidget
from ..styles.tokens import (
    DARK_ACCENT_VOLTAGE, DARK_ACCENT_CURRENT, DARK_ACCENT_POWER, DARK_ACCENT_RESISTANCE,
    LIGHT_ACCENT_VOLTAGE, LIGHT_ACCENT_CURRENT, LIGHT_ACCENT_POWER, LIGHT_ACCENT_RESISTANCE
)


class PSUTab(QWidget):
    """
    Benchtop Monitor & Control tab providing verified setpoint adjustments,
    four-channel high-contrast vector readouts, hardware status alarm matrix,
    and live 60 FPS strip charting for the LAB-HP 41000 power supply.
    """

    set_voltage_requested = pyqtSignal(float)
    set_current_requested = pyqtSignal(float)
    set_power_requested = pyqtSignal(float)
    set_ovp_requested = pyqtSignal(float)
    output_state_requested = pyqtSignal(bool)
    mode_toggle_requested = pyqtSignal()
    operating_mode_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_dark = True
        self.is_local_mode = False

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(14)

        # ---------------------------------------------------------------------
        # Left Column: Controls, Setpoints, Status Matrix
        # ---------------------------------------------------------------------
        left_col = QVBoxLayout()
        left_col.setSpacing(10)

        # Output Switch Box
        out_box = QGroupBox("Master Output Power Stage")
        ob_layout = QVBoxLayout(out_box)
        ob_layout.setSpacing(6)

        self.btn_output_on = QPushButton("⚡ OUTPUT ON")
        self.btn_output_on.setObjectName("success")
        self.btn_output_on.setFixedHeight(38)
        self.btn_output_on.setEnabled(False)
        self.btn_output_on.clicked.connect(self._request_output_on)
        ob_layout.addWidget(self.btn_output_on)

        self.btn_output_off = QPushButton("OUTPUT STANDBY (OFF)")
        self.btn_output_off.setObjectName("danger")
        self.btn_output_off.setFixedHeight(34)
        self.btn_output_off.setEnabled(False)
        self.btn_output_off.clicked.connect(lambda: self.output_state_requested.emit(False))
        ob_layout.addWidget(self.btn_output_off)

        self.chk_high_volt_safety = QCheckBox("High Voltage Interlock Warning (> 50 V)")
        self.chk_high_volt_safety.setChecked(True)
        ob_layout.addWidget(self.chk_high_volt_safety)

        left_col.addWidget(out_box)

        # Setpoint Adjustments
        self.setpoint_box = QGroupBox("Target Setpoint Registers")
        self.setpoint_box_layout = QVBoxLayout(self.setpoint_box)
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        # Voltage
        grid.addWidget(QLabel("Target Voltage:"), 0, 0)
        self.spin_v_set = QDoubleSpinBox()
        self.spin_v_set.setRange(0.0, 1000.0)
        self.spin_v_set.setDecimals(2)
        self.spin_v_set.setSingleStep(1.0)
        self.spin_v_set.setSuffix(" V")
        grid.addWidget(self.spin_v_set, 0, 1)

        self.btn_apply_v = QToolButton()
        self.btn_apply_v.setText("Apply")
        self.btn_apply_v.clicked.connect(self._apply_voltage)
        grid.addWidget(self.btn_apply_v, 0, 2)

        # Current
        grid.addWidget(QLabel("Target Current:"), 1, 0)
        self.spin_i_set = QDoubleSpinBox()
        self.spin_i_set.setRange(0.0, 7.0)
        self.spin_i_set.setDecimals(4)
        self.spin_i_set.setSingleStep(0.1)
        self.spin_i_set.setSuffix(" A")
        grid.addWidget(self.spin_i_set, 1, 1)

        self.btn_apply_i = QToolButton()
        self.btn_apply_i.setText("Apply")
        self.btn_apply_i.clicked.connect(self._apply_current)
        grid.addWidget(self.btn_apply_i, 1, 2)

        # Power
        grid.addWidget(QLabel("Power Limit:"), 2, 0)
        self.spin_p_set = QDoubleSpinBox()
        self.spin_p_set.setRange(0.0, 4000.0)
        self.spin_p_set.setDecimals(1)
        self.spin_p_set.setValue(4000.0)
        self.spin_p_set.setSuffix(" W")
        grid.addWidget(self.spin_p_set, 2, 1)

        self.btn_apply_p = QToolButton()
        self.btn_apply_p.setText("Apply")
        self.btn_apply_p.clicked.connect(self._apply_power)
        grid.addWidget(self.btn_apply_p, 2, 2)

        # OVP
        grid.addWidget(QLabel("Over-Voltage (OVP):"), 3, 0)
        self.spin_ovp_set = QDoubleSpinBox()
        self.spin_ovp_set.setRange(0.0, 1100.0)
        self.spin_ovp_set.setDecimals(1)
        self.spin_ovp_set.setValue(1100.0)
        self.spin_ovp_set.setSuffix(" V")
        grid.addWidget(self.spin_ovp_set, 3, 1)

        self.btn_apply_ovp = QToolButton()
        self.btn_apply_ovp.setText("Apply")
        self.btn_apply_ovp.clicked.connect(self._apply_ovp)
        grid.addWidget(self.btn_apply_ovp, 3, 2)

        self.setpoint_box_layout.addLayout(grid)

        self.lbl_local_notice = QLabel("🔒 LOCAL MODE: Setpoints controlled at Front Panel")
        self.lbl_local_notice.setStyleSheet("""
            background-color: #291800;
            border: 1px solid #78350f;
            border-radius: 5px;
            color: #f59e0b;
            font-weight: 700;
            padding: 6px;
            font-size: 8.5pt;
        """)
        self.lbl_local_notice.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_local_notice.setVisible(False)
        self.setpoint_box_layout.addWidget(self.lbl_local_notice)

        left_col.addWidget(self.setpoint_box)

        # Operating Mode Selector
        mode_box = QGroupBox("Operating Mode")
        mb_layout = QHBoxLayout(mode_box)
        self.combo_op_mode = QComboBox()
        self.combo_op_mode.addItems(["UI", "UIP", "UIR", "PVSIM", "USER"])
        mb_layout.addWidget(self.combo_op_mode)

        self.btn_apply_mode = QPushButton("Set Mode")
        self.btn_apply_mode.clicked.connect(lambda: self.operating_mode_requested.emit(self.combo_op_mode.currentText()))
        mb_layout.addWidget(self.btn_apply_mode)
        left_col.addWidget(mode_box)

        # Hardware Status & Trips Badges
        status_box = QGroupBox("Hardware Status & Trips")
        s_layout = QGridLayout(status_box)
        s_layout.setSpacing(6)

        self.status_badges = {}
        status_items = [
            ("OVP", "OVP Trip", "#ef4444"),
            ("CurrLim", "Current Limit (CC)", "#f59e0b"),
            ("PowLim", "Power Limit (CP)", "#f59e0b"),
            ("Standby", "Standby (Off)", "#94a3b8"),
            ("Remote", "Remote Mode", "#0ea5e9"),
            ("Local", "Local Mode", "#f59e0b"),
        ]
        for idx, (key, label_txt, color) in enumerate(status_items):
            badge = QLabel(label_txt)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setStyleSheet("""
                background-color: #1a1c22;
                border: 1px solid #2b2f38;
                color: #555b68;
                font-size: 8pt;
                font-weight: 700;
                padding: 4px;
                border-radius: 4px;
            """)
            self.status_badges[key] = (badge, color)
            s_layout.addWidget(badge, idx // 2, idx % 2)

        left_col.addWidget(status_box)
        left_col.addStretch()

        main_layout.addLayout(left_col, 0)

        # ---------------------------------------------------------------------
        # Right Column: Vector Readouts + Real-time Telemetry Plot
        # ---------------------------------------------------------------------
        right_col = QVBoxLayout()
        right_col.setSpacing(12)

        # Cards Row
        cards_row = QHBoxLayout()
        cards_row.setSpacing(10)

        self.card_volt = ModernMetricCard("Voltage", "V", DARK_ACCENT_VOLTAGE)
        self.card_curr = ModernMetricCard("Current", "A", DARK_ACCENT_CURRENT)
        self.card_pow  = ModernMetricCard("Power", "W", DARK_ACCENT_POWER)
        self.card_res  = ModernMetricCard("Load Res.", "Ω", DARK_ACCENT_RESISTANCE)

        cards_row.addWidget(self.card_volt)
        cards_row.addWidget(self.card_curr)
        cards_row.addWidget(self.card_pow)
        cards_row.addWidget(self.card_res)
        right_col.addLayout(cards_row)

        # Real-time Trend Plot
        self.trend_plot = TimeSeriesPlotWidget("Real-Time PSU Telemetry Trend (60 FPS)")
        self.trend_plot.add_trace("voltage", "Voltage (V)", DARK_ACCENT_VOLTAGE)
        self.trend_plot.add_trace("current", "Current (A)", DARK_ACCENT_CURRENT)
        self.trend_plot.add_trace("power", "Power (W)", DARK_ACCENT_POWER)
        right_col.addWidget(self.trend_plot, 1)

        main_layout.addLayout(right_col, 1)

    def _request_output_on(self):
        v = self.spin_v_set.value()
        if self.chk_high_volt_safety.isChecked() and v > 50.0:
            res = QMessageBox.warning(
                self, "High Voltage Interlock Confirmation",
                f"You are engaging HIGH VOLTAGE output at {v:.1f} V (> 50 V).\nEnsure load isolation and circuit safety.",
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
            )
            if res != QMessageBox.StandardButton.Ok:
                return
        self.output_state_requested.emit(True)

    def _apply_voltage(self):
        v = self.spin_v_set.value()
        self.card_volt.update_setpoint(v, decimals=2)
        self.set_voltage_requested.emit(v)

    def _apply_current(self):
        i = self.spin_i_set.value()
        self.card_curr.update_setpoint(i, decimals=4)
        self.set_current_requested.emit(i)

    def _apply_power(self):
        p = self.spin_p_set.value()
        self.card_pow.update_setpoint(p, decimals=1)
        self.set_power_requested.emit(p)

    def _apply_ovp(self):
        ovp = self.spin_ovp_set.value()
        self.set_ovp_requested.emit(ovp)

    def update_telemetry(self, t_sec: float, v: float, i: float, p: float, r: float):
        self.card_volt.update_measurement(v, decimals=2)
        self.card_curr.update_measurement(i, decimals=4)
        self.card_pow.update_measurement(p, decimals=1)
        self.card_res.update_measurement(r if not math.isinf(r) else 9999.0, decimals=2)

        self.trend_plot.append_data_point(t_sec, {
            "voltage": v,
            "current": i,
            "power": p
        })

    def update_output_state(self, on: bool):
        if on:
            self.btn_output_on.setText("⚡ OUTPUT ACTIVE (ON)")
            self.btn_output_on.setStyleSheet("background-color: #15803D; border: 2px solid #4ADE80; color: #FFFFFF; font-weight: bold;")
            self.btn_output_off.setStyleSheet("")
        else:
            self.btn_output_on.setText("⚡ OUTPUT ON")
            self.btn_output_on.setStyleSheet("")
            self.btn_output_off.setStyleSheet("background-color: #450A0A; border: 2px solid #EF4444; color: #FCA5A5; font-weight: bold;")

    def update_status_badges(self, status: Dict[str, Any]):
        for key, (badge, color) in self.status_badges.items():
            active = False
            if key == "OVP" and status.get("ovp_trip", False): active = True
            elif key == "CurrLim" and status.get("current_limit", False): active = True
            elif key == "PowLim" and status.get("power_limit", False): active = True
            elif key == "Standby" and status.get("standby", False): active = True
            elif key == "Remote" and not self.is_local_mode: active = True
            elif key == "Local" and self.is_local_mode: active = True

            if active:
                badge.setStyleSheet(f"""
                    background-color: {color}22;
                    border: 1px solid {color};
                    color: {color};
                    font-size: 8pt;
                    font-weight: 700;
                    padding: 4px;
                    border-radius: 4px;
                """)
            else:
                badge.setStyleSheet("""
                    background-color: #1a1c22;
                    border: 1px solid #2b2f38;
                    color: #555b68;
                    font-size: 8pt;
                    font-weight: 700;
                    padding: 4px;
                    border-radius: 4px;
                """)

    def set_connected(self, connected: bool):
        self.btn_output_on.setEnabled(connected and not self.is_local_mode)
        self.btn_output_off.setEnabled(connected and not self.is_local_mode)
        self.spin_v_set.setEnabled(connected and not self.is_local_mode)
        self.spin_i_set.setEnabled(connected and not self.is_local_mode)
        self.spin_p_set.setEnabled(connected and not self.is_local_mode)
        self.spin_ovp_set.setEnabled(connected and not self.is_local_mode)
        self.btn_apply_v.setEnabled(connected and not self.is_local_mode)
        self.btn_apply_i.setEnabled(connected and not self.is_local_mode)
        self.btn_apply_p.setEnabled(connected and not self.is_local_mode)
        self.btn_apply_ovp.setEnabled(connected and not self.is_local_mode)
        self.btn_apply_mode.setEnabled(connected and not self.is_local_mode)

    def set_local_mode(self, is_local: bool):
        self.is_local_mode = is_local
        self.lbl_local_notice.setVisible(is_local)
        self.set_connected(True)

    def set_theme(self, is_dark: bool):
        self.is_dark = is_dark
        v_col = DARK_ACCENT_VOLTAGE if is_dark else LIGHT_ACCENT_VOLTAGE
        i_col = DARK_ACCENT_CURRENT if is_dark else LIGHT_ACCENT_CURRENT
        p_col = DARK_ACCENT_POWER if is_dark else LIGHT_ACCENT_POWER
        r_col = DARK_ACCENT_RESISTANCE if is_dark else LIGHT_ACCENT_RESISTANCE

        self.card_volt.set_theme(is_dark, v_col)
        self.card_curr.set_theme(is_dark, i_col)
        self.card_pow.set_theme(is_dark, p_col)
        self.card_res.set_theme(is_dark, r_col)
        self.trend_plot.set_theme(is_dark)
