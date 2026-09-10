"""ConnectionChip — Compact industrial instrument status chip with RTT latency and pulse dot."""
try:
    from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton
    from PyQt6.QtCore import Qt, pyqtSignal
except ImportError:
    class QFrame:
        def __init__(self, parent=None): pass
        def setObjectName(self, name): pass
        def setStyleSheet(self, s): pass
    class QHBoxLayout:
        def __init__(self, parent=None): pass
        def setContentsMargins(self, *a): pass
        def setSpacing(self, *a): pass
        def addWidget(self, *a): pass
        def addStretch(self): pass
    class QLabel:
        def __init__(self, text=""): pass
        def setStyleSheet(self, s): pass
        def setText(self, t): pass
    class QPushButton:
        def __init__(self, text=""): pass
    class Qt:
        class CursorShape:
            PointingHandCursor = 13
    def pyqtSignal(*args, **kwargs):
        class Sig:
            def connect(self, s): pass
            def emit(self, *a): pass
        return Sig()


class ConnectionChip(QFrame):
    """
    Compact status pill displaying instrument identifier, connection state dot,
    target IP/port, and real-time round-trip latency (RTT).
    """

    clicked = pyqtSignal(str)  # short_id

    def __init__(self, short_id: str, label_text: str, parent=None):
        super().__init__(parent)
        self.short_id = short_id
        self.label_text = label_text
        self.is_connected = False
        self.is_dark = True

        self.setObjectName("connection_chip")
        try:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        except Exception:
            pass

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(8)

        # Status indicator dot (●)
        self.lbl_dot = QLabel("●")
        self.lbl_dot.setStyleSheet("font-size: 10pt; color: #EF4444;")
        layout.addWidget(self.lbl_dot)

        # Instrument Label
        self.lbl_name = QLabel(label_text)
        self.lbl_name.setStyleSheet("font-weight: 700; font-size: 9pt; color: #E8EDF2;")
        layout.addWidget(self.lbl_name)

        # Latency / Details
        self.lbl_info = QLabel("Disconnected")
        self.lbl_info.setStyleSheet("font-size: 8.5pt; color: #8B95A5;")
        layout.addWidget(self.lbl_info)

        self._apply_style()

    def mousePressEvent(self, event):
        self.clicked.emit(self.short_id)
        super().mousePressEvent(event)

    def set_connected(self, connected: bool, endpoint: str = "", rtt_ms: float = 0.0):
        self.is_connected = connected
        if connected:
            self.lbl_dot.setText("●")
            self.lbl_dot.setStyleSheet("font-size: 10pt; color: #22C55E;")
            rtt_txt = f"{rtt_ms:.1f}ms" if rtt_ms > 0 else "OK"
            ep_txt = endpoint if endpoint else "Online"
            self.lbl_info.setText(f"{ep_txt} ({rtt_txt})")
            self.lbl_info.setStyleSheet("font-size: 8.5pt; color: #3FB58C;" if self.is_dark else "font-size: 8.5pt; color: #16A34A;")
        else:
            self.lbl_dot.setText("●")
            self.lbl_dot.setStyleSheet("font-size: 10pt; color: #EF4444;")
            self.lbl_info.setText("Disconnected")
            self.lbl_info.setStyleSheet("font-size: 8.5pt; color: #8B95A5;" if self.is_dark else "font-size: 8.5pt; color: #64748B;")

    def set_theme(self, is_dark: bool):
        self.is_dark = is_dark
        self._apply_style()

    def _apply_style(self):
        if self.is_dark:
            self.setStyleSheet("""
                QFrame#connection_chip {
                    background-color: #20252E;
                    border: 1px solid #2F3540;
                    border-radius: 14px;
                }
                QFrame#connection_chip:hover {
                    background-color: #262B33;
                    border: 1px solid #4A9BDB;
                }
            """)
            self.lbl_name.setStyleSheet("font-weight: 700; font-size: 9pt; color: #E8EDF2;")
        else:
            self.setStyleSheet("""
                QFrame#connection_chip {
                    background-color: #FFFFFF;
                    border: 1px solid #CBD5E1;
                    border-radius: 14px;
                }
                QFrame#connection_chip:hover {
                    background-color: #F1F5F9;
                    border: 1px solid #0284C7;
                }
            """)
            self.lbl_name.setStyleSheet("font-weight: 700; font-size: 9pt; color: #0F172A;")
