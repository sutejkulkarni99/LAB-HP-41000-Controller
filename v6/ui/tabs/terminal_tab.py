"""TerminalTab — Interactive ASCII / SCPI command console for multi-instrument bus inspection."""
import time
from typing import Dict, List

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel,
        QLineEdit, QTextEdit, QPushButton, QToolButton, QComboBox
    )
    from PyQt6.QtCore import Qt, pyqtSignal
except ImportError:
    class QWidget:
        def __init__(self, parent=None): pass
    class QVBoxLayout:
        def __init__(self, parent=None): pass
    class QHBoxLayout:
        def __init__(self, parent=None): pass
    class QLabel:
        def __init__(self, text=""): pass
    class QLineEdit:
        def __init__(self, parent=None): pass
    class QTextEdit:
        def __init__(self, parent=None): pass
    class QPushButton:
        def __init__(self, text=""): pass
    class QToolButton:
        def __init__(self, parent=None): pass
    class QComboBox:
        def __init__(self, parent=None): pass
    def pyqtSignal(*args, **kwargs):
        class Sig:
            def connect(self, s): pass
            def emit(self, *a): pass
        return Sig()


class TerminalTab(QWidget):
    """
    Direct low-level interactive terminal supporting both ASCII (ETPS LAB-HP)
    and IEEE-488.2 / SCPI-1999 (R&S RTB2000) command syntax.
    """

    command_send_requested = pyqtSignal(str, str)  # (instrument_id, command_str)

    LABHP_PRESETS = [
        ("IDN?", "ID"), ("Measure V", "MU"), ("Measure I", "MI"),
        ("Status", "STATUS"), ("Output State", "SB"), ("Limits", "LIMU"),
        ("Go Remote", "GTR"), ("Go Local", "GTL"), ("Save Setup", "SS")
    ]

    RTB2000_PRESETS = [
        ("*IDN?", "*IDN?"), ("*OPT?", "*OPT?"), ("Acq State?", "ACQ:STAT?"),
        ("CH1 Scale?", "CHAN1:SCAL?"), ("CH2 Scale?", "CHAN2:SCAL?"),
        ("Timebase?", "TIM:SCAL?"), ("Trigger Level?", "TRIG:A:LEV1?"),
        ("RUN", "RUN"), ("STOP", "STOP")
    ]

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Top Row: Instrument Target Selector & Quick Commands
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Target Instrument:"))

        self.combo_target = QComboBox()
        self.combo_target.addItem("ETPS LAB-HP 41000", "labhp_41000")
        self.combo_target.addItem("Rohde & Schwarz RTB2000", "rtb2000")
        self.combo_target.currentIndexChanged.connect(self._on_target_changed)
        top_row.addWidget(self.combo_target)

        top_row.addSpacing(15)
        top_row.addWidget(QLabel("Quick Presets:"))

        self.preset_container = QHBoxLayout()
        top_row.addLayout(self.preset_container)
        top_row.addStretch()

        layout.addLayout(top_row)

        # Output Log Console
        self.term_log = QTextEdit()
        self.term_log.setReadOnly(True)
        self.term_log.setStyleSheet("""
            QTextEdit {
                background-color: #0A0C10;
                color: #38BDF8;
                font-family: monospace;
                font-size: 9pt;
                border: 1px solid #1E232E;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.term_log, 1)

        # Command Input Field
        in_row = QHBoxLayout()
        self.lbl_cmd_type = QLabel("ASCII Command:")
        in_row.addWidget(self.lbl_cmd_type)

        self.txt_cmd = QLineEdit()
        self.txt_cmd.setPlaceholderText("Enter command (e.g. ID or *IDN? or CHAN1:SCAL?)...")
        self.txt_cmd.returnPressed.connect(self._send_input_command)
        in_row.addWidget(self.txt_cmd, 1)

        self.btn_send = QPushButton("SEND")
        self.btn_send.setObjectName("primary")
        self.btn_send.clicked.connect(self._send_input_command)
        in_row.addWidget(self.btn_send)

        self.btn_clear = QToolButton()
        self.btn_clear.setText("Clear")
        self.btn_clear.clicked.connect(self.term_log.clear)
        in_row.addWidget(self.btn_clear)

        layout.addLayout(in_row)

        self._populate_presets()

    def _on_target_changed(self):
        target_id = self.combo_target.currentData()
        if target_id == "rtb2000":
            self.lbl_cmd_type.setText("SCPI Command:")
        else:
            self.lbl_cmd_type.setText("ASCII Command:")
        self._populate_presets()

    def _populate_presets(self):
        # Clear existing buttons
        while self.preset_container.count():
            item = self.preset_container.takeAt(0)
            w = item.widget()
            if w: w.deleteLater()

        target_id = self.combo_target.currentData()
        presets = self.RTB2000_PRESETS if target_id == "rtb2000" else self.LABHP_PRESETS

        for label, cmd in presets:
            btn = QToolButton()
            btn.setText(label)
            btn.clicked.connect(lambda checked, c=cmd: self._send_command(c))
            self.preset_container.addWidget(btn)

    def _send_input_command(self):
        cmd = self.txt_cmd.text().strip()
        if cmd:
            self._send_command(cmd)
            self.txt_cmd.clear()

    def _send_command(self, cmd: str):
        target_id = self.combo_target.currentData()
        t_str = time.strftime("%H:%M:%S")
        self.term_log.append(f"<span style='color: #64748B;'>[{t_str}]</span> <span style='color: #F59E0B;'>[{target_id}]</span> <span style='color: #38BDF8;'>TX &gt;&gt; {cmd}</span>")
        self.command_send_requested.emit(target_id, cmd)

    def log_response(self, target_id: str, resp: str, is_error: bool = False):
        t_str = time.strftime("%H:%M:%S")
        if is_error:
            self.term_log.append(f"<span style='color: #64748B;'>[{t_str}]</span> <span style='color: #F59E0B;'>[{target_id}]</span> <span style='color: #EF4444;'>ERR &lt;&lt; {resp}</span>")
        else:
            self.term_log.append(f"<span style='color: #64748B;'>[{t_str}]</span> <span style='color: #F59E0B;'>[{target_id}]</span> <span style='color: #4ADE80;'>RX &lt;&lt; {resp}</span>")
