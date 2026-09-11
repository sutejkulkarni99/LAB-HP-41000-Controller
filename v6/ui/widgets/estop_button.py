"""EStopButton — Latching Industrial Emergency Stop Button with Ctrl+E shortcut."""
from ..qt_compat import QPushButton, QKeySequence, QShortcut, pyqtSignal


class EStopButton(QPushButton):
    """
    Industrial Emergency Stop button with latching safety mechanism and Ctrl+E shortcut.
    Triggers immediate global shutdown across all connected high-voltage and output sources.
    """

    emergency_triggered = pyqtSignal()
    emergency_stopped = emergency_triggered
    emergency_cleared = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("🛑 E-STOP\n[Ctrl+E]", parent)
        self.setObjectName("emergency")
        self.setFixedSize(84, 84)
        self.setToolTip("Emergency Stop (Ctrl+E): Immediately cuts output across all connected instruments")
        self.latched = False

        self.clicked.connect(self._on_click)

        try:
            self._shortcut = QShortcut(QKeySequence("Ctrl+E"), self)
            self._shortcut.activated.connect(self.trigger)
        except Exception:
            pass

    def _on_click(self):
        if not self.latched:
            self.trigger()
        else:
            self.reset_latch()

    def trigger(self):
        """Engage latching emergency stop."""
        self.latched = True
        self.setText("LATCHED\n[Reset]")
        self.setProperty("latched", "true")
        self._refresh_style()
        self.emergency_triggered.emit()

    def reset_latch(self):
        """Disengage emergency latch to allow normal operation."""
        self.latched = False
        self.setText("🛑 E-STOP\n[Ctrl+E]")
        self.setProperty("latched", "false")
        self._refresh_style()
        self.emergency_cleared.emit()

    def _refresh_style(self):
        try:
            self.style().unpolish(self)
            self.style().polish(self)
        except Exception:
            pass
