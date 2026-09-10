"""SOATab — Safe Operating Area (SOA) power envelope visualizer (pixel-identical to v5)."""
import numpy as np
from typing import Dict, Any

try:
    from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
    from PyQt6.QtCore import Qt
    import pyqtgraph as pg
    HAVE_PYQTGRAPH = True
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
    HAVE_PYQTGRAPH = False


class SOATab(QWidget):
    """
    Safe Operating Area (SOA) workspace rendering the 1000 V × 7 A × 4000 W
    hyperbolic power envelope and live dynamic operating point marker.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_dark = True

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Header Description Banner
        soa_desc = QLabel(
            "Safe Operating Area (SOA): Shows the 1000 V × 7 A × 4000 W hyperbolic power envelope.\n"
            "The yellow dot tracks your real-time operating point (Voltage vs. Current) against the maximum hardware limit."
        )
        soa_desc.setStyleSheet("color: #94a3b8; font-size: 9.5pt;")
        layout.addWidget(soa_desc)

        # Live Operating State HUD
        self.hud_frame = QFrame()
        self.hud_frame.setStyleSheet("""
            QFrame {
                background-color: #16181D;
                border: 1px solid #282C37;
                border-radius: 6px;
                padding: 6px;
            }
        """)
        h_layout = QHBoxLayout(self.hud_frame)
        h_layout.setContentsMargins(10, 4, 10, 4)

        self.lbl_v_stat = QLabel("V: 0.00 V")
        self.lbl_v_stat.setStyleSheet("font-weight: 700; color: #38BDF8; font-family: monospace;")
        h_layout.addWidget(self.lbl_v_stat)

        self.lbl_i_stat = QLabel("I: 0.0000 A")
        self.lbl_i_stat.setStyleSheet("font-weight: 700; color: #4ADE80; font-family: monospace;")
        h_layout.addWidget(self.lbl_i_stat)

        self.lbl_p_stat = QLabel("P: 0.0 W (0.0% of 4000W)")
        self.lbl_p_stat.setStyleSheet("font-weight: 700; color: #FBBF24; font-family: monospace;")
        h_layout.addWidget(self.lbl_p_stat)

        h_layout.addStretch()

        self.lbl_safety_status = QLabel("STATUS: NORMAL")
        self.lbl_safety_status.setStyleSheet("font-weight: 800; color: #22C55E; font-size: 9.5pt;")
        h_layout.addWidget(self.lbl_safety_status)

        layout.addWidget(self.hud_frame)

        # Interactive Graph
        if HAVE_PYQTGRAPH:
            self.soa_plot = pg.PlotWidget()
            self.soa_plot.showGrid(x=True, y=True, alpha=0.2)
            self.soa_plot.setLabel('bottom', 'Voltage', units='V')
            self.soa_plot.setLabel('left', 'Current', units='A')
            self.soa_plot.setXRange(0, 1050)
            self.soa_plot.setYRange(0, 8)

            # Draw hyperbolic 4 kW boundary: I = min(7.0, 4000 / V)
            v_vals = np.linspace(10, 1000, 250)
            i_boundary = np.minimum(7.0, 4000.0 / v_vals)
            self.soa_plot.plot(
                v_vals, i_boundary,
                pen=pg.mkPen('#EF4444', width=2, style=Qt.PenStyle.DashLine),
                name="4000 W Limit"
            )

            # Real-time marker dot
            self.soa_marker = pg.ScatterPlotItem(
                size=14, pen=pg.mkPen('#FFFFFF', width=1.5), brush=pg.mkBrush('#FBBF24')
            )
            self.soa_plot.addItem(self.soa_marker)
            layout.addWidget(self.soa_plot, 1)
        else:
            lbl_fallback = QLabel("PyQtGraph is required for interactive hardware-accelerated SOA mapping.")
            layout.addWidget(lbl_fallback)

    def update_point(self, v: float, i: float, p: float):
        self.lbl_v_stat.setText(f"V: {v:.2f} V")
        self.lbl_i_stat.setText(f"I: {i:.4f} A")
        pct = (p / 4000.0) * 100.0
        self.lbl_p_stat.setText(f"P: {p:.1f} W ({pct:.1f}% of 4000W)")

        if pct > 95.0:
            self.lbl_safety_status.setText("STATUS: MAXIMUM LOAD WARNING")
            self.lbl_safety_status.setStyleSheet("font-weight: 800; color: #EF4444;")
        elif pct > 80.0:
            self.lbl_safety_status.setText("STATUS: HIGH LOAD")
            self.lbl_safety_status.setStyleSheet("font-weight: 800; color: #F59E0B;")
        else:
            self.lbl_safety_status.setText("STATUS: NORMAL")
            self.lbl_safety_status.setStyleSheet("font-weight: 800; color: #22C55E;")

        if HAVE_PYQTGRAPH:
            self.soa_marker.setData([v], [i])

    def set_theme(self, is_dark: bool):
        self.is_dark = is_dark
        if HAVE_PYQTGRAPH:
            bg = "#121418" if is_dark else "#F8FAFC"
            fg = "#E2E8F0" if is_dark else "#0F172A"
            self.soa_plot.setBackground(bg)
            self.soa_plot.getAxis('bottom').setPen(fg)
            self.soa_plot.getAxis('left').setPen(fg)
