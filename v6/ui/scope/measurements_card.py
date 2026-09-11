"""MeasurementsCard — Live automated scalar measurement readout card."""
from typing import Dict, Any

from ..qt_compat import QWidget, QVBoxLayout, QGridLayout, QLabel, QFrame, Qt

from ..styles.tokens import SCOPE_CH1_COLOR, SCOPE_CH2_COLOR


class MeasurementsCard(QWidget):
    """
    Dedicated readout panel displaying calibrated hardware measurement values
    (Vrms, Vpp, Frequency, Period) for active oscilloscope channels.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        # Header Row
        lbl_h_param = QLabel("PARAM")
        lbl_h_param.setStyleSheet("font-size: 7.5pt; font-weight: bold; color: #8B94AD;")
        grid.addWidget(lbl_h_param, 0, 0)

        lbl_h_ch1 = QLabel("CH1")
        lbl_h_ch1.setStyleSheet(f"font-size: 8pt; font-weight: 800; color: {SCOPE_CH1_COLOR};")
        grid.addWidget(lbl_h_ch1, 0, 1)

        lbl_h_ch2 = QLabel("CH2")
        lbl_h_ch2.setStyleSheet(f"font-size: 8pt; font-weight: 800; color: {SCOPE_CH2_COLOR};")
        grid.addWidget(lbl_h_ch2, 0, 2)

        # 1. Vrms
        lbl_rms = QLabel("Vrms:")
        lbl_rms.setStyleSheet("font-size: 8.5pt; color: #94A3B8;")
        grid.addWidget(lbl_rms, 1, 0)
        self.val_ch1_rms = QLabel("-- V")
        self.val_ch1_rms.setStyleSheet(f"font-family: monospace; font-weight: bold; color: {SCOPE_CH1_COLOR};")
        grid.addWidget(self.val_ch1_rms, 1, 1)
        self.val_ch2_rms = QLabel("-- V")
        self.val_ch2_rms.setStyleSheet(f"font-family: monospace; font-weight: bold; color: {SCOPE_CH2_COLOR};")
        grid.addWidget(self.val_ch2_rms, 1, 2)

        # 2. Vpp
        lbl_vpp = QLabel("Vpp:")
        lbl_vpp.setStyleSheet("font-size: 8.5pt; color: #94A3B8;")
        grid.addWidget(lbl_vpp, 2, 0)
        self.val_ch1_vpp = QLabel("-- V")
        self.val_ch1_vpp.setStyleSheet(f"font-family: monospace; font-weight: bold; color: {SCOPE_CH1_COLOR};")
        grid.addWidget(self.val_ch1_vpp, 2, 1)
        self.val_ch2_vpp = QLabel("-- V")
        self.val_ch2_vpp.setStyleSheet(f"font-family: monospace; font-weight: bold; color: {SCOPE_CH2_COLOR};")
        grid.addWidget(self.val_ch2_vpp, 2, 2)

        # 3. Frequency
        lbl_freq = QLabel("Frequency:")
        lbl_freq.setStyleSheet("font-size: 8.5pt; color: #94A3B8;")
        grid.addWidget(lbl_freq, 3, 0)
        self.val_ch1_freq = QLabel("-- Hz")
        self.val_ch1_freq.setStyleSheet(f"font-family: monospace; font-weight: bold; color: {SCOPE_CH1_COLOR};")
        grid.addWidget(self.val_ch1_freq, 3, 1)
        self.val_ch2_freq = QLabel("-- Hz")
        self.val_ch2_freq.setStyleSheet(f"font-family: monospace; font-weight: bold; color: {SCOPE_CH2_COLOR};")
        grid.addWidget(self.val_ch2_freq, 3, 2)

        layout.addLayout(grid)

    @staticmethod
    def _format_freq(hz: float) -> str:
        if hz <= 0.0 or hz > 1e11:
            return "-- Hz"
        if hz >= 1e6:
            return f"{hz / 1e6:.3f} MHz"
        if hz >= 1e3:
            return f"{hz / 1e3:.2f} kHz"
        return f"{hz:.1f} Hz"

    @staticmethod
    def _format_volt(v: float) -> str:
        if v == 0.0 or abs(v) > 1e6:
            return "-- V"
        if abs(v) < 0.1:
            return f"{v * 1000.0:.1f} mV"
        return f"{v:.3f} V"

    def update_metrics(self, metrics: Dict[str, Any]):
        """Update readouts from polled scope measurements."""
        if not metrics:
            return

        c1_rms = metrics.get("ch1_vrms", 0.0)
        c1_vpp = metrics.get("ch1_vpp", 0.0)
        c1_freq = metrics.get("ch1_freq_hz", 0.0)

        c2_rms = metrics.get("ch2_vrms", 0.0)
        c2_vpp = metrics.get("ch2_vpp", 0.0)
        c2_freq = metrics.get("ch2_freq_hz", 0.0)

        self.val_ch1_rms.setText(self._format_volt(c1_rms))
        self.val_ch1_vpp.setText(self._format_volt(c1_vpp))
        self.val_ch1_freq.setText(self._format_freq(c1_freq))

        self.val_ch2_rms.setText(self._format_volt(c2_rms))
        self.val_ch2_vpp.setText(self._format_volt(c2_vpp))
        self.val_ch2_freq.setText(self._format_freq(c2_freq))
