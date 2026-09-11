"""PSUTab — Benchtop Power Supply Control Card with Responsive Splitter and Collapsible sections."""
import math
from typing import Dict, Any

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
        QLabel, QLineEdit, QDoubleSpinBox, QPushButton, QCheckBox,
        QRadioButton, QButtonGroup, QProgressBar, QFrame, QSplitter,
        QScrollArea, QSizePolicy
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
        def __init__(self, text="", parent=None): pass
    class QLineEdit:
        def __init__(self, parent=None): pass
    class QDoubleSpinBox:
        def __init__(self, parent=None): pass
    class QPushButton:
        def __init__(self, text="", parent=None): pass
    class QCheckBox:
        def __init__(self, text="", parent=None): pass
    class QRadioButton:
        def __init__(self, text="", parent=None): pass
    class QButtonGroup:
        def __init__(self, parent=None): pass
    class QProgressBar:
        def __init__(self, parent=None): pass
    class QFrame:
        def __init__(self, parent=None): pass
    class QSplitter:
        def __init__(self, *args, parent=None): pass
    class QScrollArea:
        def __init__(self, parent=None): pass
    class QSizePolicy:
        class Policy:
            Preferred = 0
            Expanding = 1
    def pyqtSignal(*args, **kwargs):
        class Sig:
            def connect(self, s): pass
            def emit(self, *a): pass
        return Sig()

from ..widgets.metric_card import ModernMetricCard
from ..widgets.collapsible import CollapsibleSection
from ..styles.tokens import (
    DARK_ACCENT_VOLTAGE, DARK_ACCENT_CURRENT,
    DARK_ACCENT_POWER, DARK_ACCENT_RESISTANCE
)


class PSUTab(QWidget):
    """
    Primary benchtop instrument card representing the ETPS LAB-HP 41000 DC Source.
    Equipped with large readouts, remote setpoints, operating mode selectors, and hardware alarms.
    """

    set_voltage_requested = pyqtSignal(float)
    set_current_requested = pyqtSignal(float)
    set_power_requested = pyqtSignal(float)
    set_ovp_requested = pyqtSignal(float)
    output_state_requested = pyqtSignal(bool)
    operating_mode_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_connected = False
        self.is_local = False
        self.is_dark = True

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(10, 10, 10, 10)
        outer_layout.setSpacing(10)

        # Main horizontal splitter: Left panel (Readouts + Master Output) vs Right panel (Setpoints & Config)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # ---------------------------------------------------------------------
        # LEFT PANEL: Live Readout Cards & Master Output
        # ---------------------------------------------------------------------
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 6, 0)
        left_layout.setSpacing(10)

        # 4 Metric Cards (Voltage, Current, Power, Resistance)
        self.card_v = ModernMetricCard("OUTPUT VOLTAGE", "0.00", "V", DARK_ACCENT_VOLTAGE)
        self.card_i = ModernMetricCard("OUTPUT CURRENT", "0.0000", "A", DARK_ACCENT_CURRENT)
        self.card_p = ModernMetricCard("DELIVERED POWER", "0.0", "W", DARK_ACCENT_POWER)
        self.card_r = ModernMetricCard("CALCULATED LOAD", "---", "Ω", DARK_ACCENT_RESISTANCE)

        left_layout.addWidget(self.card_v)
        left_layout.addWidget(self.card_i)
        left_layout.addWidget(self.card_p)
        left_layout.addWidget(self.card_r)

        # Master Output Control Card
        card_out = QGroupBox("Master Power Output")
        out_layout = QVBoxLayout(card_out)
        out_layout.setContentsMargins(10, 12, 10, 10)
        out_layout.setSpacing(8)

        self.btn_output = QPushButton("⚡ OUTPUT OFF")
        self.btn_output.setObjectName("danger")
        self.btn_output.setFixedHeight(48)
        self.btn_output.setStyleSheet("font-size: 11pt; font-weight: 800; letter-spacing: 0.5px;")
        self.btn_output.clicked.connect(self._toggle_output)
        out_layout.addWidget(self.btn_output)

        self.lbl_local_warning = QLabel("Front Panel Locked (Remote Software Control)")
        self.lbl_local_warning.setStyleSheet("font-size: 8pt; color: #8B94AD;")
        self.lbl_local_warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        out_layout.addWidget(self.lbl_local_warning)

        left_layout.addWidget(card_out)
        left_layout.addStretch()

        self.splitter.addWidget(left_widget)

        # ---------------------------------------------------------------------
        # RIGHT PANEL: Setpoints & Config wrapped in QScrollArea
        # ---------------------------------------------------------------------
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(6, 0, 0, 0)
        right_layout.setSpacing(10)

        # 1. Collapsible Section: Remote Setpoints (Expanded by default)
        self.sec_setpoints = CollapsibleSection("Remote Setpoints & Compliance Limits")
        self.sec_setpoints.setStatus("V: 0.00V | I: 0.000A | P: 0W")

        setpoints_container = QWidget()
        sp_layout = QGridLayout(setpoints_container)
        sp_layout.setContentsMargins(0, 4, 0, 4)
        sp_layout.setHorizontalSpacing(10)
        sp_layout.setVerticalSpacing(8)

        # Voltage Setpoint
        sp_layout.addWidget(QLabel("Voltage Setpoint (U):"), 0, 0)
        self.spin_v = QDoubleSpinBox()
        self.spin_v.setRange(0.0, 1000.0)
        self.spin_v.setDecimals(2)
        self.spin_v.setSuffix(" V")
        self.spin_v.setSingleStep(1.0)
        sp_layout.addWidget(self.spin_v, 0, 1)

        self.btn_apply_v = QPushButton("Apply")
        self.btn_apply_v.setObjectName("primary")
        self.btn_apply_v.clicked.connect(lambda: self.set_voltage_requested.emit(self.spin_v.value()))
        sp_layout.addWidget(self.btn_apply_v, 0, 2)

        # Current Compliance Limit
        sp_layout.addWidget(QLabel("Current Limit (I):"), 1, 0)
        self.spin_i = QDoubleSpinBox()
        self.spin_i.setRange(0.0, 7.0)
        self.spin_i.setDecimals(4)
        self.spin_i.setSuffix(" A")
        self.spin_i.setSingleStep(0.1)
        sp_layout.addWidget(self.spin_i, 1, 1)

        self.btn_apply_i = QPushButton("Apply")
        self.btn_apply_i.setObjectName("primary")
        self.btn_apply_i.clicked.connect(lambda: self.set_current_requested.emit(self.spin_i.value()))
        sp_layout.addWidget(self.btn_apply_i, 1, 2)

        # Power Limit
        sp_layout.addWidget(QLabel("Power Limit (P):"), 2, 0)
        self.spin_p = QDoubleSpinBox()
        self.spin_p.setRange(0.0, 4000.0)
        self.spin_p.setDecimals(1)
        self.spin_p.setSuffix(" W")
        self.spin_p.setSingleStep(50.0)
        sp_layout.addWidget(self.spin_p, 2, 1)

        self.btn_apply_p = QPushButton("Apply")
        self.btn_apply_p.setObjectName("primary")
        self.btn_apply_p.clicked.connect(lambda: self.set_power_requested.emit(self.spin_p.value()))
        sp_layout.addWidget(self.btn_apply_p, 2, 2)

        # Over-Voltage Protection (OVP)
        sp_layout.addWidget(QLabel("Over-Voltage Prot (OVP):"), 3, 0)
        self.spin_ovp = QDoubleSpinBox()
        self.spin_ovp.setRange(0.0, 1050.0)
        self.spin_ovp.setDecimals(1)
        self.spin_ovp.setSuffix(" V")
        self.spin_ovp.setValue(1050.0)
        sp_layout.addWidget(self.spin_ovp, 3, 1)

        self.btn_apply_ovp = QPushButton("Apply")
        self.btn_apply_ovp.clicked.connect(lambda: self.set_ovp_requested.emit(self.spin_ovp.value()))
        sp_layout.addWidget(self.btn_apply_ovp, 3, 2)

        self.sec_setpoints.setContentWidget(setpoints_container)
        self.sec_setpoints.setExpanded(True)
        right_layout.addWidget(self.sec_setpoints)

        # 2. Collapsible Section: Operating Mode Selection (Collapsed by default)
        self.sec_mode = CollapsibleSection("Operating Mode Selection")
        self.sec_mode.setStatus("CV Mode")

        mode_container = QWidget()
        mode_layout = QHBoxLayout(mode_container)
        mode_layout.setContentsMargins(0, 4, 0, 4)
        mode_layout.setSpacing(15)

        self.mode_group = QButtonGroup(self)
        self.rb_cv = QRadioButton("Constant Voltage (CV)")
        self.rb_cc = QRadioButton("Constant Current (CC)")
        self.rb_cp = QRadioButton("Constant Power (CP)")
        self.rb_cv.setChecked(True)

        self.mode_group.addButton(self.rb_cv)
        self.mode_group.addButton(self.rb_cc)
        self.mode_group.addButton(self.rb_cp)

        self.rb_cv.toggled.connect(lambda chk: chk and self._on_mode_toggled("CV"))
        self.rb_cc.toggled.connect(lambda chk: chk and self._on_mode_toggled("CC"))
        self.rb_cp.toggled.connect(lambda chk: chk and self._on_mode_toggled("CP"))

        mode_layout.addWidget(self.rb_cv)
        mode_layout.addWidget(self.rb_cc)
        mode_layout.addWidget(self.rb_cp)
        mode_layout.addStretch()

        self.sec_mode.setContentWidget(mode_container)
        self.sec_mode.setExpanded(False)
        right_layout.addWidget(self.sec_mode)

        # 3. Collapsible Section: Hardware Safety & Trip Status (Collapsed by default)
        self.sec_status = CollapsibleSection("Hardware Safety & Trip Status")
        self.sec_status.setStatus("All Systems Nominal")

        status_container = QWidget()
        stat_layout = QGridLayout(status_container)
        stat_layout.setContentsMargins(0, 4, 0, 4)
        stat_layout.setHorizontalSpacing(10)
        stat_layout.setVerticalSpacing(8)

        self.badge_ovp = QLabel("● OVP TRIP")
        self.badge_ovp.setStyleSheet("font-weight: bold; color: #64748B; font-size: 9pt;")
        stat_layout.addWidget(self.badge_ovp, 0, 0)

        self.badge_ocp = QLabel("● OCP TRIP")
        self.badge_ocp.setStyleSheet("font-weight: bold; color: #64748B; font-size: 9pt;")
        stat_layout.addWidget(self.badge_ocp, 0, 1)

        self.badge_otp = QLabel("● OTP TRIP")
        self.badge_otp.setStyleSheet("font-weight: bold; color: #64748B; font-size: 9pt;")
        stat_layout.addWidget(self.badge_otp, 1, 0)

        self.badge_opp = QLabel("● OPP TRIP")
        self.badge_opp.setStyleSheet("font-weight: bold; color: #64748B; font-size: 9pt;")
        stat_layout.addWidget(self.badge_opp, 1, 1)

        self.sec_status.setContentWidget(status_container)
        self.sec_status.setExpanded(False)
        right_layout.addWidget(self.sec_status)

        right_layout.addStretch()
        right_scroll.setWidget(right_widget)

        self.splitter.addWidget(right_scroll)

        # Set Splitter Stretch Factors (35% Left, 65% Right)
        self.splitter.setStretchFactor(0, 35)
        self.splitter.setStretchFactor(1, 65)

        outer_layout.addWidget(self.splitter)

    def _on_mode_toggled(self, mode: str):
        self.sec_mode.setStatus(f"{mode} Mode")
        self.operating_mode_requested.emit(mode)

    def _toggle_output(self):
        curr = self.btn_output.property("active") == "true"
        new_state = not curr
        self.output_state_requested.emit(new_state)

    def update_telemetry(self, t_sec: float, v: float, i: float, p: float, r: float):
        self.card_v.set_value(f"{v:.2f}")
        self.card_i.set_value(f"{i:.4f}")
        self.card_p.set_value(f"{p:.1f}")

        if r > 0 and not math.isinf(r):
            if r > 1000.0:
                self.card_r.set_value(f"{r/1000.0:.2f} k")
            else:
                self.card_r.set_value(f"{r:.2f}")
        else:
            self.card_r.set_value("---")

    def update_output_state(self, is_on: bool):
        if is_on:
            self.btn_output.setText("⚡ OUTPUT ON")
            self.btn_output.setObjectName("success")
            self.btn_output.setProperty("active", "true")
        else:
            self.btn_output.setText("⚡ OUTPUT OFF")
            self.btn_output.setObjectName("danger")
            self.btn_output.setProperty("active", "false")
        self.btn_output.style().unpolish(self.btn_output)
        self.btn_output.style().polish(self.btn_output)

    def update_status_badges(self, ovp: bool, ocp: bool, otp: bool, opp: bool):
        self.badge_ovp.setStyleSheet("font-weight: bold; color: #EF4444; font-size: 9pt;" if ovp else "font-weight: bold; color: #64748B; font-size: 9pt;")
        self.badge_ocp.setStyleSheet("font-weight: bold; color: #EF4444; font-size: 9pt;" if ocp else "font-weight: bold; color: #64748B; font-size: 9pt;")
        self.badge_otp.setStyleSheet("font-weight: bold; color: #EF4444; font-size: 9pt;" if otp else "font-weight: bold; color: #64748B; font-size: 9pt;")
        self.badge_opp.setStyleSheet("font-weight: bold; color: #EF4444; font-size: 9pt;" if opp else "font-weight: bold; color: #64748B; font-size: 9pt;")

        tripped = []
        if ovp: tripped.append("OVP")
        if ocp: tripped.append("OCP")
        if otp: tripped.append("OTP")
        if opp: tripped.append("OPP")
        if tripped:
            self.sec_status.setStatus(f"TRIPPED: {', '.join(tripped)}")
        else:
            self.sec_status.setStatus("All Systems Nominal")

    def set_connected(self, connected: bool):
        self.is_connected = connected
        self.btn_output.setEnabled(connected and not self.is_local)
        self.btn_apply_v.setEnabled(connected and not self.is_local)
        self.btn_apply_i.setEnabled(connected and not self.is_local)
        self.btn_apply_p.setEnabled(connected and not self.is_local)
        self.btn_apply_ovp.setEnabled(connected and not self.is_local)
        self.rb_cv.setEnabled(connected and not self.is_local)
        self.rb_cc.setEnabled(connected and not self.is_local)
        self.rb_cp.setEnabled(connected and not self.is_local)

    def set_local_mode(self, is_local: bool):
        self.is_local = is_local
        if is_local:
            self.lbl_local_warning.setText("Front Panel ACTIVE (Local Physical Control)")
            self.lbl_local_warning.setStyleSheet("font-size: 8pt; color: #F59E0B; font-weight: bold;")
        else:
            self.lbl_local_warning.setText("Front Panel Locked (Remote Software Control)")
            self.lbl_local_warning.setStyleSheet("font-size: 8pt; color: #8B94AD;")
        self.set_connected(self.is_connected)

    def set_theme(self, is_dark: bool):
        self.is_dark = is_dark
        self.card_v.set_theme(is_dark)
        self.card_i.set_theme(is_dark)
        self.card_p.set_theme(is_dark)
        self.card_r.set_theme(is_dark)
