"""MathPanelWidget — Dual-channel waveform math (ADD, SUB, MULT, FFT) controls."""
from ..qt_compat import (
    QGroupBox, QVBoxLayout, QGridLayout, QLabel,
    QComboBox, QCheckBox, QPushButton, pyqtSignal
)


class MathPanelWidget(QGroupBox):
    """
    Oscilloscope waveform math configuration card supporting algebraic operations
    (CH1+CH2, CH1-CH2, CH1*CH2) and Fast Fourier Transform (FFT) spectrum analysis.
    """

    math_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__("Waveform Math & FFT Engine", parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        self.chk_enable = QCheckBox("Enable Math Trace (Purple)")
        self.chk_enable.setChecked(False)
        self.chk_enable.toggled.connect(self._emit_config)
        layout.addWidget(self.chk_enable)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)

        grid.addWidget(QLabel("Operation:"), 0, 0)
        self.combo_op = QComboBox()
        self.combo_op.addItems([
            "CH1 + CH2 (Sum)",
            "CH1 - CH2 (Differential)",
            "CH1 * CH2 (Instant Power)",
            "FFT CH1 (Spectrum)",
            "FFT CH2 (Spectrum)"
        ])
        self.combo_op.currentIndexChanged.connect(self._emit_config)
        grid.addWidget(self.combo_op, 0, 1)

        grid.addWidget(QLabel("FFT Window:"), 1, 0)
        self.combo_window = QComboBox()
        self.combo_window.addItems(["Hann", "Hamming", "Blackman", "Flat Top", "Rectangular"])
        self.combo_window.currentIndexChanged.connect(self._emit_config)
        grid.addWidget(self.combo_window, 1, 1)

        layout.addLayout(grid)

    def _emit_config(self):
        op_text = self.combo_op.currentText()
        op_code = "ADD"
        if "CH1 - CH2" in op_text: op_code = "SUB"
        elif "CH1 * CH2" in op_text: op_code = "MUL"
        elif "FFT CH1" in op_text: op_code = "FFT1"
        elif "FFT CH2" in op_text: op_code = "FFT2"

        self.math_changed.emit({
            "enabled": self.chk_enable.isChecked(),
            "operation": op_code,
            "window": self.combo_window.currentText().lower()
        })
