"""SoftkeyBar — Bottom benchtop softkey action bar for oscilloscope automation."""
from ..qt_compat import QFrame, QHBoxLayout, QPushButton, pyqtSignal


class SoftkeyBar(QFrame):
    """
    Bottom softkey strip patterned after Rohde & Schwarz RTB2000 hardware front panel.
    Provides single-click access to autoscale, single-shot acquisition, and trace capture.
    """

    autoscale_clicked = pyqtSignal()
    single_capture_clicked = pyqtSignal()
    clear_sweeps_clicked = pyqtSignal()
    snapshot_clicked = pyqtSignal()
    cursor_snap_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #14171F;
                border-top: 1px solid #2F3540;
                padding: 4px;
            }
            QPushButton {
                font-size: 8.5pt;
                padding: 6px 10px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(8)

        self.btn_auto = QPushButton("⚡ AUTOSCALE")
        self.btn_auto.clicked.connect(self.autoscale_clicked.emit)
        layout.addWidget(self.btn_auto)

        self.btn_single = QPushButton("📸 CAPTURE SINGLE")
        self.btn_single.setObjectName("primary")
        self.btn_single.clicked.connect(self.single_capture_clicked.emit)
        layout.addWidget(self.btn_single)

        self.btn_clear = QPushButton("🗑 CLEAR SWEEPS")
        self.btn_clear.clicked.connect(self.clear_sweeps_clicked.emit)
        layout.addWidget(self.btn_clear)

        self.btn_snap_cursor = QPushButton("📍 SNAP CURSORS")
        self.btn_snap_cursor.clicked.connect(self.cursor_snap_clicked.emit)
        layout.addWidget(self.btn_snap_cursor)

        layout.addStretch()

        self.btn_snapshot = QPushButton("💾 SAVE WAVEFORM (.NPZ)")
        self.btn_snapshot.setObjectName("success")
        self.btn_snapshot.clicked.connect(self.snapshot_clicked.emit)
        layout.addWidget(self.btn_snapshot)
