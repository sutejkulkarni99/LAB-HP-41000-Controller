"""SessionTab — Multi-instrument unified session logging and manifest coordinator with collapsible sections."""
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any

from ..qt_compat import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QTextEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox, QFrame,
    QScrollArea, QSizePolicy, Qt, pyqtSignal
)

from ..widgets.collapsible import CollapsibleSection


class SessionTab(QWidget):
    """
    Unified Session Coordinator managing experiment metadata, manifest generation,
    synchronized timecode logging across all connected instruments, and session archival.
    """

    session_start_requested = pyqtSignal(dict)
    session_pause_requested = pyqtSignal()
    session_stop_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_logging = False
        self.active_session_dir: str = str(Path.cwd() / "sessions")

        main_vbox = QVBoxLayout(self)
        main_vbox.setContentsMargins(10, 10, 10, 10)
        main_vbox.setSpacing(10)

        # Top Card: Session Clock & Master Controls
        clock_card = QFrame()
        clock_card.setStyleSheet("""
            QFrame {
                background-color: #0E1220;
                border: 1px solid #1B2238;
                border-radius: 8px;
                padding: 6px;
            }
        """)
        c_layout = QHBoxLayout(clock_card)
        c_layout.setContentsMargins(10, 6, 10, 6)

        clock_box = QVBoxLayout()
        lbl_clock_title = QLabel("SYNCHRONIZED SESSION CLOCK")
        lbl_clock_title.setStyleSheet("font-size: 8pt; font-weight: 700; color: #8B94AD; letter-spacing: 1px;")
        self.lbl_clock = QLabel("00:00:00.000")
        self.lbl_clock.setStyleSheet("font-size: 24pt; font-weight: 900; font-family: monospace; color: #7DD3FC;")
        clock_box.addWidget(lbl_clock_title)
        clock_box.addWidget(self.lbl_clock)
        c_layout.addLayout(clock_box)

        c_layout.addStretch()

        # Big Buttons
        self.btn_start = QPushButton("▶ START RECORDING")
        self.btn_start.setObjectName("success")
        self.btn_start.setFixedHeight(44)
        self.btn_start.setStyleSheet("font-size: 10pt; font-weight: 800; padding: 0 16px;")
        self.btn_start.clicked.connect(self._on_start_clicked)
        c_layout.addWidget(self.btn_start)

        self.btn_pause = QPushButton("⏸ PAUSE")
        self.btn_pause.setFixedHeight(44)
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self.session_pause_requested.emit)
        c_layout.addWidget(self.btn_pause)

        self.btn_stop = QPushButton("⏹ STOP & SEAL")
        self.btn_stop.setObjectName("danger")
        self.btn_stop.setFixedHeight(44)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("font-size: 10pt; font-weight: 800; padding: 0 16px;")
        self.btn_stop.clicked.connect(self._on_stop_clicked)
        c_layout.addWidget(self.btn_stop)

        main_vbox.addWidget(clock_card)

        # Scrollable middle area for Collapsible sections
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 1. Collapsible Section: Metadata Configuration & Directory (Expanded)
        self.sec_metadata = CollapsibleSection("Session Manifest & Experiment Metadata")
        self.sec_metadata.setStatus("PROJ-LABHP-VAL-001")

        meta_container = QWidget()
        m_layout = QGridLayout(meta_container)
        m_layout.setContentsMargins(4, 4, 4, 4)
        m_layout.setHorizontalSpacing(10)
        m_layout.setVerticalSpacing(8)

        m_layout.addWidget(QLabel("Operator:"), 0, 0)
        self.txt_operator = QLineEdit("Lead Test Engineer")
        m_layout.addWidget(self.txt_operator, 0, 1)

        m_layout.addWidget(QLabel("Project / Test ID:"), 0, 2)
        self.txt_project = QLineEdit("PROJ-LABHP-VAL-001")
        m_layout.addWidget(self.txt_project, 0, 3)

        m_layout.addWidget(QLabel("Purpose / Description:"), 1, 0)
        self.txt_purpose = QLineEdit("Thermal stress and step-response verification under dynamic load")
        m_layout.addWidget(self.txt_purpose, 1, 1, 1, 3)

        m_layout.addWidget(QLabel("Storage Root Dir:"), 2, 0)
        self.txt_dir = QLineEdit(self.active_session_dir)
        m_layout.addWidget(self.txt_dir, 2, 1, 1, 2)

        self.btn_browse = QPushButton("Browse...")
        self.btn_browse.clicked.connect(self._browse_dir)
        m_layout.addWidget(self.btn_browse, 2, 3)

        self.sec_metadata.setContentWidget(meta_container)
        self.sec_metadata.setExpanded(True)
        layout.addWidget(self.sec_metadata)

        # 2. Collapsible Section: Multi-Instrument Logging Status Table (Expanded)
        self.sec_streams = CollapsibleSection("Active Multi-Instrument Storage Streams")
        self.sec_streams.setStatus("2 Streams Registered")

        tbl_container = QWidget()
        t_layout = QVBoxLayout(tbl_container)
        t_layout.setContentsMargins(4, 4, 4, 4)

        self.table = QTableWidget(2, 5)
        self.table.setHorizontalHeaderLabels([
            "Instrument Target", "Status", "Samples Logged", "Waveform Buffer", "Active File"
        ])
        if hasattr(self.table.horizontalHeader(), "setSectionResizeMode"):
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        instruments = [
            ("ETPS LAB-HP 41000", "Standby", "0 pts", "N/A", "telemetry_labhp.csv"),
            ("R&S RTB2000 Scope", "Standby", "0 pts", "0 frames", "waveforms_rtb2000.npz")
        ]
        for row, data in enumerate(instruments):
            for col, val in enumerate(data):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, col, item)

        t_layout.addWidget(self.table)
        self.sec_streams.setContentWidget(tbl_container)
        self.sec_streams.setExpanded(True)
        layout.addWidget(self.sec_streams)

        layout.addStretch()
        scroll_area.setWidget(scroll_content)
        main_vbox.addWidget(scroll_area, 1)

        # Bottom Actions & Live Log Console
        bot_row = QHBoxLayout()
        self.btn_open_folder = QPushButton("📂 Open Session Folder")
        self.btn_open_folder.clicked.connect(self._open_session_folder)
        bot_row.addWidget(self.btn_open_folder)

        bot_row.addStretch()
        self.lbl_session_status = QLabel("Status: Session Idle. Ready to record.")
        self.lbl_session_status.setStyleSheet("font-weight: 700; color: #8B94AD;")
        bot_row.addWidget(self.lbl_session_status)
        main_vbox.addLayout(bot_row)

        self.term_log = QTextEdit()
        self.term_log.setReadOnly(True)
        self.term_log.setFixedHeight(80)
        self.term_log.setStyleSheet("font-family: monospace; font-size: 8.5pt; background-color: #05070E;")
        main_vbox.addWidget(self.term_log)

    def _browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select Session Output Directory", self.txt_dir.text())
        if d:
            self.txt_dir.setText(d)
            self.active_session_dir = d

    def _open_session_folder(self):
        d = self.txt_dir.text()
        if os.path.exists(d):
            if sys.platform == "win32":
                os.startfile(d)
            elif sys.platform == "darwin":
                subprocess.run(["open", d])
            else:
                subprocess.run(["xdg-open", d])
        else:
            QMessageBox.warning(self, "Folder Not Found", f"Directory does not exist yet:\n{d}")

    def _on_start_clicked(self):
        meta = {
            "operator": self.txt_operator.text().strip(),
            "project": self.txt_project.text().strip(),
            "purpose": self.txt_purpose.text().strip(),
            "session_dir": self.txt_dir.text().strip()
        }
        self.is_logging = True
        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_stop.setEnabled(True)
        self.txt_operator.setEnabled(False)
        self.txt_project.setEnabled(False)
        self.txt_purpose.setEnabled(False)
        self.txt_dir.setEnabled(False)
        self.btn_browse.setEnabled(False)
        self.lbl_session_status.setText("Status: RECORDING SYNCHRONIZED MULTI-INSTRUMENT SESSION")
        self.lbl_session_status.setStyleSheet("font-weight: 700; color: #4ADE80;")
        self.log_message(f"Started session '{meta['project']}' by '{meta['operator']}'.")
        self.session_start_requested.emit(meta)

    def _on_stop_clicked(self):
        self.is_logging = False
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.txt_operator.setEnabled(True)
        self.txt_project.setEnabled(True)
        self.txt_purpose.setEnabled(True)
        self.txt_dir.setEnabled(True)
        self.btn_browse.setEnabled(True)
        self.lbl_session_status.setText("Status: SESSION COMPLETE & MANIFEST SEALED")
        self.lbl_session_status.setStyleSheet("font-weight: 700; color: #7DD3FC;")
        self.log_message("Stopped session and wrote manifest.json.")
        self.session_stop_requested.emit()

    def update_clock(self, clock_str: str):
        self.lbl_clock.setText(clock_str)

    def update_instrument_stats(self, row: int, status: str, samples: int, extra: str = ""):
        if row < self.table.rowCount():
            item_status = self.table.item(row, 1)
            if item_status: item_status.setText(status)
            item_samples = self.table.item(row, 2)
            if item_samples: item_samples.setText(f"{samples} pts")
            if extra:
                item_extra = self.table.item(row, 3)
                if item_extra: item_extra.setText(extra)

    def log_message(self, msg: str):
        self.term_log.append(f">> {msg}")
