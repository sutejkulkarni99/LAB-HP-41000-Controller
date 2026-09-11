"""ChannelControlWidget — Channel vertical parameters control card (V/div, coupling, position)."""
from typing import Optional

from ..qt_compat import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QComboBox, QDoubleSpinBox, QPushButton, QCheckBox, pyqtSignal
)


class ChannelControlWidget(QGroupBox):
    """
    Dedicated channel strip panel allowing rapid adjustment of vertical deflection,
    probe attenuation, input coupling, and vertical position offset.
    """

    scale_changed = pyqtSignal(int, float)      # channel, scale_v_div
    state_changed = pyqtSignal(int, bool)       # channel, enabled
    position_changed = pyqtSignal(int, float)   # channel, pos_div
    coupling_changed = pyqtSignal(int, str)     # channel, coupling

    VOLT_DIV_OPTIONS = [
        ("1 mV/div", 0.001), ("2 mV/div", 0.002), ("5 mV/div", 0.005),
        ("10 mV/div", 0.010), ("20 mV/div", 0.020), ("50 mV/div", 0.050),
        ("100 mV/div", 0.100), ("200 mV/div", 0.200), ("500 mV/div", 0.500),
        ("1 V/div", 1.0), ("2 V/div", 2.0), ("5 V/div", 5.0), ("10 V/div", 10.0)
    ]

    def __init__(self, channel: int, color_hex: str, parent=None):
        super().__init__(f"CH{channel} Analog Input", parent)
        self.channel = channel
        self.color_hex = color_hex

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Header: Enable Toggle with color badge
        h_row = QHBoxLayout()
        self.btn_power = QPushButton(f"● CH{channel} ON")
        self.btn_power.setCheckable(True)
        self.btn_power.setChecked(True)
        self.btn_power.setStyleSheet(f"""
            QPushButton:checked {{
                background-color: #20252E;
                border: 2px solid {color_hex};
                color: {color_hex};
                font-weight: bold;
            }}
        """)
        self.btn_power.clicked.connect(self._on_toggle)
        h_row.addWidget(self.btn_power)
        layout.addLayout(h_row)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)

        # Scale V/Div
        grid.addWidget(QLabel("Scale:"), 0, 0)
        self.combo_scale = QComboBox()
        for label, val in self.VOLT_DIV_OPTIONS:
            self.combo_scale.addItem(label, val)
        self.combo_scale.setCurrentIndex(9)  # 1 V/div
        self.combo_scale.currentIndexChanged.connect(self._on_scale_changed)
        grid.addWidget(self.combo_scale, 0, 1)

        # Position (div)
        grid.addWidget(QLabel("Offset:"), 1, 0)
        self.spin_pos = QDoubleSpinBox()
        self.spin_pos.setRange(-5.0, 5.0)
        self.spin_pos.setSingleStep(0.2)
        self.spin_pos.setValue(0.0)
        self.spin_pos.setSuffix(" div")
        self.spin_pos.valueChanged.connect(self._on_pos_changed)
        grid.addWidget(self.spin_pos, 1, 1)

        # Coupling
        grid.addWidget(QLabel("Coupling:"), 2, 0)
        self.combo_coupling = QComboBox()
        self.combo_coupling.addItems(["DC 1MΩ", "AC 1MΩ", "GND"])
        self.combo_coupling.currentIndexChanged.connect(self._on_coupling_changed)
        grid.addWidget(self.combo_coupling, 2, 1)

        # Probe Attenuation
        grid.addWidget(QLabel("Probe:"), 3, 0)
        self.combo_probe = QComboBox()
        self.combo_probe.addItems(["1X", "10X", "100X"])
        self.combo_probe.setCurrentText("1X")
        grid.addWidget(self.combo_probe, 3, 1)

        layout.addLayout(grid)

    def _on_toggle(self, checked: bool):
        self.btn_power.setText(f"● CH{self.channel} ON" if checked else f"○ CH{self.channel} OFF")
        self.state_changed.emit(self.channel, checked)

    def _on_scale_changed(self, idx: int):
        val = self.combo_scale.currentData()
        if val is not None:
            self.scale_changed.emit(self.channel, float(val))

    def _on_pos_changed(self, val: float):
        self.position_changed.emit(self.channel, val)

    def _on_coupling_changed(self, idx: int):
        c_str = self.combo_coupling.currentText().split()[0]
        self.coupling_changed.emit(self.channel, c_str)

    def set_verified_scale(self, scale: float):
        for idx in range(self.combo_scale.count()):
            if abs(self.combo_scale.itemData(idx) - scale) < 1e-4:
                self.combo_scale.blockSignals(True)
                self.combo_scale.setCurrentIndex(idx)
                self.combo_scale.blockSignals(False)
                break

    def set_verified_state(self, state: bool):
        self.btn_power.blockSignals(True)
        self.btn_power.setChecked(state)
        self.btn_power.setText(f"● CH{self.channel} ON" if state else f"○ CH{self.channel} OFF")
        self.btn_power.blockSignals(False)
