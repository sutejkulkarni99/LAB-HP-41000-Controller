#!/usr/bin/env python3
"""
LAB-HP 41000 DC Power Source Controller — Next-Gen Edition (v5)
================================================================================
High-performance GUI for ETPS LAB-HP 41000 (4 kW, 1000 V, 7 A) via LAN/Ethernet.
Communicates using the native ASCII protocol (Telnet/TCP port 10001).

Key Enhancements in v5:
- Hardware-Accelerated 60+ FPS Real-Time Plotting (PyQtGraph with Matplotlib fallback).
- Dedicated Local vs. Remote Mode Switch (GTL / GTR) with smart safety lock:
    * In Local Mode: Hardware is controlled at the physical front-panel knobs.
      Software setpoint controls are safely locked to prevent conflict, while
      Data Logging, live high-FPS graphing, telemetry readouts, SOA curve,
      and safety monitoring remain 100% active!
    * In Remote Mode: Full computer control of setpoints, limits, and output.
- Modern vector typography readouts (clean, industrial, no outdated 7-segment LCDs).
- Live Safe Operating Area (SOA) 2D curve with real-time operating point tracking.
- Non-blocking asynchronous priority command queue (zero UI freeze or stutter).
- Real-time calculated telemetry: Load Resistance (R = V/I) and Energy (Wh).
- Interactive HUD crosshair inspector with cursor coordinate tooltip.
- Robust network scanner, watchdog, CSV data logger, and ASCII diagnostic terminal.

Requirements:
    pip install PyQt6 pyqtgraph numpy
    (Optional fallback: matplotlib)

Author: Laboratory Automation Suite
Version: 5.0.0
"""

import sys
import os
import time
import datetime
import socket
import threading
import queue
import re
import csv
import math
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# -----------------------------------------------------------------------------
# PyQt6 Imports
# -----------------------------------------------------------------------------
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QGridLayout, QTabWidget, QGroupBox, QLabel, QLineEdit, QSpinBox,
        QDoubleSpinBox, QPushButton, QCheckBox, QTextEdit, QFileDialog,
        QMessageBox, QSplitter, QFrame, QProgressBar, QSizePolicy,
        QStatusBar, QComboBox, QCompleter, QToolButton, QStyle, QDialog,
        QDialogButtonBox, QFormLayout, QSlider, QListWidget, QListWidgetItem,
        QAbstractItemView, QRadioButton, QButtonGroup
    )
    from PyQt6.QtCore import (
        Qt, QTimer, QThread, pyqtSignal, QSettings, QEvent, QObject,
        QPointF, QRectF
    )
    from PyQt6.QtGui import (
        QFont, QColor, QPalette, QPixmap, QImage, QIcon, QKeySequence, QShortcut,
        QPainter, QPen, QBrush, QLinearGradient, QPdfWriter, QPageSize, QPageLayout
    )
    try:
        from PyQt6.QtSvg import QSvgGenerator
    except ImportError:
        QSvgGenerator = None
except ImportError:
    print("CRITICAL ERROR: PyQt6 is required to run LAB-HP Controller v5.")
    print("Please install it with: pip install PyQt6 pyqtgraph numpy")
    sys.exit(1)

# -----------------------------------------------------------------------------
# Optional High-Performance Plotting Engine (PyQtGraph)
# -----------------------------------------------------------------------------
HAVE_PYQTGRAPH = False
try:
    import pyqtgraph as pg
    try:
        import pyqtgraph.exporters
    except Exception:
        pass
    import numpy as np
    HAVE_PYQTGRAPH = True
    # Configure PyQtGraph defaults for smooth dark industrial rendering (Atmos & Media.io palette)
    pg.setConfigOption('background', '#0f1117')
    pg.setConfigOption('foreground', '#94a3b8')
    pg.setConfigOption('antialias', True)
except ImportError:
    HAVE_PYQTGRAPH = False
    try:
        import matplotlib
        matplotlib.use("QtAgg")
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
        from matplotlib.figure import Figure
    except ImportError:
        pass


# =============================================================================
# MODERN DARK STYLESHEET: "SLATE CONTROL" (Atmos, Media.io, UX Misfit, Toptal)
# #0F1117 (bg), #1A1D24 (cards), #262B33 (hover), #2F3540 (borders),
# #E8EDF2 (primary text), #8B95A5 (secondary)
# Accents: #4A9BDB (V), #3FB58C (I), #D4A04A (P), #9B7FD4 (R)
# =============================================================================
MODERN_DARK_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #0F1117;
    color: #E8EDF2;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 10pt;
}

/* Containers & Cards (Elevation Depth Level 1) */
QGroupBox {
    background-color: #1A1D24;
    border: 1px solid #2F3540;
    border-radius: 8px;
    margin-top: 14px;
    padding: 14px 10px 10px 10px;
    font-weight: 600;
    font-size: 9.5pt;
    color: #8B95A5;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    background-color: #1A1D24;
    border-radius: 3px;
    color: #E8EDF2;
}

/* Inputs & Spinboxes (Elevation Level 2) */
QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox, QListWidget {
    background-color: #20252E;
    border: 1px solid #2F3540;
    border-radius: 5px;
    padding: 5px 8px;
    color: #E8EDF2;
    font-size: 10pt;
    selection-background-color: #4A9BDB;
    selection-color: #0F1117;
}

QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus, QListWidget:focus {
    border: 1px solid #4A9BDB;
    background-color: #262B33;
}

QLineEdit:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled, QComboBox:disabled, QListWidget:disabled {
    background-color: #16181F;
    border-color: #262A33;
    color: #555E6D;
}

/* Modern Push Buttons */
QPushButton {
    background-color: #242933;
    border: 1px solid #2F3540;
    border-radius: 6px;
    padding: 6px 14px;
    color: #E8EDF2;
    font-weight: 600;
    font-size: 9.5pt;
}

QPushButton:hover {
    background-color: #262B33;
    border-color: #4A9BDB;
    color: #FFFFFF;
}

QPushButton:pressed {
    background-color: #1A1D24;
    border-color: #242933;
}

QPushButton:disabled {
    background-color: #16181F;
    border-color: #262A33;
    color: #555E6D;
}

/* Button Variants */
QPushButton#primary {
    background-color: #2563EB;
    border: 1px solid #3B82F6;
    color: #FFFFFF;
}
QPushButton#primary:hover {
    background-color: #1D4ED8;
    border-color: #60A5FA;
}

QPushButton#success {
    background-color: #15803D;
    border: 1px solid #3FB58C;
    color: #FFFFFF;
}
QPushButton#success:hover {
    background-color: #166534;
    border-color: #4ADE80;
}

QPushButton#danger {
    background-color: #991B1B;
    border: 1px solid #DC2626;
    color: #FFFFFF;
}
QPushButton#danger:hover {
    background-color: #7F1D1D;
    border-color: #EF4444;
}

/* Tool Buttons */
QToolButton {
    background-color: #242933;
    border: 1px solid #2F3540;
    border-radius: 5px;
    padding: 5px;
    color: #E8EDF2;
}
QToolButton:hover {
    background-color: #262B33;
    border-color: #4A9BDB;
}
QToolButton:pressed {
    background-color: #1A1D24;
}
QToolButton:disabled {
    background-color: #16181F;
    border-color: #262A33;
    color: #555E6D;
}

/* Industrial E-Stop Button */
QPushButton#emergency {
    background-color: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
                                      stop:0 #DC2626, stop:0.7 #991B1B, stop:1 #450A0A);
    border: 3px solid #D4A04A;
    border-radius: 42px;
    font-size: 11pt;
    font-weight: 800;
    letter-spacing: 0.5px;
    color: #FFFFFF;
    padding: 0;
}
QPushButton#emergency:hover {
    background-color: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
                                      stop:0 #EF4444, stop:0.7 #B91C1C, stop:1 #7F1D1D);
    border-color: #FBBF24;
}
QPushButton#emergency:disabled {
    background-color: #242933;
    border-color: #2F3540;
    color: #555E6D;
}
QPushButton#emergency[latched="true"] {
    background-color: #450A0A;
    border: 3px solid #DC2626;
    color: #FCA5A5;
}

/* Mode Switch Button */
QPushButton#mode_remote {
    background-color: #1E3A5F;
    border: 1px solid #4A9BDB;
    color: #E8EDF2;
    font-weight: bold;
    border-radius: 6px;
    padding: 6px 14px;
}
QPushButton#mode_remote:hover {
    background-color: #2563EB;
    border-color: #60A5FA;
}

QPushButton#mode_local {
    background-color: #78350F;
    border: 1px solid #D4A04A;
    color: #FEF3C7;
    font-weight: bold;
    border-radius: 6px;
    padding: 6px 14px;
}
QPushButton#mode_local:hover {
    background-color: #92400E;
    border-color: #FBBF24;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #2F3540;
    background-color: #1A1D24;
    border-radius: 6px;
    top: -1px;
}
QTabBar::tab {
    background-color: #20252E;
    border: 1px solid #2F3540;
    padding: 9px 20px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 600;
    color: #8B95A5;
}
QTabBar::tab:selected {
    background-color: #1A1D24;
    border-bottom: 2px solid #4A9BDB;
    color: #4A9BDB;
}
QTabBar::tab:hover:!selected {
    background-color: #262B33;
    color: #E8EDF2;
}

/* Text Terminal & Logs */
QTextEdit {
    background-color: #14171F;
    border: 1px solid #2F3540;
    border-radius: 6px;
    color: #E8EDF2;
    font-family: "JetBrains Mono", "SF Mono", "Consolas", "Courier New", monospace;
    font-size: 9pt;
    line-height: 1.4;
}

/* Checkboxes & Sliders */
QCheckBox {
    color: #E8EDF2;
    font-size: 9.5pt;
    spacing: 7px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #2F3540;
    background-color: #20252E;
}
QCheckBox::indicator:checked {
    background-color: #4A9BDB;
    border-color: #4A9BDB;
}

/* Status Bar */
QStatusBar {
    background-color: #1A1D24;
    border-top: 1px solid #2F3540;
    color: #8B95A5;
    font-size: 9pt;
}

/* Sliders */
QSlider::groove:horizontal {
    height: 5px;
    background: #2F3540;
    border-radius: 2px;
}
QSlider::sub-page:horizontal {
    background: #4A9BDB;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #E8EDF2;
    border: 1px solid #8B95A5;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover {
    background: #FFFFFF;
    border-color: #4A9BDB;
}

/* Dialogs */
QDialog {
    background-color: #0F1117;
    color: #E8EDF2;
}
"""


# =============================================================================
# MODERN LIGHT THEME STYLESHEET: "CLEAN LABORATORY"
# #F8FAFC (bg), #FFFFFF (cards), #E2E8F0 (borders), #F1F5F9 (hover),
# #0F172A (primary text), #475569 (secondary)
# Accents: #0284C7 (V), #16A34A (I), #D97706 (P), #9333EA (R)
# =============================================================================
MODERN_LIGHT_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #F8FAFC;
    color: #0F172A;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 10pt;
}

/* Containers & Cards */
QGroupBox {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    margin-top: 14px;
    padding: 14px 10px 10px 10px;
    font-weight: 600;
    font-size: 9.5pt;
    color: #475569;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    background-color: #FFFFFF;
    border-radius: 3px;
    color: #0F172A;
}

/* Inputs & Spinboxes */
QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox, QListWidget {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 5px;
    padding: 5px 8px;
    color: #0F172A;
    font-size: 10pt;
    selection-background-color: #0284C7;
    selection-color: #FFFFFF;
}

QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus, QListWidget:focus {
    border: 1px solid #0284C7;
    background-color: #FFFFFF;
}

QLineEdit:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled, QComboBox:disabled, QListWidget:disabled {
    background-color: #F1F5F9;
    border-color: #E2E8F0;
    color: #94A3B8;
}

/* Modern Push Buttons */
QPushButton {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 14px;
    color: #0F172A;
    font-weight: 600;
    font-size: 9.5pt;
}

QPushButton:hover {
    background-color: #F1F5F9;
    border-color: #0284C7;
    color: #0F172A;
}

QPushButton:pressed {
    background-color: #E2E8F0;
    border-color: #94A3B8;
}

QPushButton:disabled {
    background-color: #F8FAFC;
    border-color: #E2E8F0;
    color: #94A3B8;
}

/* Button Variants */
QPushButton#primary {
    background-color: #0284C7;
    border: 1px solid #0369A1;
    color: #FFFFFF;
}
QPushButton#primary:hover {
    background-color: #0369A1;
    border-color: #075985;
}

QPushButton#success {
    background-color: #16A34A;
    border: 1px solid #15803D;
    color: #FFFFFF;
}
QPushButton#success:hover {
    background-color: #15803D;
    border-color: #166534;
}

QPushButton#danger {
    background-color: #DC2626;
    border: 1px solid #B91C1C;
    color: #FFFFFF;
}
QPushButton#danger:hover {
    background-color: #B91C1C;
    border-color: #991B1B;
}

/* Tool Buttons */
QToolButton {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 5px;
    padding: 5px;
    color: #0F172A;
}
QToolButton:hover {
    background-color: #F1F5F9;
    border-color: #0284C7;
}
QToolButton:pressed {
    background-color: #E2E8F0;
}
QToolButton:disabled {
    background-color: #F8FAFC;
    border-color: #E2E8F0;
    color: #94A3B8;
}

/* Industrial E-Stop Button */
QPushButton#emergency {
    background-color: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
                                      stop:0 #DC2626, stop:0.7 #B91C1C, stop:1 #7F1D1D);
    border: 3px solid #D97706;
    border-radius: 42px;
    font-size: 11pt;
    font-weight: 800;
    letter-spacing: 0.5px;
    color: #FFFFFF;
    padding: 0;
}
QPushButton#emergency:hover {
    background-color: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
                                      stop:0 #EF4444, stop:0.7 #DC2626, stop:1 #991B1B);
    border-color: #F59E0B;
}
QPushButton#emergency:disabled {
    background-color: #E2E8F0;
    border-color: #CBD5E1;
    color: #94A3B8;
}
QPushButton#emergency[latched="true"] {
    background-color: #7F1D1D;
    border: 3px solid #DC2626;
    color: #FEE2E2;
}

/* Mode Switch Button */
QPushButton#mode_remote {
    background-color: #0284C7;
    border: 1px solid #0369A1;
    color: #FFFFFF;
    font-weight: bold;
    border-radius: 6px;
    padding: 6px 14px;
}
QPushButton#mode_remote:hover {
    background-color: #0369A1;
    border-color: #075985;
}

QPushButton#mode_local {
    background-color: #D97706;
    border: 1px solid #B45309;
    color: #FFFFFF;
    font-weight: bold;
    border-radius: 6px;
    padding: 6px 14px;
}
QPushButton#mode_local:hover {
    background-color: #B45309;
    border-color: #92400E;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #E2E8F0;
    background-color: #FFFFFF;
    border-radius: 6px;
    top: -1px;
}
QTabBar::tab {
    background-color: #F1F5F9;
    border: 1px solid #E2E8F0;
    padding: 9px 20px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 600;
    color: #475569;
}
QTabBar::tab:selected {
    background-color: #FFFFFF;
    border-bottom: 2px solid #0284C7;
    color: #0284C7;
}
QTabBar::tab:hover:!selected {
    background-color: #E2E8F0;
    color: #0F172A;
}

/* Text Terminal & Logs */
QTextEdit {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    color: #0F172A;
    font-family: "JetBrains Mono", "SF Mono", "Consolas", "Courier New", monospace;
    font-size: 9pt;
    line-height: 1.4;
}

/* Checkboxes & Sliders */
QCheckBox {
    color: #0F172A;
    font-size: 9.5pt;
    spacing: 7px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #CBD5E1;
    background-color: #FFFFFF;
}
QCheckBox::indicator:checked {
    background-color: #0284C7;
    border-color: #0284C7;
}

/* Status Bar */
QStatusBar {
    background-color: #F1F5F9;
    border-top: 1px solid #E2E8F0;
    color: #475569;
    font-size: 9pt;
}

/* Sliders */
QSlider::groove:horizontal {
    height: 5px;
    background: #E2E8F0;
    border-radius: 2px;
}
QSlider::sub-page:horizontal {
    background: #0284C7;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #FFFFFF;
    border: 1px solid #94A3B8;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover {
    background: #F8FAFC;
    border-color: #0284C7;
}

/* Dialogs */
QDialog {
    background-color: #F8FAFC;
    color: #0F172A;
}
"""


# =============================================================================
# MODERN VECTOR READOUT CARD WIDGET (Replaces 7-segment QLCDNumber)
# =============================================================================
class ModernMetricCard(QFrame):
    """
    Sleek, high-contrast vector metric readout card.
    Displays Primary Value, Unit, Target Setpoint, and Deviation (Delta).
    Supports dynamic dark (Slate Control) and light (Clean Laboratory) themes.
    """

    def __init__(self, title: str, unit: str, color_hex: str, parent=None):
        super().__init__(parent)
        self.title_text = title
        self.unit_text = unit
        self.accent_color = color_hex
        self.setpoint_val = 0.0
        self.actual_val = 0.0

        self.setObjectName("metric_card")
        self.setStyleSheet(f"""
            QFrame#metric_card {{
                background-color: #1A1D24;
                border: 1px solid #2F3540;
                border-radius: 8px;
            }}
            QFrame#metric_card:hover {{
                background-color: #262B33;
                border: 1px solid {self.accent_color};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        # Header Row: Title & Unit Badge
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        self.lbl_title = QLabel(title.upper())
        self.lbl_title.setStyleSheet("font-size: 8.5pt; font-weight: 700; letter-spacing: 0.8px; color: #8B95A5;")
        header_row.addWidget(self.lbl_title)

        header_row.addStretch()

        self.lbl_unit = QLabel(f"[{unit}]")
        self.lbl_unit.setStyleSheet(f"font-size: 8.5pt; font-weight: 700; color: {self.accent_color};")
        header_row.addWidget(self.lbl_unit)
        layout.addLayout(header_row)

        # Primary Vector Digits
        self.lbl_value = QLabel("0.00")
        self.lbl_value.setStyleSheet("""
            font-family: 'JetBrains Mono', 'SF Pro Display', 'Consolas', monospace;
            font-size: 26pt;
            font-weight: 700;
            color: #E8EDF2;
            margin: 2px 0;
        """)
        self.lbl_value.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.lbl_value)

        # Sub-stats row: Setpoint & Delta
        sub_row = QHBoxLayout()
        sub_row.setContentsMargins(0, 0, 0, 0)
        self.lbl_setpoint = QLabel("Set: 0.00")
        self.lbl_setpoint.setStyleSheet("font-size: 9pt; color: #8B95A5;")
        sub_row.addWidget(self.lbl_setpoint)

        sub_row.addStretch()

        self.lbl_delta = QLabel("Δ 0.00")
        self.lbl_delta.setStyleSheet("font-size: 9pt; font-family: monospace; color: #8B95A5;")
        sub_row.addWidget(self.lbl_delta)
        layout.addLayout(sub_row)

    def set_theme(self, is_dark: bool, accent_color: str = None):
        """Adapt metric card styling to Slate Control or Clean Laboratory."""
        if accent_color:
            self.accent_color = accent_color

        if is_dark:
            self.setStyleSheet(f"""
                QFrame#metric_card {{
                    background-color: #1A1D24;
                    border: 1px solid #2F3540;
                    border-radius: 8px;
                }}
                QFrame#metric_card:hover {{
                    background-color: #262B33;
                    border: 1px solid {self.accent_color};
                }}
            """)
            self.lbl_title.setStyleSheet("font-size: 8.5pt; font-weight: 700; letter-spacing: 0.8px; color: #8B95A5;")
            self.lbl_unit.setStyleSheet(f"font-size: 8.5pt; font-weight: 700; color: {self.accent_color};")
            self.lbl_value.setStyleSheet("""
                font-family: 'JetBrains Mono', 'SF Pro Display', 'Consolas', monospace;
                font-size: 26pt;
                font-weight: 700;
                color: #E8EDF2;
                margin: 2px 0;
            """)
            self.lbl_setpoint.setStyleSheet("font-size: 9pt; color: #8B95A5;")
        else:
            self.setStyleSheet(f"""
                QFrame#metric_card {{
                    background-color: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    border-radius: 8px;
                }}
                QFrame#metric_card:hover {{
                    background-color: #F1F5F9;
                    border: 1px solid {self.accent_color};
                }}
            """)
            self.lbl_title.setStyleSheet("font-size: 8.5pt; font-weight: 700; letter-spacing: 0.8px; color: #475569;")
            self.lbl_unit.setStyleSheet(f"font-size: 8.5pt; font-weight: 700; color: {self.accent_color};")
            self.lbl_value.setStyleSheet("""
                font-family: 'JetBrains Mono', 'SF Pro Display', 'Consolas', monospace;
                font-size: 26pt;
                font-weight: 700;
                color: #0F172A;
                margin: 2px 0;
            """)
            self.lbl_setpoint.setStyleSheet("font-size: 9pt; color: #475569;")

    def update_measurement(self, actual: float, decimals: int = 2):
        self.actual_val = actual
        fmt = f"{{:.{decimals}f}}"
        self.lbl_value.setText(fmt.format(actual))

        diff = self.actual_val - self.setpoint_val
        delta_sign = "+" if diff > 0.0001 else ("-" if diff < -0.0001 else "±")
        delta_str = f"Δ {delta_sign}{abs(diff):.{min(decimals, 3)}f} {self.unit_text}"

        if abs(diff) < 0.05:
            delta_color = "#22c55e"  # on target (green)
        elif abs(diff) < 1.0:
            delta_color = "#94a3b8"  # nominal (gray)
        else:
            delta_color = "#f59e0b"  # regulating or ramping (amber)

        self.lbl_delta.setText(delta_str)
        self.lbl_delta.setStyleSheet(f"font-size: 8.5pt; font-family: monospace; color: {delta_color};")

    def update_setpoint(self, setpoint: float, decimals: int = 2):
        self.setpoint_val = setpoint
        fmt = f"Set: {{:.{decimals}f}} {self.unit_text}"
        self.lbl_setpoint.setText(fmt.format(setpoint))
        self.update_measurement(self.actual_val, decimals)


# =============================================================================
# CHART PRESENTATION & EXPORT SETTINGS DIALOG
# =============================================================================

# =============================================================================
# ADVANCED PLOT TRACE STYLES & RENDERING HELPERS
# Continuous (solid, dashed, dotted, dash-dot, step) & Discrete (+, *, o, s, ^, d)
# =============================================================================
PLOT_STYLE_OPTIONS = [
    "Continuous: Solid Line (Default)",
    "Continuous: Dashed Line",
    "Continuous: Dotted Line",
    "Continuous: Dash-Dot Line",
    "Continuous: Step Plot (Sample & Hold)",
    "Discrete: Plus Marker (+)",
    "Discrete: Cross Marker (x)",
    "Discrete: Star Marker (*)",
    "Discrete: Circle Marker (o)",
    "Discrete: Square Marker (s)",
    "Discrete: Triangle Marker (^)",
    "Discrete: Diamond Marker (d)",
    "Combined: Line with Circle Markers",
    "Combined: Line with Plus Markers",
    "Combined: Line with Cross Markers",
    "Combined: Line with Star Markers"
]

def parse_plot_style(style_str: str):
    """
    Parses user-chosen plot style into PyQtGraph and Matplotlib parameters.
    Returns: (pg_symbol, symbol_size, mpl_linestyle, mpl_marker, is_step)
    """
    s = (style_str or "").strip()
    # Defaults
    pg_symbol = None
    mpl_linestyle = "-"
    mpl_marker = None
    is_step = False

    if "Dashed" in s:
        mpl_linestyle = "--"
    elif "Dotted" in s:
        mpl_linestyle = ":"
    elif "Dash-Dot" in s:
        mpl_linestyle = "-."
    elif "Step" in s:
        is_step = True
        mpl_linestyle = "-"

    # Discrete or Combined
    if "Plus" in s:
        pg_symbol = "+"
        mpl_marker = "+"
    elif "Cross" in s:
        pg_symbol = "x"
        mpl_marker = "x"
    elif "Star" in s:
        pg_symbol = "star"
        mpl_marker = "*"
    elif "Circle" in s:
        pg_symbol = "o"
        mpl_marker = "o"
    elif "Square" in s:
        pg_symbol = "s"
        mpl_marker = "s"
    elif "Triangle" in s:
        pg_symbol = "t"
        mpl_marker = "^"
    elif "Diamond" in s:
        pg_symbol = "d"
        mpl_marker = "D"

    # If purely discrete (no "Combined" and no "Continuous"), suppress line
    if "Discrete" in s:
        mpl_linestyle = "None"

    return pg_symbol, mpl_linestyle, mpl_marker, is_step

def apply_pyqtgraph_curve_style(curve, color_hex: str, line_width: float, style_str: str, marker_size: int = 6):
    """Configures PyQtGraph PlotDataItem for continuous, discrete, or combined traces."""
    if not curve or not HAVE_PYQTGRAPH:
        return
    import pyqtgraph as pg
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QColor

    pg_symbol, mpl_ls, _, is_step = parse_plot_style(style_str)

    # Line Pen
    if "Discrete" in (style_str or ""):
        pen = None
    else:
        q_pen_style = Qt.PenStyle.SolidLine
        if "Dashed" in (style_str or ""):
            q_pen_style = Qt.PenStyle.DashLine
        elif "Dotted" in (style_str or ""):
            q_pen_style = Qt.PenStyle.DotLine
        elif "Dash-Dot" in (style_str or ""):
            q_pen_style = Qt.PenStyle.DashDotLine
        pen = pg.mkPen(color=color_hex, width=line_width, style=q_pen_style)

    curve.setPen(pen)

    # Symbol Configuration
    if pg_symbol:
        curve.setSymbol(pg_symbol)
        curve.setSymbolSize(marker_size)
        qcol = QColor(color_hex)
        curve.setSymbolPen(pg.mkPen(color=color_hex, width=1.2))
        curve.setSymbolBrush(pg.mkBrush(qcol))
    else:
        curve.setSymbol(None)

def get_matplotlib_plot_kwargs(color_hex: str, line_width: float, style_str: str, marker_size: int = 6) -> dict:
    """Produces kwargs dictionary for matplotlib ax.plot()."""
    pg_symbol, mpl_ls, mpl_marker, is_step = parse_plot_style(style_str)
    kw = {
        "color": color_hex,
        "linewidth": line_width if mpl_ls != "None" else 0,
        "linestyle": mpl_ls,
    }
    if is_step:
        kw["drawstyle"] = "steps-post"
    if mpl_marker:
        kw["marker"] = mpl_marker
        kw["markersize"] = marker_size
        kw["markeredgecolor"] = color_hex
        kw["markerfacecolor"] = color_hex
    return kw

# =============================================================================
# SMART LAYOUT, METADATA COMPANION & LATEX EXPORT UTILITIES
# =============================================================================
def calculate_lowest_density_quadrant(t_data: list, traces_dict: dict) -> tuple:
    """
    Analyzes spatial distribution of waveform points to locate the quadrant with the
    least visual occlusion for automatic legend placement.
    Returns: (mpl_loc, pyqtgraph_loc)
    """
    if not t_data or not traces_dict:
        return "upper right", "Top-Right"

    t_min = min(t_data)
    t_max = max(t_data)
    t_span = (t_max - t_min) or 1.0

    all_y = []
    for k, y_series in traces_dict.items():
        if not y_series:
            continue
        for idx in range(min(len(t_data), len(y_series))):
            y_val = y_series[idx]
            if y_val is not None and not math.isnan(y_val) and not math.isinf(y_val):
                all_y.append(y_val)

    if not all_y:
        return "upper right", "Top-Right"

    y_min = min(all_y)
    y_max = max(all_y)
    y_span = (y_max - y_min) or 1.0

    counts = {
        ("upper right", "Top-Right"): 0,
        ("upper left", "Top-Left"): 0,
        ("lower right", "Bottom-Right"): 0,
        ("lower left", "Bottom-Left"): 0,
    }

    step = max(1, len(t_data) // 500)
    for k, y_series in traces_dict.items():
        if not y_series:
            continue
        n = min(len(t_data), len(y_series))
        for idx in range(0, n, step):
            t_val = t_data[idx]
            y_val = y_series[idx]
            if y_val is None or math.isnan(y_val) or math.isinf(y_val):
                continue
            norm_x = (t_val - t_min) / t_span
            norm_y = (y_val - y_min) / y_span

            is_top = (norm_y >= 0.5)
            is_right = (norm_x >= 0.5)

            if is_top and is_right:
                counts[("upper right", "Top-Right")] += 1
            elif is_top and not is_right:
                counts[("upper left", "Top-Left")] += 1
            elif not is_top and is_right:
                counts[("lower right", "Bottom-Right")] += 1
            else:
                counts[("lower left", "Bottom-Left")] += 1

    best_pair = min(counts.keys(), key=lambda k: counts[k])
    return best_pair


def calculate_percentile_limits(traces_dict: dict, p_low=5.0, p_high=95.0, margin=0.08):
    """
    Computes 5th to 95th percentile bounds across active traces to suppress inrush
    transient spikes from flattening the steady-state waveform.
    """
    all_vals = []
    for k, series in traces_dict.items():
        if not series:
            continue
        for v in series:
            if v is not None and not math.isnan(v) and not math.isinf(v):
                all_vals.append(float(v))

    if len(all_vals) < 10:
        return None

    try:
        if HAVE_NUMPY:
            arr = np.array(all_vals)
            y_low = float(np.percentile(arr, p_low))
            y_high = float(np.percentile(arr, p_high))
        else:
            sorted_vals = sorted(all_vals)
            n = len(sorted_vals)
            idx_low = int(n * (p_low / 100.0))
            idx_high = min(n - 1, int(n * (p_high / 100.0)))
            y_low = sorted_vals[idx_low]
            y_high = sorted_vals[idx_high]

        span = (y_high - y_low)
        if span <= 1e-6:
            span = max(abs(y_high) * 0.1, 1.0)
        return (y_low - margin * span, y_high + margin * span)
    except Exception:
        return None


def generate_companion_metadata(export_filepath: str, plot_settings: dict, data_dict: dict, stats_dict: dict = None) -> str:
    """
    Writes a companion .meta JSON file alongside an exported plot containing full provenance,
    telemetry statistical moments, acquisition timestamps, and publication configuration.
    """
    meta_path = str(Path(export_filepath).with_suffix(Path(export_filepath).suffix + ".meta"))
    t = data_dict.get('t', [])
    duration_s = (t[-1] - t[0]) if (t and len(t) > 1) else 0.0

    channels_meta = {}
    label_map = {'v': 'Voltage (V)', 'i': 'Current (A)', 'p': 'Power (W)', 'r': 'Resistance (Ω)'}
    for ch_key, ch_label in label_map.items():
        vals = [v for v in data_dict.get(ch_key, []) if v is not None and not math.isnan(v) and not math.isinf(v)]
        if vals:
            channels_meta[ch_label] = {
                "count": len(vals),
                "min": round(min(vals), 4),
                "max": round(max(vals), 4),
                "mean": round(sum(vals) / len(vals), 4),
            }

    meta_doc = {
        "provenance": {
            "instrument": "ETPS LAB-HP 41000 DC Power Source (4 kW, 1000 V, 7 A)",
            "controller_software": "LAB-HP Controller v5 Next-Gen Edition",
            "export_timestamp_iso": datetime.datetime.now().isoformat(),
            "target_artifact": Path(export_filepath).name,
            "publication_preset": plot_settings.get("publication_preset", "Custom"),
            "watermark_footnote": plot_settings.get("watermark_text", "ETPS LAB-HP 41000 Telemetry"),
        },
        "session_summary": {
            "duration_seconds": round(duration_s, 3),
            "sample_count": len(t),
            "channels_recorded": list(channels_meta.keys()),
        },
        "channel_statistics": channels_meta,
        "presentation_settings": {
            "title": plot_settings.get("title", ""),
            "font_family": plot_settings.get("font_family", "Default"),
            "font_size_pt": plot_settings.get("font_size", 10),
            "line_width_px": plot_settings.get("line_width", 2.0),
            "legend_loc": plot_settings.get("legend_loc", "Top-Right"),
            "export_dpi": plot_settings.get("export_dpi", 300),
            "theme": plot_settings.get("export_theme", "Default"),
            "auto_limits_percentile": plot_settings.get("auto_limits_percentile", False),
            "transparent_pdf": plot_settings.get("transparent_pdf", False),
        }
    }
    if stats_dict:
        meta_doc["session_summary"].update(stats_dict)

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta_doc, f, indent=2)
    return meta_path


def export_tikz_pgf(filepath: str, data_dict: dict, plot_settings: dict, is_export_dark: bool = False):
    """
    Exports clean, publication-grade LaTeX TikZ / pgfplots code (.pgf or .tex).
    Natively compatible with LaTeX documents via \\usepackage{pgfplots}.
    """
    t = data_dict.get('t', [])
    if not t:
        raise ValueError("No time series data available for LaTeX TikZ export.")

    title_text = plot_settings.get("title", "LAB-HP 41000 Telemetry")
    show_title = plot_settings.get("show_title", True)
    x_lbl = plot_settings.get("x_label", "Elapsed Time")
    x_unit = plot_settings.get("x_unit", "s")
    x_full = f"{x_lbl} ({x_unit})" if x_unit else x_lbl
    y_lbl = plot_settings.get("y_label", "Magnitude")
    y_unit = plot_settings.get("y_unit", "")
    y_full = f"{y_lbl} ({y_unit})" if y_unit else y_lbl
    lw = plot_settings.get("line_width", 1.5)

    max_pts = 600
    stride = max(1, len(t) // max_pts)

    tikz_lines = [
        r"% ============================================================================",
        r"% Generated by ETPS LAB-HP 41000 Controller v5 — LaTeX TikZ / pgfplots Export",
        f"% Timestamp: {datetime.datetime.now().isoformat()}",
        f"% Publication Preset: {plot_settings.get('publication_preset', 'Custom')}",
        r"% Required LaTeX Preamble: \usepackage{pgfplots} \pgfplotsset{compat=1.18}",
        r"% ============================================================================",
        r"\begin{tikzpicture}",
        r"\begin{axis}[",
        r"    width=13.5cm, height=7.5cm,",
        f"    xlabel={{{x_full}}},",
        f"    ylabel={{{y_full}}},",
    ]
    if show_title and title_text:
        tikz_lines.append(f"    title={{{title_text}}},")
    tikz_lines.extend([
        r"    grid=both,",
        r"    grid style={line width=.1pt, draw=gray!25},",
        r"    major grid style={line width=.2pt, draw=gray!50},",
        r"    legend pos=north east,",
        r"    legend cell align={left},",
        r"    legend style={font=\footnotesize},",
        r"    tick label style={font=\footnotesize},",
        r"    label style={font=\small},",
        r"]"
    ])

    color_map = {
        'v': ("blue!75!black", "Voltage (V)"),
        'i': ("teal!85!black", "Current (A)"),
        'p': ("orange!85!black", "Power (W)"),
        'r': ("violet!85!black", "Resistance (\\Omega)")
    }

    trace_order_pref = plot_settings.get("trace_order", ["Voltage (V)", "Current (A)", "Power (W)", "Resistance (Ω)"])
    key_order = []
    for pref in trace_order_pref:
        if "Voltage" in pref and 'v' in data_dict and data_dict['v']: key_order.append('v')
        elif "Current" in pref and 'i' in data_dict and data_dict['i']: key_order.append('i')
        elif "Power" in pref and 'p' in data_dict and data_dict['p']: key_order.append('p')
        elif "Resistance" in pref and 'r' in data_dict and data_dict['r']: key_order.append('r')

    if not key_order:
        key_order = [k for k in ['v', 'i', 'p', 'r'] if k in data_dict and data_dict[k]]

    for k in key_order:
        col_tex, label_tex = color_map[k]
        series = data_dict[k]
        tikz_lines.append(f"\\addplot[color={col_tex}, line width={lw:.1f}pt] coordinates {{")
        coord_buf = []
        n = min(len(t), len(series))
        for idx in range(0, n, stride):
            t_val = t[idx]
            y_val = series[idx]
            if y_val is None or math.isnan(y_val) or math.isinf(y_val):
                continue
            coord_buf.append(f"({t_val:.3f}, {y_val:.3f})")
            if len(coord_buf) >= 8:
                tikz_lines.append("    " + " ".join(coord_buf))
                coord_buf = []
        if coord_buf:
            tikz_lines.append("    " + " ".join(coord_buf))
        tikz_lines.append("};")
        tikz_lines.append(f"\\addlegendentry{{{label_tex}}}")

    tikz_lines.extend([
        r"\end{axis}",
        r"\end{tikzpicture}"
    ])

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(tikz_lines) + "\n")


class BatchExportDialog(QDialog):
    """
    Comprehensive dialog for batch exporting all active telemetry traces:
    - Multi-Panel publication PDF document
    - Individual trace raster/vector image files (V, I, P, R)
    - Companion metadata (.meta) JSON file
    - LaTeX TikZ / PGF export
    - High-DPI and Publication Theme selection
    """
    def __init__(self, parent=None, default_name="session_batch"):
        super().__init__(parent)
        self.setWindowTitle("Batch Export Telemetry Suite")
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        grp_target = QGroupBox("Target Directory & File Prefix")
        g1 = QGridLayout(grp_target)
        g1.addWidget(QLabel("Output Directory:"), 0, 0)
        self.txt_dir = QLineEdit(str(Path.cwd()))
        g1.addWidget(self.txt_dir, 0, 1)
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._browse_dir)
        g1.addWidget(btn_browse, 0, 2)

        g1.addWidget(QLabel("File Prefix:"), 1, 0)
        self.txt_prefix = QLineEdit(default_name)
        g1.addWidget(self.txt_prefix, 1, 1, 1, 2)
        layout.addWidget(grp_target)

        grp_mode = QGroupBox("Batch Export Mode & Layout")
        g2 = QVBoxLayout(grp_mode)
        self.radio_multipanel = QRadioButton("Multi-Panel Document (Stacked V, I, P, R subplots in a single publication figure)")
        self.radio_multipanel.setChecked(True)
        self.radio_separate = QRadioButton("Individual Trace Files (Separate image files for Voltage, Current, Power, Resistance)")
        g2.addWidget(self.radio_multipanel)
        g2.addWidget(self.radio_separate)
        layout.addWidget(grp_mode)

        grp_fmt = QGroupBox("Format & Quality")
        g3 = QGridLayout(grp_fmt)
        g3.addWidget(QLabel("File Format:"), 0, 0)
        self.combo_fmt = QComboBox()
        self.combo_fmt.addItems([
            "PDF Vector Document (*.pdf)",
            "PNG High-DPI Raster (*.png)",
            "Scalable Vector Graphic (*.svg)",
            "LaTeX TikZ / pgfplots (*.pgf)",
            "JPEG Image (*.jpg)"
        ])
        g3.addWidget(self.combo_fmt, 0, 1)

        g3.addWidget(QLabel("Quality / DPI:"), 1, 0)
        self.combo_dpi = QComboBox()
        self.combo_dpi.addItems(["150 DPI (Screen)", "300 DPI (Journal Print)", "600 DPI (Archival Ultra)", "1200 DPI (Micro-Graphic)"])
        self.combo_dpi.setCurrentIndex(1)
        g3.addWidget(self.combo_dpi, 1, 1)

        g3.addWidget(QLabel("Color Theme:"), 2, 0)
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["Publication Clean Light (White)", "Dark Mode (Slate)", "Match Active GUI Theme"])
        g3.addWidget(self.combo_theme, 2, 1)

        self.chk_meta = QCheckBox("Generate Companion .meta JSON File")
        self.chk_meta.setChecked(True)
        g3.addWidget(self.chk_meta, 3, 0, 1, 2)

        self.chk_watermark = QCheckBox("Include Provenance Footnote / Watermark")
        self.chk_watermark.setChecked(True)
        g3.addWidget(self.chk_watermark, 4, 0, 1, 2)

        self.chk_transparent = QCheckBox("Transparent Background (PDF / PNG)")
        self.chk_transparent.setChecked(False)
        g3.addWidget(self.chk_transparent, 5, 0, 1, 2)

        layout.addWidget(grp_fmt)

        bbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        layout.addWidget(bbox)

    def _browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select Export Directory", self.txt_dir.text())
        if d:
            self.txt_dir.setText(d)

    def get_options(self) -> dict:
        dpi_val = int(self.combo_dpi.currentText().split()[0])
        fmt_str = self.combo_fmt.currentText()
        if "pdf" in fmt_str.lower(): ext = ".pdf"
        elif "png" in fmt_str.lower(): ext = ".png"
        elif "svg" in fmt_str.lower(): ext = ".svg"
        elif "pgf" in fmt_str.lower(): ext = ".pgf"
        else: ext = ".jpg"

        return {
            "dir": self.txt_dir.text().strip(),
            "prefix": self.txt_prefix.text().strip(),
            "multipanel": self.radio_multipanel.isChecked(),
            "ext": ext,
            "dpi": dpi_val,
            "theme": self.combo_theme.currentText(),
            "generate_meta": self.chk_meta.isChecked(),
            "watermark": self.chk_watermark.isChecked(),
            "transparent": self.chk_transparent.isChecked(),
        }

# =============================================================================
# PUBLICATION PRESETS & TEMPLATES CONFIGURATION
# =============================================================================
TEMPLATE_DIR = Path.home() / ".config" / "labhp" / "plot_templates"
try:
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    TEMPLATE_DIR = Path.cwd() / "plot_templates"
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

PUBLICATION_PRESETS = {
    "Custom (User Defined)": None,
    "Nature (89mm, 7pt Arial, 1.0pt line, 600 DPI)": {
        "title_align": "Left",
        "font_size": 7,
        "font_family": "Arial, Helvetica, sans-serif",
        "line_width": 1.0,
        "plot_style": "Continuous: Solid Line (Default)",
        "marker_size": 4,
        "grid_style": "None",
        "legend_loc": "Auto (Lowest Density)",
        "export_theme": "Publication Clean Light (White)",
        "export_dpi": 600,
        "auto_limits_percentile": True,
        "transparent_pdf": True,
        "show_watermark": False,
        "export_companion_meta": True,
    },
    "IEEE Transactions (3.5in, 8pt Times, 1.5pt line, 300 DPI)": {
        "title_align": "Center",
        "font_size": 8,
        "font_family": "Times New Roman, serif",
        "line_width": 1.5,
        "plot_style": "Continuous: Solid Line (Default)",
        "marker_size": 5,
        "grid_style": "Both X & Y",
        "legend_loc": "Top-Right",
        "export_theme": "Publication Clean Light (White)",
        "export_dpi": 300,
        "auto_limits_percentile": True,
        "transparent_pdf": False,
        "show_watermark": False,
        "export_companion_meta": True,
    },
    "APS Physical Review (3.375in, 9pt, 1.0pt line, 600 DPI)": {
        "title_align": "Center",
        "font_size": 9,
        "font_family": "Times New Roman, serif",
        "line_width": 1.0,
        "plot_style": "Continuous: Solid Line (Default)",
        "marker_size": 4,
        "grid_style": "Both X & Y",
        "legend_loc": "Auto (Lowest Density)",
        "export_theme": "Publication Clean Light (White)",
        "export_dpi": 600,
        "auto_limits_percentile": True,
        "transparent_pdf": True,
        "show_watermark": False,
        "export_companion_meta": True,
    },
    "Industrial High-Density (Slate Dark, 2.0pt line, 150 DPI)": {
        "title_align": "Center",
        "font_size": 10,
        "font_family": "JetBrains Mono, monospace",
        "line_width": 2.0,
        "plot_style": "Continuous: Solid Line (Default)",
        "marker_size": 6,
        "grid_style": "Both X & Y",
        "legend_loc": "Top-Right",
        "export_theme": "Dark Mode (Slate)",
        "export_dpi": 150,
        "auto_limits_percentile": False,
        "transparent_pdf": False,
        "show_watermark": True,
        "watermark_text": "ETPS LAB-HP 41000 Telemetry",
        "export_companion_meta": True,
    },
}

class PlotPresentationDialog(QDialog):
    """
    Publication-grade customization dialog for waveform presentation and export:
    - Template System (Save/Load JSON I/O, Recent templates)
    - Publication Presets (Nature, IEEE, APS, Industrial, Custom)
    - Typography, Font Pairing, and Mathematical Sizing
    - Smart Layout: Auto-legend to lowest-density region, 5-95% percentile auto-axis limits
    - Drag-and-Drop Trace Priority & Legend Ordering
    - Metadata & LaTeX Support (Companion .meta JSON, Watermark, Transparent PDF)
    """

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chart Presentation & Publication Settings")
        self.setMinimumWidth(560)
        self.settings = dict(settings)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # 0. Preset & Template Management Bar
        grp_tmpl = QGroupBox("Publication Presets & Template System")
        g_tmpl = QGridLayout(grp_tmpl)
        g_tmpl.setSpacing(8)

        g_tmpl.addWidget(QLabel("Preset:"), 0, 0)
        self.combo_preset = QComboBox()
        self.combo_preset.addItems(list(PUBLICATION_PRESETS.keys()))
        curr_preset = self.settings.get("publication_preset", "Custom (User Defined)")
        if curr_preset in PUBLICATION_PRESETS:
            self.combo_preset.setCurrentText(curr_preset)
        self.combo_preset.currentIndexChanged.connect(self._on_preset_changed)
        g_tmpl.addWidget(self.combo_preset, 0, 1, 1, 3)

        # Recent Templates
        g_tmpl.addWidget(QLabel("Saved Template:"), 1, 0)
        self.combo_templates = QComboBox()
        self._refresh_template_list()
        self.combo_templates.currentIndexChanged.connect(self._on_template_selected)
        g_tmpl.addWidget(self.combo_templates, 1, 1)

        self.btn_save_tmpl = QPushButton("💾 Save Template...")
        self.btn_save_tmpl.setToolTip("Save all active presentation settings to a reusable JSON template")
        self.btn_save_tmpl.clicked.connect(self._save_template_dialog)
        g_tmpl.addWidget(self.btn_save_tmpl, 1, 2)

        self.btn_load_tmpl = QPushButton("📂 Load File...")
        self.btn_load_tmpl.setToolTip("Browse and load a custom JSON settings template")
        self.btn_load_tmpl.clicked.connect(self._load_template_file_dialog)
        g_tmpl.addWidget(self.btn_load_tmpl, 1, 3)

        layout.addWidget(grp_tmpl)

        # 1. Title & Typography Group
        grp_title = QGroupBox("Plot Title, Axes & Typography")
        g1 = QGridLayout(grp_title)
        g1.addWidget(QLabel("Title Text:"), 0, 0)
        self.txt_title = QLineEdit(self.settings.get("title", "LAB-HP 41000 — Session Waveform Telemetry"))
        g1.addWidget(self.txt_title, 0, 1)

        self.chk_show_title = QCheckBox("Show Title on Canvas & Export")
        self.chk_show_title.setChecked(self.settings.get("show_title", True))
        g1.addWidget(self.chk_show_title, 1, 0, 1, 2)

        g1.addWidget(QLabel("Title Alignment:"), 2, 0)
        self.combo_title_pos = QComboBox()
        self.combo_title_pos.addItems(["Center", "Left", "Right"])
        self.combo_title_pos.setCurrentText(self.settings.get("title_align", "Center"))
        g1.addWidget(self.combo_title_pos, 2, 1)

        g1.addWidget(QLabel("Font Family:"), 3, 0)
        self.combo_font = QComboBox()
        self.combo_font.addItems([
            "Default (Sans-Serif)",
            "Arial, Helvetica, sans-serif",
            "Times New Roman, serif",
            "Computer Modern, serif",
            "JetBrains Mono, monospace"
        ])
        self.combo_font.setCurrentText(self.settings.get("font_family", "Default (Sans-Serif)"))
        g1.addWidget(self.combo_font, 3, 1)

        g1.addWidget(QLabel("Font Size:"), 4, 0)
        self.spin_font_size = QSpinBox()
        self.spin_font_size.setRange(6, 18)
        self.spin_font_size.setValue(int(self.settings.get("font_size", 10)))
        self.spin_font_size.setSuffix(" pt")
        g1.addWidget(self.spin_font_size, 4, 1)

        g1.addWidget(QLabel("X-Axis Label:"), 5, 0)
        self.txt_xlabel = QLineEdit(self.settings.get("x_label", "Elapsed Time"))
        g1.addWidget(self.txt_xlabel, 5, 1)

        g1.addWidget(QLabel("X-Axis Unit:"), 6, 0)
        self.txt_xunit = QLineEdit(self.settings.get("x_unit", "s"))
        g1.addWidget(self.txt_xunit, 6, 1)

        g1.addWidget(QLabel("Y-Axis Label:"), 7, 0)
        self.txt_ylabel = QLineEdit(self.settings.get("y_label", "Magnitude"))
        g1.addWidget(self.txt_ylabel, 7, 1)

        g1.addWidget(QLabel("Y-Axis Unit:"), 8, 0)
        self.txt_yunit = QLineEdit(self.settings.get("y_unit", ""))
        g1.addWidget(self.txt_yunit, 8, 1)

        self.chk_auto_limits = QCheckBox("Smart Outlier Suppression: Auto-Axis Limits (5-95% Percentile)")
        self.chk_auto_limits.setToolTip("Suppresses transient inrush spikes from flattening the steady-state waveform")
        self.chk_auto_limits.setChecked(self.settings.get("auto_limits_percentile", False))
        g1.addWidget(self.chk_auto_limits, 9, 0, 1, 2)

        layout.addWidget(grp_title)

        # 2. Legend, Trace Styling & Drag-Drop Order Group
        grp_legend = QGroupBox("Legend Positioning, Trace Styling & Layer Order")
        g3 = QGridLayout(grp_legend)
        self.chk_show_legend = QCheckBox("Display Legend")
        self.chk_show_legend.setChecked(self.settings.get("show_legend", True))
        g3.addWidget(self.chk_show_legend, 0, 0, 1, 2)

        g3.addWidget(QLabel("Legend Position:"), 1, 0)
        self.combo_legend_loc = QComboBox()
        self.combo_legend_loc.addItems([
            "Auto (Lowest Density)", "Top-Right", "Top-Left", "Bottom-Right", "Bottom-Left",
            "Top-Center", "Bottom-Center", "Hidden"
        ])
        self.combo_legend_loc.setCurrentText(self.settings.get("legend_loc", "Top-Right"))
        self.combo_legend_loc.setToolTip("Auto (Lowest Density) places the legend away from active waveform points")
        g3.addWidget(self.combo_legend_loc, 1, 1)

        g3.addWidget(QLabel("Plot Style / Trace:"), 2, 0)
        self.combo_plot_style = QComboBox()
        self.combo_plot_style.addItems(PLOT_STYLE_OPTIONS)
        self.combo_plot_style.setCurrentText(self.settings.get("plot_style", "Continuous: Solid Line (Default)"))
        g3.addWidget(self.combo_plot_style, 2, 1)

        g3.addWidget(QLabel("Marker Size:"), 3, 0)
        self.spin_marker_size = QSpinBox()
        self.spin_marker_size.setRange(2, 24)
        self.spin_marker_size.setValue(int(self.settings.get("marker_size", 6)))
        self.spin_marker_size.setSuffix(" px")
        g3.addWidget(self.spin_marker_size, 3, 1)

        g3.addWidget(QLabel("Trace Line Width:"), 4, 0)
        self.combo_line_width = QComboBox()
        self.combo_line_width.addItems(["0.75 px (Hairline)", "1.0 px (Fine)", "1.5 px (Normal)", "2.0 px (Standard)", "2.5 px (Thick)", "3.0 px (Bold)"])
        lw_str = f"{float(self.settings.get('line_width', 2.0)):.2f}".rstrip('0').rstrip('.')
        for idx in range(self.combo_line_width.count()):
            if lw_str in self.combo_line_width.itemText(idx):
                self.combo_line_width.setCurrentIndex(idx)
                break
        g3.addWidget(self.combo_line_width, 4, 1)

        g3.addWidget(QLabel("Grid Visibility:"), 5, 0)
        self.combo_grid = QComboBox()
        self.combo_grid.addItems(["Both X & Y", "X Only", "Y Only", "None"])
        self.combo_grid.setCurrentText(self.settings.get("grid_style", "Both X & Y"))
        g3.addWidget(self.combo_grid, 5, 1)

        # Drag-and-drop Trace Ordering
        g3.addWidget(QLabel("Trace & Legend Order (Drag to Reorder):"), 6, 0, 1, 2)
        self.list_trace_order = QListWidget()
        self.list_trace_order.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list_trace_order.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.list_trace_order.setMaximumHeight(88)

        default_order = ["Voltage (V)", "Current (A)", "Power (W)", "Resistance (Ω)"]
        saved_order = self.settings.get("trace_order", default_order)
        for item_text in saved_order:
            self.list_trace_order.addItem(item_text)
        for item_text in default_order:
            if item_text not in saved_order:
                self.list_trace_order.addItem(item_text)
        g3.addWidget(self.list_trace_order, 7, 0, 1, 2)

        layout.addWidget(grp_legend)

        # 3. Export Defaults, Metadata & LaTeX Group
        grp_export = QGroupBox("Export Defaults, Metadata & LaTeX Features")
        g4 = QGridLayout(grp_export)
        g4.addWidget(QLabel("Export Color Theme:"), 0, 0)
        self.combo_export_theme = QComboBox()
        self.combo_export_theme.addItems(["Match Active GUI Theme", "Dark Mode (Slate)", "Publication Clean Light (White)"])
        self.combo_export_theme.setCurrentText(self.settings.get("export_theme", "Match Active GUI Theme"))
        g4.addWidget(self.combo_export_theme, 0, 1)

        g4.addWidget(QLabel("Export Quality / DPI:"), 1, 0)
        self.combo_export_dpi = QComboBox()
        self.combo_export_dpi.addItems(["150 DPI (Standard Screen)", "300 DPI (High-Resolution Print)", "600 DPI (Ultra-Sharp Archival)", "1200 DPI (Micro-Graphic)"])
        dpi_str = str(self.settings.get("export_dpi", 300))
        for idx in range(self.combo_export_dpi.count()):
            if dpi_str in self.combo_export_dpi.itemText(idx):
                self.combo_export_dpi.setCurrentIndex(idx)
                break
        g4.addWidget(self.combo_export_dpi, 1, 1)

        self.chk_transparent = QCheckBox("Transparent Background (PDF / PNG / LaTeX)")
        self.chk_transparent.setChecked(self.settings.get("transparent_pdf", False))
        g4.addWidget(self.chk_transparent, 2, 0, 1, 2)

        self.chk_watermark = QCheckBox("Add Provenance Footnote / Watermark")
        self.chk_watermark.setChecked(self.settings.get("show_watermark", False))
        g4.addWidget(self.chk_watermark, 3, 0)

        self.txt_watermark = QLineEdit(self.settings.get("watermark_text", "ETPS LAB-HP 41000 Telemetry"))
        g4.addWidget(self.txt_watermark, 3, 1)

        self.chk_companion_meta = QCheckBox("Generate Companion .meta JSON File on Export")
        self.chk_companion_meta.setToolTip("Exports a companion metadata file with descriptive statistics, peaks, and settings")
        self.chk_companion_meta.setChecked(self.settings.get("export_companion_meta", True))
        g4.addWidget(self.chk_companion_meta, 4, 0, 1, 2)

        layout.addWidget(grp_export)

        # Dialog Buttons
        btn_row = QHBoxLayout()
        btn_reset = QPushButton("Reset to Defaults")
        btn_reset.clicked.connect(self._reset_defaults)
        btn_row.addWidget(btn_reset)
        btn_row.addStretch()

        bbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        btn_row.addWidget(bbox)
        layout.addLayout(btn_row)

    def _refresh_template_list(self):
        self.combo_templates.clear()
        self.combo_templates.addItem("-- Select Template --")
        try:
            for p in sorted(TEMPLATE_DIR.glob("*.json")):
                self.combo_templates.addItem(p.stem, userData=str(p))
        except Exception:
            pass

    def _on_template_selected(self, index: int):
        if index <= 0:
            return
        filepath = self.combo_templates.currentData()
        if filepath and os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.apply_dict_to_ui(data)
            except Exception as e:
                QMessageBox.warning(self, "Template Error", f"Failed to load template:\n{e}")

    def _on_preset_changed(self, index: int):
        preset_name = self.combo_preset.currentText()
        preset_cfg = PUBLICATION_PRESETS.get(preset_name)
        if preset_cfg:
            self.apply_dict_to_ui(preset_cfg)

    def _save_template_dialog(self):
        default_p = str(TEMPLATE_DIR / "custom_template.json")
        path, _ = QFileDialog.getSaveFileName(self, "Save Presentation Template", default_p, "JSON Template (*.json)")
        if path:
            try:
                settings_dict = self.get_settings()
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(settings_dict, f, indent=2)
                self._refresh_template_list()
                QMessageBox.information(self, "Template Saved", f"Presentation template saved to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Save Failed", f"Failed to save template:\n{e}")

    def _load_template_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Presentation Template", str(TEMPLATE_DIR), "JSON Template (*.json)")
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.apply_dict_to_ui(data)
                QMessageBox.information(self, "Template Loaded", f"Template '{Path(path).stem}' loaded successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Load Failed", f"Failed to load template:\n{e}")

    def apply_dict_to_ui(self, d: dict):
        if "title" in d: self.txt_title.setText(str(d["title"]))
        if "show_title" in d: self.chk_show_title.setChecked(bool(d["show_title"]))
        if "title_align" in d: self.combo_title_pos.setCurrentText(str(d["title_align"]))
        if "font_size" in d: self.spin_font_size.setValue(int(d["font_size"]))
        if "font_family" in d: self.combo_font.setCurrentText(str(d["font_family"]))
        if "x_label" in d: self.txt_xlabel.setText(str(d["x_label"]))
        if "x_unit" in d: self.txt_xunit.setText(str(d["x_unit"]))
        if "y_label" in d: self.txt_ylabel.setText(str(d["y_label"]))
        if "y_unit" in d: self.txt_yunit.setText(str(d["y_unit"]))
        if "show_legend" in d: self.chk_show_legend.setChecked(bool(d["show_legend"]))
        if "legend_loc" in d: self.combo_legend_loc.setCurrentText(str(d["legend_loc"]))
        if "plot_style" in d: self.combo_plot_style.setCurrentText(str(d["plot_style"]))
        if "marker_size" in d: self.spin_marker_size.setValue(int(d["marker_size"]))
        if "line_width" in d:
            lw_s = f"{float(d['line_width']):.2f}".rstrip('0').rstrip('.')
            for i in range(self.combo_line_width.count()):
                if lw_s in self.combo_line_width.itemText(i):
                    self.combo_line_width.setCurrentIndex(i)
                    break
        if "grid_style" in d: self.combo_grid.setCurrentText(str(d["grid_style"]))
        if "export_theme" in d: self.combo_export_theme.setCurrentText(str(d["export_theme"]))
        if "export_dpi" in d:
            dpi_s = str(d["export_dpi"])
            for i in range(self.combo_export_dpi.count()):
                if dpi_s in self.combo_export_dpi.itemText(i):
                    self.combo_export_dpi.setCurrentIndex(i)
                    break
        if "auto_limits_percentile" in d: self.chk_auto_limits.setChecked(bool(d["auto_limits_percentile"]))
        if "transparent_pdf" in d: self.chk_transparent.setChecked(bool(d["transparent_pdf"]))
        if "show_watermark" in d: self.chk_watermark.setChecked(bool(d["show_watermark"]))
        if "watermark_text" in d: self.txt_watermark.setText(str(d["watermark_text"]))
        if "export_companion_meta" in d: self.chk_companion_meta.setChecked(bool(d["export_companion_meta"]))

    def _reset_defaults(self):
        self.combo_preset.setCurrentText("Custom (User Defined)")
        self.txt_title.setText("LAB-HP 41000 — Session Waveform Telemetry")
        self.chk_show_title.setChecked(True)
        self.combo_title_pos.setCurrentText("Center")
        self.combo_font.setCurrentIndex(0)
        self.spin_font_size.setValue(10)
        self.txt_xlabel.setText("Elapsed Time")
        self.txt_xunit.setText("s")
        self.txt_ylabel.setText("Magnitude")
        self.txt_yunit.setText("")
        self.chk_auto_limits.setChecked(False)
        self.chk_show_legend.setChecked(True)
        self.combo_legend_loc.setCurrentText("Top-Right")
        self.combo_plot_style.setCurrentText("Continuous: Solid Line (Default)")
        self.spin_marker_size.setValue(6)
        self.combo_line_width.setCurrentIndex(3)  # 2.0 px
        self.combo_grid.setCurrentText("Both X & Y")
        self.combo_export_theme.setCurrentText("Match Active GUI Theme")
        self.combo_export_dpi.setCurrentIndex(1)  # 300 DPI
        self.chk_transparent.setChecked(False)
        self.chk_watermark.setChecked(False)
        self.txt_watermark.setText("ETPS LAB-HP 41000 Telemetry")
        self.chk_companion_meta.setChecked(True)

    def get_settings(self) -> dict:
        lw_txt = self.combo_line_width.currentText()
        lw_val = 2.0
        try:
            lw_val = float(lw_txt.split()[0])
        except Exception:
            lw_val = 2.0

        dpi_txt = self.combo_export_dpi.currentText()
        dpi_val = 300
        try:
            dpi_val = int(dpi_txt.split()[0])
        except Exception:
            dpi_val = 300

        loc = self.combo_legend_loc.currentText()
        if not self.chk_show_legend.isChecked():
            loc = "Hidden"

        # Trace order
        trace_order = [self.list_trace_order.item(i).text() for i in range(self.list_trace_order.count())]

        return {
            "publication_preset": self.combo_preset.currentText(),
            "title": self.txt_title.text().strip(),
            "show_title": self.chk_show_title.isChecked(),
            "title_align": self.combo_title_pos.currentText(),
            "font_family": self.combo_font.currentText(),
            "font_size": self.spin_font_size.value(),
            "x_label": self.txt_xlabel.text().strip(),
            "x_unit": self.txt_xunit.text().strip(),
            "y_label": self.txt_ylabel.text().strip(),
            "y_unit": self.txt_yunit.text().strip(),
            "auto_limits_percentile": self.chk_auto_limits.isChecked(),
            "show_legend": self.chk_show_legend.isChecked(),
            "legend_loc": loc,
            "plot_style": self.combo_plot_style.currentText(),
            "marker_size": self.spin_marker_size.value(),
            "line_width": lw_val,
            "grid_style": self.combo_grid.currentText(),
            "trace_order": trace_order,
            "export_theme": self.combo_export_theme.currentText(),
            "export_dpi": dpi_val,
            "transparent_pdf": self.chk_transparent.isChecked(),
            "show_watermark": self.chk_watermark.isChecked(),
            "watermark_text": self.txt_watermark.text().strip(),
            "export_companion_meta": self.chk_companion_meta.isChecked(),
        }


# =============================================================================
# CONTROLLER COMMUNICATION CORE
# =============================================================================
class LABHPController:
    """ASCII Protocol Driver for ETPS LAB-HP 41000 over TCP/IP."""

    MAX_VOLTAGE = 1000.0
    MAX_CURRENT = 7.0
    MAX_POWER   = 4000.0

    def __init__(self):
        self.sock: socket.socket | None = None
        self._lock = threading.Lock()
        self.connected = False
        self.ip = ""
        self.port = 10001
        self.timeout = 4.0
        self.last_roundtrip_ms = 0.0

    def connect(self, ip: str, port: int = 10001) -> bool:
        if self.connected:
            self.disconnect()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect((ip, port))
        self.ip = ip
        self.port = port
        self.connected = True
        time.sleep(0.15)

        # Flush any welcome or boot banners
        try:
            self.sock.settimeout(0.3)
            self.sock.recv(4096)
        except (socket.timeout, OSError):
            pass
        self.sock.settimeout(self.timeout)
        return True

    def disconnect(self):
        self.connected = False
        with self._lock:
            sock = self.sock
            self.sock = None
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass

    def _send(self, cmd: str, expect_response: bool = False, retries: int = 1) -> str:
        with self._lock:
            if not self.sock or not self.connected:
                raise ConnectionError("Device not connected")

            data = (cmd.strip() + "\r\n").encode("ascii")
            t_start = time.perf_counter()

            for attempt in range(retries + 1):
                try:
                    self.sock.sendall(data)
                    if expect_response:
                        resp = b""
                        deadline = time.time() + self.timeout
                        while time.time() < deadline:
                            chunk = self.sock.recv(4096)
                            if not chunk:
                                break
                            resp += chunk
                            if b"\n" in resp or b"\r" in resp:
                                break
                        decoded = resp.decode("ascii", errors="ignore").strip()
                        self.last_roundtrip_ms = (time.perf_counter() - t_start) * 1000.0
                        return decoded
                    self.last_roundtrip_ms = (time.perf_counter() - t_start) * 1000.0
                    return ""
                except (socket.timeout, OSError) as e:
                    if attempt < retries:
                        time.sleep(0.08)
                        continue
                    self.connected = False
                    raise ConnectionError(f"I/O error ({cmd}): {e}")
            return ""

    @staticmethod
    def _parse_value(resp: str) -> float:
        if not resp:
            return 0.0
        val_part = resp.split(",", 1)[1] if "," in resp else resp
        match = re.search(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", val_part)
        return float(match.group()) if match else 0.0

    # Device Command Interface
    def get_idn(self) -> str: return self._send("ID", expect_response=True, retries=2)
    def set_remote(self): self._send("GTR", retries=2)
    def set_local(self): self._send("GTL", retries=2)
    def reset(self): self._send("*RST")
    def save_setup(self): self._send("SS")

    # Setpoints
    def set_voltage(self, v: float): self._send(f"UA,{v:.2f}")
    def get_voltage_setpoint(self) -> float: return self._parse_value(self._send("UA", expect_response=True))
    def set_current(self, i: float): self._send(f"IA,{i:.4f}")
    def get_current_setpoint(self) -> float: return self._parse_value(self._send("IA", expect_response=True))
    def set_power(self, p: float): self._send(f"PA,{p:.2f}")
    def get_power_setpoint(self) -> float: return self._parse_value(self._send("PA", expect_response=True))
    def set_ovp(self, v: float): self._send(f"OVP,{v:.1f}")
    def get_ovp(self) -> float: return self._parse_value(self._send("OVP", expect_response=True))

    # Output Control
    def output_on(self): self._send("SB,R", retries=2)
    def output_off(self): self._send("SB,S", retries=2)
    def get_output_state(self) -> bool:
        resp = self._send("SB", expect_response=True)
        return ("R" in resp.split(",", 1)[1].upper()) if "," in resp else False

    # Measurements & Status
    def measure_voltage(self) -> float: return self._parse_value(self._send("MU", expect_response=True))
    def measure_current(self) -> float: return self._parse_value(self._send("MI", expect_response=True))
    def get_status_raw(self) -> str: return self._send("STATUS", expect_response=True)

    def get_mode(self) -> str:
        resp = self._send("MODE", expect_response=True)
        return resp.split(",")[1].strip() if "," in resp else resp

    def set_mode(self, mode: str): self._send(f"MODE,{mode}")

    def measure_fast_telemetry(self) -> dict:
        """Pipelined measurement for high polling efficiency."""
        u = self.measure_voltage()
        i = self.measure_current()
        p = u * i
        r = (u / i) if i > 0.0005 else float('inf')
        return {"voltage": u, "current": i, "power": p, "resistance": r}

    @staticmethod
    def decode_status(raw: str) -> dict:
        """Decode 16-bit status word."""
        bits = raw.replace("STATUS,", "").strip()
        if not bits:
            return {}
        bits = bits.zfill(16)
        bits_rev = bits[::-1]
        bit_list = [int(b) for b in bits_rev]
        return {
            "OVP shutdown": bool(bit_list[0]),
            "Standby": bool(bit_list[1]),
            "Remote mode": bool(bit_list[4]),
            "Local mode": bool(bit_list[5]),
            "Local lockout": bool(bit_list[6]),
            "Current limit": bool(bit_list[7]),
            "Power limit": bool(bit_list[8]),
            "Raw": raw.strip()
        }


# =============================================================================
# ASYNCHRONOUS TELEMETRY & POLLING WORKER
# =============================================================================
class TelemetryWorker(QThread):
    telemetry_received = pyqtSignal(dict)
    output_state_received = pyqtSignal(bool)
    status_received = pyqtSignal(dict)
    connection_lost = pyqtSignal(str)

    def __init__(self, controller: LABHPController, interval_s: float = 0.2):
        super().__init__()
        self.controller = controller
        self.interval_s = max(0.05, interval_s)
        self._stop_event = threading.Event()
        self._force_trigger = threading.Event()

    def set_interval(self, interval_s: float):
        self.interval_s = max(0.05, interval_s)

    def trigger_now(self):
        self._force_trigger.set()

    def run(self):
        while not self._stop_event.is_set():
            if not self.controller.connected:
                self.connection_lost.emit("Socket disconnected")
                break

            try:
                meas = self.controller.measure_fast_telemetry()
                self.telemetry_received.emit(meas)

                out_state = self.controller.get_output_state()
                self.output_state_received.emit(out_state)

                raw_status = self.controller.get_status_raw()
                status_dict = self.controller.decode_status(raw_status)
                self.status_received.emit(status_dict)

            except Exception as e:
                if not self._stop_event.is_set():
                    self.connection_lost.emit(str(e))
                    break

            # Wait with event wakeups
            self._stop_event.wait(self.interval_s)
            self._force_trigger.clear()

    def stop(self):
        self._stop_event.set()
        self.wait(1500)


# =============================================================================
# NETWORK SCANNER THREAD
# =============================================================================
class FastNetworkScanner(QThread):
    progress = pyqtSignal(int, int)
    device_found = pyqtSignal(str, str)
    scan_finished = pyqtSignal(list)

    def __init__(self, port: int = 10001, timeout: float = 0.35):
        super().__init__()
        self.port = port
        self.timeout = timeout
        self._stop_flag = threading.Event()

    def stop(self):
        self._stop_flag.set()

    def run(self):
        targets = self._discover_candidate_ips()
        total = len(targets)
        if total == 0:
            self.scan_finished.emit([])
            return

        found = []
        done = 0
        with ThreadPoolExecutor(max_workers=40) as executor:
            future_to_ip = {executor.submit(self._probe_ip, ip): ip for ip in targets}
            for future in as_completed(future_to_ip):
                if self._stop_flag.is_set():
                    break
                ip = future_to_ip[future]
                try:
                    idn = future.result()
                    if idn:
                        found.append((ip, idn))
                        self.device_found.emit(ip, idn)
                except Exception:
                    pass
                done += 1
                self.progress.emit(done, total)

        self.scan_finished.emit(found)

    def _probe_ip(self, ip: str) -> str | None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(self.timeout)
                s.connect((ip, self.port))
                s.settimeout(0.8)
                s.sendall(b"ID\r\n")
                resp = s.recv(1024).decode("ascii", errors="ignore").strip()
                return resp if resp else "ETPS LAB-HP Source"
        except Exception:
            return None

    def _discover_candidate_ips(self) -> list[str]:
        ips = []
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            parts = local_ip.split(".")
            if len(parts) == 4:
                subnet = f"{parts[0]}.{parts[1]}.{parts[2]}"
                ips.extend([f"{subnet}.{i}" for i in range(1, 255)])
        except Exception:
            pass
        if not ips:
            ips = ["127.0.0.1", "192.168.1.100", "192.168.0.100", "10.0.0.100"]
        return ips


# =============================================================================
# DATA LOGGER THREAD
# =============================================================================
class HighSpeedLogger(QThread):
    row_logged = pyqtSignal(int, str)
    error_occurred = pyqtSignal(str)

    def __init__(self, controller: LABHPController, file_path: str, interval_s: float,
                 channels: dict):
        super().__init__()
        self.controller = controller
        self.file_path = file_path
        self.interval_s = max(0.05, interval_s)
        self.channels = channels  # {'v': bool, 'i': bool, 'p': bool, 'r': bool, 'out': bool}
        self._stop_event = threading.Event()
        self._paused = threading.Event()
        self._paused.set()  # not paused
        self.record_count = 0

    def pause(self): self._paused.clear()
    def resume(self): self._paused.set()
    def stop(self):
        self._stop_event.set()
        self.wait(2000)

    def run(self):
        try:
            with open(self.file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                header = ["ISO_Timestamp", "Epoch_Seconds", "Elapsed_Seconds"]
                if self.channels.get("v"): header.extend(["Voltage_Set_V", "Voltage_Meas_V"])
                if self.channels.get("i"): header.extend(["Current_Set_A", "Current_Meas_A"])
                if self.channels.get("p"): header.extend(["Power_Set_W", "Power_Meas_W"])
                if self.channels.get("r"): header.append("Resistance_Ohm")
                if self.channels.get("out"): header.append("Output_State")
                writer.writerow(header)
                f.flush()

                t_start = time.time()
                while not self._stop_event.is_set():
                    self._paused.wait()
                    if self._stop_event.is_set():
                        break

                    now = time.time()
                    dt_str = datetime.datetime.now().isoformat()
                    elapsed = now - t_start

                    meas = self.controller.measure_fast_telemetry()
                    v_set = self.controller.get_voltage_setpoint()
                    i_set = self.controller.get_current_setpoint()
                    p_set = self.controller.get_power_setpoint()
                    out_on = self.controller.get_output_state()

                    row = [dt_str, f"{now:.3f}", f"{elapsed:.3f}"]
                    if self.channels.get("v"): row.extend([f"{v_set:.3f}", f"{meas['voltage']:.3f}"])
                    if self.channels.get("i"): row.extend([f"{i_set:.4f}", f"{meas['current']:.4f}"])
                    if self.channels.get("p"): row.extend([f"{p_set:.2f}", f"{meas['power']:.2f}"])
                    if self.channels.get("r"):
                        r_str = f"{meas['resistance']:.2f}" if not math.isinf(meas['resistance']) else "INF"
                        row.append(r_str)
                    if self.channels.get("out"): row.append("1" if out_on else "0")

                    writer.writerow(row)
                    f.flush()
                    self.record_count += 1
                    preview = f"#{self.record_count:05d} | {elapsed:7.2f}s | V:{meas['voltage']:7.2f}V | I:{meas['current']:6.4f}A | P:{meas['power']:7.2f}W"
                    self.row_logged.emit(self.record_count, preview)

                    self._stop_event.wait(self.interval_s)
        except Exception as e:
            self.error_occurred.emit(str(e))


# =============================================================================
# MAIN WINDOW
# =============================================================================
class LABHPControllerV5(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ETPS LAB-HP 41000 — Professional DC Source Suite v5")
        self.setMinimumSize(1260, 880)

        self.controller = LABHPController()
        self.telemetry_worker: TelemetryWorker | None = None
        self.logger_thread: HighSpeedLogger | None = None
        self.scanner_thread: FastNetworkScanner | None = None

        # Application state
        self.is_local_mode = False  # Track whether device is in Local or Remote mode
        self.emergency_latched = False
        self.log_start_time = 0.0
        self.settings = QSettings("ETPS", "LABHP_v5")

        # Global Theme & Presentation State
        self.current_theme = "dark"
        self.plot_settings = {
            "title": "LAB-HP 41000 — Session Waveform Telemetry",
            "show_title": True,
            "title_align": "Center",
            "x_label": "Elapsed Time",
            "x_unit": "s",
            "y_label": "Magnitude",
            "y_unit": "",
            "show_legend": True,
            "legend_loc": "Top-Right",
            "plot_style": "Continuous: Solid Line (Default)",
            "marker_size": 6,
            "line_width": 2.0,
            "grid_style": "Both X & Y",
            "export_theme": "Match Active GUI Theme",
            "export_dpi": 300,
        }

        # Telemetry History Ring Buffers (for 60 FPS plotting)
        self.max_history_points = 2000
        self.history_t = []
        self.history_v = []
        self.history_i = []
        self.history_p = []
        self.history_t0 = None

        # Cumulative Energy Wh
        self.energy_wh = 0.0
        self.last_energy_calc_t = None

        # Historical / Full-Session Log Data (for analytics & multi-format export)
        self.hist_t = []
        self.hist_v = []
        self.hist_i = []
        self.hist_p = []
        self.hist_r = []
        self.current_loaded_csv = ""

        self._build_ui()
        self.setStyleSheet(MODERN_DARK_STYLESHEET)
        self._load_saved_settings()

        # Keyboard shortcuts
        self.shortcut_estop = QShortcut(QKeySequence("Ctrl+E"), self)
        self.shortcut_estop.activated.connect(self._toggle_emergency_stop)

        self.shortcut_output = QShortcut(QKeySequence("Ctrl+O"), self)
        self.shortcut_output.activated.connect(self._toggle_output_shortcut)

        # Watchdog heartbeat timer
        self.watchdog_timer = QTimer(self)
        self.watchdog_timer.timeout.connect(self._watchdog_heartbeat)
        self.watchdog_timer.start(5000)

    # -------------------------------------------------------------------------
    # UI CONSTRUCTION
    # -------------------------------------------------------------------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(14, 12, 14, 12)
        root_layout.setSpacing(12)

        # 1. TOP HEADER & CONNECTION BAR
        root_layout.addWidget(self._create_header_bar())

        # 2. TABBED WORKSPACE
        tabs = QTabWidget()
        root_layout.addWidget(tabs, 1)

        tab_main = QWidget()
        tab_logger = QWidget()
        tab_soa = QWidget()
        tab_terminal = QWidget()

        tabs.addTab(tab_main, "  Benchtop Monitor & Control  ")
        tabs.addTab(tab_logger, "  High-Speed Data Logger  ")
        tabs.addTab(tab_soa, "  Safe Operating Area (SOA)  ")
        tabs.addTab(tab_terminal, "  ASCII Command Terminal  ")

        self._build_main_tab(tab_main)
        self._build_logger_tab(tab_logger)
        self._build_soa_tab(tab_soa)
        self._build_terminal_tab(tab_terminal)

        # 3. STATUS BAR
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Enter Instrument IP and click Connect.")

    def _create_header_bar(self) -> QWidget:
        header_card = QFrame()
        self.header_card = header_card
        self.header_card.setObjectName("header_card")
        self.header_card.setStyleSheet("""
            QFrame#header_card {
                background-color: #16181d;
                border: 1px solid #272a31;
                border-radius: 8px;
            }
        """)
        h_layout = QHBoxLayout(header_card)
        h_layout.setContentsMargins(14, 10, 14, 10)
        h_layout.setSpacing(12)

        # Title & Device Badge
        title_box = QVBoxLayout()
        self.lbl_header_title = QLabel("LAB-HP 41000")
        self.lbl_header_title.setStyleSheet("font-size: 14pt; font-weight: 800; color: #38bdf8; letter-spacing: 0.5px;")
        self.lbl_header_sub = QLabel("4 kW  •  1000 V  •  7 A  •  LAN ASCII Controller")
        self.lbl_header_sub.setStyleSheet("font-size: 8.5pt; color: #94a3b8;")
        title_box.addWidget(self.lbl_header_title)
        title_box.addWidget(self.lbl_header_sub)
        h_layout.addLayout(title_box)

        h_layout.addSpacing(15)

        # Connection Controls
        h_layout.addWidget(QLabel("IP:"))
        self.combo_ip = QComboBox()
        self.combo_ip.setEditable(True)
        self.combo_ip.setMinimumWidth(150)
        self.combo_ip.addItem("192.168.1.100")
        h_layout.addWidget(self.combo_ip)

        self.btn_scan = QToolButton()
        self.btn_scan.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.btn_scan.setToolTip("Auto-Scan Local Subnet for LAB-HP Devices")
        self.btn_scan.clicked.connect(self._start_network_scan)
        h_layout.addWidget(self.btn_scan)

        h_layout.addWidget(QLabel("Port:"))
        self.spin_port = QSpinBox()
        self.spin_port.setRange(1, 65535)
        self.spin_port.setValue(10001)
        self.spin_port.setFixedWidth(75)
        h_layout.addWidget(self.spin_port)

        self.btn_connect = QPushButton("CONNECT")
        self.btn_connect.setObjectName("primary")
        self.btn_connect.clicked.connect(self._toggle_connection)
        h_layout.addWidget(self.btn_connect)

        self.lbl_conn_status = QLabel("● Disconnected")
        self.lbl_conn_status.setStyleSheet("color: #ef4444; font-weight: 700; font-size: 9.5pt;")
        h_layout.addWidget(self.lbl_conn_status)

        h_layout.addStretch()

        # =====================================================================
        # KEY FEATURE: LOCAL / REMOTE MODE SWITCH BUTTON
        # =====================================================================
        mode_box = QVBoxLayout()
        mode_box.setSpacing(2)
        lbl_mode_caption = QLabel("BUS CONTROL MODE")
        lbl_mode_caption.setStyleSheet("font-size: 7.5pt; font-weight: 700; color: #64748b; letter-spacing: 0.5px;")
        lbl_mode_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mode_box.addWidget(lbl_mode_caption)

        self.btn_mode_toggle = QPushButton("⚡ REMOTE MODE")
        self.btn_mode_toggle.setObjectName("mode_remote")
        self.btn_mode_toggle.setToolTip(
            "Toggle between REMOTE (computer control) and LOCAL (front-panel physical control).\n"
            "In Local Mode, data logging, graphing, and readouts remain active while setpoints are locked."
        )
        self.btn_mode_toggle.clicked.connect(self._toggle_local_remote_mode)
        self.btn_mode_toggle.setEnabled(False)
        mode_box.addWidget(self.btn_mode_toggle)
        h_layout.addLayout(mode_box)

        h_layout.addSpacing(10)

        # =====================================================================
        # GLOBAL THEME TOGGLE (DARK / LIGHT MODE)
        # =====================================================================
        theme_box = QVBoxLayout()
        theme_box.setSpacing(2)
        lbl_theme_caption = QLabel("DISPLAY THEME")
        lbl_theme_caption.setStyleSheet("font-size: 7.5pt; font-weight: 700; color: #64748b; letter-spacing: 0.5px;")
        lbl_theme_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        theme_box.addWidget(lbl_theme_caption)

        self.btn_theme_toggle = QPushButton("☀️ Light Mode")
        self.btn_theme_toggle.setToolTip("Switch application theme between Modern Dark and Clean Laboratory Light")
        self.btn_theme_toggle.clicked.connect(self._toggle_theme)
        theme_box.addWidget(self.btn_theme_toggle)
        h_layout.addLayout(theme_box)

        h_layout.addSpacing(15)

        # Industrial Latching Emergency Stop
        self.btn_estop = QPushButton("EMERGENCY\nSTOP")
        self.btn_estop.setObjectName("emergency")
        self.btn_estop.setFixedSize(84, 84)
        self.btn_estop.setEnabled(False)
        self.btn_estop.clicked.connect(self._toggle_emergency_stop)
        self.btn_estop.setToolTip("Immediate Hardware Shutdown (Ctrl+E)")
        h_layout.addWidget(self.btn_estop)

        return header_card

    # -------------------------------------------------------------------------
    # TAB 1: BENCHTOP MONITOR & CONTROL
    # -------------------------------------------------------------------------
    def _build_main_tab(self, parent: QWidget):
        main_layout = QHBoxLayout(parent)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(14)

        # Left Column: Setpoints & Output Controls
        left_col = QVBoxLayout()
        left_col.setSpacing(12)

        # Output Control Box (High visibility)
        out_box = QGroupBox("Power Output Stage")
        out_vbox = QVBoxLayout(out_box)
        out_vbox.setSpacing(10)

        out_btn_row = QHBoxLayout()
        self.btn_output_on = QPushButton("OUTPUT ON")
        self.btn_output_on.setObjectName("success")
        self.btn_output_on.setFixedHeight(40)
        self.btn_output_on.setEnabled(False)
        self.btn_output_on.clicked.connect(self._turn_output_on)
        out_btn_row.addWidget(self.btn_output_on)

        self.btn_output_off = QPushButton("OUTPUT OFF")
        self.btn_output_off.setObjectName("danger")
        self.btn_output_off.setFixedHeight(40)
        self.btn_output_off.setEnabled(False)
        self.btn_output_off.clicked.connect(self._turn_output_off)
        out_btn_row.addWidget(self.btn_output_off)
        out_vbox.addLayout(out_btn_row)

        self.lbl_output_badge = QLabel("OUTPUT: STANDBY (OFF)")
        self.lbl_output_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_output_badge.setStyleSheet("""
            background-color: #272a31;
            color: #94a3b8;
            font-weight: 800;
            font-size: 11pt;
            padding: 6px;
            border-radius: 5px;
        """)
        out_vbox.addWidget(self.lbl_output_badge)

        self.chk_high_volt_safety = QCheckBox("Confirm when setting Voltage > 50 V")
        self.chk_high_volt_safety.setChecked(True)
        out_vbox.addWidget(self.chk_high_volt_safety)
        left_col.addWidget(out_box)

        # Remote Setpoints Container (Will be locked in Local Mode)
        self.setpoint_box = QGroupBox("Remote Setpoints & Limits")
        self.setpoint_box_layout = QVBoxLayout(self.setpoint_box)
        self.setpoint_box_layout.setSpacing(10)

        grid = QGridLayout()
        grid.setVerticalSpacing(8)
        grid.setHorizontalSpacing(8)

        # Voltage Row
        grid.addWidget(QLabel("Voltage (V):"), 0, 0)
        self.spin_v_set = QDoubleSpinBox()
        self.spin_v_set.setRange(0.0, self.controller.MAX_VOLTAGE)
        self.spin_v_set.setDecimals(2)
        self.spin_v_set.setValue(0.0)
        self.spin_v_set.setSuffix(" V")
        grid.addWidget(self.spin_v_set, 0, 1)

        self.btn_apply_v = QToolButton()
        self.btn_apply_v.setText("Apply")
        self.btn_apply_v.setEnabled(False)
        self.btn_apply_v.clicked.connect(self._apply_voltage)
        grid.addWidget(self.btn_apply_v, 0, 2)

        self.btn_zero_v = QToolButton()
        self.btn_zero_v.setText("0V")
        self.btn_zero_v.setToolTip("Quick Zero Setpoint")
        self.btn_zero_v.setEnabled(False)
        self.btn_zero_v.clicked.connect(lambda: (self.spin_v_set.setValue(0.0), self._apply_voltage()))
        grid.addWidget(self.btn_zero_v, 0, 3)

        # Current Row
        grid.addWidget(QLabel("Current (I):"), 1, 0)
        self.spin_i_set = QDoubleSpinBox()
        self.spin_i_set.setRange(0.0, self.controller.MAX_CURRENT)
        self.spin_i_set.setDecimals(4)
        self.spin_i_set.setValue(7.0)
        self.spin_i_set.setSuffix(" A")
        grid.addWidget(self.spin_i_set, 1, 1)

        self.btn_apply_i = QToolButton()
        self.btn_apply_i.setText("Apply")
        self.btn_apply_i.setEnabled(False)
        self.btn_apply_i.clicked.connect(self._apply_current)
        grid.addWidget(self.btn_apply_i, 1, 2)

        self.btn_max_i = QToolButton()
        self.btn_max_i.setText("Max")
        self.btn_max_i.setToolTip("Set to 7.0 A Max")
        self.btn_max_i.setEnabled(False)
        self.btn_max_i.clicked.connect(lambda: (self.spin_i_set.setValue(7.0), self._apply_current()))
        grid.addWidget(self.btn_max_i, 1, 3)

        # Power Row
        grid.addWidget(QLabel("Power (P):"), 2, 0)
        self.spin_p_set = QDoubleSpinBox()
        self.spin_p_set.setRange(0.0, self.controller.MAX_POWER)
        self.spin_p_set.setDecimals(1)
        self.spin_p_set.setValue(4000.0)
        self.spin_p_set.setSuffix(" W")
        grid.addWidget(self.spin_p_set, 2, 1)

        self.btn_apply_p = QToolButton()
        self.btn_apply_p.setText("Apply")
        self.btn_apply_p.setEnabled(False)
        self.btn_apply_p.clicked.connect(self._apply_power)
        grid.addWidget(self.btn_apply_p, 2, 2)

        self.btn_max_p = QToolButton()
        self.btn_max_p.setText("Max")
        self.btn_max_p.setToolTip("Set to 4000 W Max")
        self.btn_max_p.setEnabled(False)
        self.btn_max_p.clicked.connect(lambda: (self.spin_p_set.setValue(4000.0), self._apply_power()))
        grid.addWidget(self.btn_max_p, 2, 3)

        # OVP Protection Row
        grid.addWidget(QLabel("OVP Limit:"), 3, 0)
        self.spin_ovp_set = QDoubleSpinBox()
        self.spin_ovp_set.setRange(0.0, 1100.0)
        self.spin_ovp_set.setDecimals(1)
        self.spin_ovp_set.setValue(1100.0)
        self.spin_ovp_set.setSuffix(" V")
        grid.addWidget(self.spin_ovp_set, 3, 1)

        self.btn_apply_ovp = QToolButton()
        self.btn_apply_ovp.setText("Apply")
        self.btn_apply_ovp.setEnabled(False)
        self.btn_apply_ovp.clicked.connect(self._apply_ovp)
        grid.addWidget(self.btn_apply_ovp, 3, 2)

        self.setpoint_box_layout.addLayout(grid)

        # Notice label displayed when Local Mode is active
        self.lbl_local_notice = QLabel("🔒 LOCAL MODE: Setpoints controlled at Front Panel")
        self.lbl_local_notice.setStyleSheet("""
            background-color: #291800;
            border: 1px solid #78350f;
            border-radius: 5px;
            color: #f59e0b;
            font-weight: 700;
            padding: 6px;
            font-size: 8.5pt;
        """)
        self.lbl_local_notice.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_local_notice.setVisible(False)
        self.setpoint_box_layout.addWidget(self.lbl_local_notice)

        left_col.addWidget(self.setpoint_box)

        # Operating Mode Selector
        mode_box = QGroupBox("Operating Mode")
        mb_layout = QHBoxLayout(mode_box)
        self.combo_op_mode = QComboBox()
        self.combo_op_mode.addItems(["UI", "UIP", "UIR", "PVSIM", "USER"])
        mb_layout.addWidget(self.combo_op_mode)

        self.btn_apply_mode = QPushButton("Set Mode")
        self.btn_apply_mode.setEnabled(False)
        self.btn_apply_mode.clicked.connect(self._apply_mode)
        mb_layout.addWidget(self.btn_apply_mode)
        left_col.addWidget(mode_box)

        # Instrument Status Bits / Alarms
        status_box = QGroupBox("Hardware Status & Trips")
        s_layout = QGridLayout(status_box)
        s_layout.setSpacing(6)

        self.status_badges = {}
        status_items = [
            ("OVP", "OVP Trip", "#ef4444"),
            ("CurrLim", "Current Limit (CC)", "#f59e0b"),
            ("PowLim", "Power Limit (CP)", "#f59e0b"),
            ("Standby", "Standby (Off)", "#94a3b8"),
            ("Remote", "Remote Mode", "#0ea5e9"),
            ("Local", "Local Mode", "#f59e0b"),
        ]
        for idx, (key, label_txt, color) in enumerate(status_items):
            badge = QLabel(label_txt)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setStyleSheet(f"""
                background-color: #1a1c22;
                border: 1px solid #2b2f38;
                color: #555b68;
                font-size: 8pt;
                font-weight: 700;
                padding: 4px;
                border-radius: 4px;
            """)
            self.status_badges[key] = (badge, color)
            s_layout.addWidget(badge, idx // 2, idx % 2)

        left_col.addWidget(status_box)
        left_col.addStretch()

        main_layout.addLayout(left_col, 0)

        # Right Column: Modern Vector Readouts + 60 FPS Real-time Chart
        right_col = QVBoxLayout()
        right_col.setSpacing(12)

        # Vector Metric Cards Row
        cards_row = QHBoxLayout()
        cards_row.setSpacing(10)

        self.card_volt = ModernMetricCard("Voltage", "V", "#38bdf8")
        self.card_curr = ModernMetricCard("Current", "A", "#4ade80")
        self.card_pow  = ModernMetricCard("Power", "W", "#fbbf24")
        self.card_res  = ModernMetricCard("Load Res.", "Ω", "#a855f7")

        cards_row.addWidget(self.card_volt)
        cards_row.addWidget(self.card_curr)
        cards_row.addWidget(self.card_pow)
        cards_row.addWidget(self.card_res)
        right_col.addLayout(cards_row)

        # Real-time Graph Container
        graph_box = QGroupBox("Real-Time Telemetry Trend (60 FPS)")
        graph_layout = QVBoxLayout(graph_box)
        graph_layout.setContentsMargins(10, 10, 10, 10)
        graph_layout.setSpacing(8)

        # Chart controls toolbar
        chart_tb = QHBoxLayout()
        chart_tb.addWidget(QLabel("Channels:"))
        self.chk_show_v = QCheckBox("Voltage (Sky Blue)")
        self.chk_show_v.setChecked(True)
        self.chk_show_v.setStyleSheet("color: #38bdf8; font-weight: bold;")
        self.chk_show_v.stateChanged.connect(self._refresh_plot_visibility)
        chart_tb.addWidget(self.chk_show_v)

        self.chk_show_i = QCheckBox("Current (Emerald)")
        self.chk_show_i.setChecked(True)
        self.chk_show_i.setStyleSheet("color: #4ade80; font-weight: bold;")
        self.chk_show_i.stateChanged.connect(self._refresh_plot_visibility)
        chart_tb.addWidget(self.chk_show_i)

        self.chk_show_p = QCheckBox("Power (Gold)")
        self.chk_show_p.setChecked(True)
        self.chk_show_p.setStyleSheet("color: #fbbf24; font-weight: bold;")
        self.chk_show_p.stateChanged.connect(self._refresh_plot_visibility)
        chart_tb.addWidget(self.chk_show_p)

        chart_tb.addStretch()

        self.btn_autorange = QToolButton()
        self.btn_autorange.setText("Auto-Range")
        self.btn_autorange.setToolTip("Fit all active data to screen")
        self.btn_autorange.clicked.connect(self._plot_autorange)
        chart_tb.addWidget(self.btn_autorange)

        self.btn_clear_plot = QToolButton()
        self.btn_clear_plot.setText("Clear Buffer")
        self.btn_clear_plot.clicked.connect(self._plot_clear_buffer)
        chart_tb.addWidget(self.btn_clear_plot)

        self.btn_pub_mode_live = QToolButton()
        self.btn_pub_mode_live.setText("📌 Pub Mode")
        self.btn_pub_mode_live.setCheckable(True)
        self.btn_pub_mode_live.setToolTip("Toggle Publication Mode: freezes style, prevents live auto-range jitter, and locks view for steady publication figure inspection")
        self.btn_pub_mode_live.clicked.connect(self._toggle_publication_mode)
        chart_tb.addWidget(self.btn_pub_mode_live)

        self.btn_batch_export_live = QToolButton()
        self.btn_batch_export_live.setText("📦 Batch Export...")
        self.btn_batch_export_live.setToolTip("Batch export all active traces as multi-panel PDF or individual image files")
        self.btn_batch_export_live.clicked.connect(self._batch_export_live)
        chart_tb.addWidget(self.btn_batch_export_live)

        self.btn_export_live = QToolButton()
        self.btn_export_live.setText("Export Plot...")
        self.btn_export_live.setToolTip("Export live oscilloscope trend to PDF, PNG, JPEG, SVG, or LaTeX TikZ")
        self.btn_export_live.clicked.connect(self._export_live_plot)
        chart_tb.addWidget(self.btn_export_live)

        self.btn_live_settings = QToolButton()
        self.btn_live_settings.setText("⚙ Settings...")
        self.btn_live_settings.setToolTip("Customize Chart Presentation, Labels, Legend, and Export Quality")
        self.btn_live_settings.clicked.connect(self._open_plot_settings_dialog)
        chart_tb.addWidget(self.btn_live_settings)

        graph_layout.addLayout(chart_tb)

        # Setup Plotting Widget (PyQtGraph or Matplotlib Fallback)
        if HAVE_PYQTGRAPH:
            self.plot_widget = pg.PlotWidget()
            self.plot_widget.showGrid(x=True, y=True, alpha=0.15)
            self.plot_widget.setLabel('bottom', 'Time', units='s')
            self.plot_widget.setLabel('left', 'Value')
            self.live_legend = self.plot_widget.addLegend(offset=(10, 10))

            # Modern Pen styles
            pen_v = pg.mkPen(color="#38bdf8", width=2.0)
            pen_i = pg.mkPen(color="#4ade80", width=2.0)
            pen_p = pg.mkPen(color="#fbbf24", width=2.0)

            self.curve_v = self.plot_widget.plot(name="Voltage (V)", pen=pen_v)
            self.curve_i = self.plot_widget.plot(name="Current (A)", pen=pen_i)
            self.curve_p = self.plot_widget.plot(name="Power (W)", pen=pen_p)

            # Interactive Crosshair Hover HUD
            self.v_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#64748b', style=Qt.PenStyle.DashLine))
            self.h_line = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('#64748b', style=Qt.PenStyle.DashLine))
            self.plot_widget.addItem(self.v_line, ignoreBounds=True)
            self.plot_widget.addItem(self.h_line, ignoreBounds=True)
            self.plot_widget.scene().sigMouseMoved.connect(self._on_plot_mouse_moved)

            graph_layout.addWidget(self.plot_widget, 1)
        else:
            # Fallback for systems without pyqtgraph
            self.mpl_fig = Figure(facecolor="#121316")
            self.mpl_ax = self.mpl_fig.add_subplot(111)
            self.mpl_ax.set_facecolor("#181a1f")
            self.mpl_ax.tick_params(colors="#94a3b8")
            self.mpl_line_v, = self.mpl_ax.plot([], [], "#38bdf8", label="Voltage (V)")
            self.mpl_line_i, = self.mpl_ax.plot([], [], "#4ade80", label="Current (A)")
            self.mpl_line_p, = self.mpl_ax.plot([], [], "#fbbf24", label="Power (W)")
            self.mpl_canvas = FigureCanvas(self.mpl_fig)
            graph_layout.addWidget(self.mpl_canvas, 1)

        # Plot HUD info strip
        self.lbl_plot_hud = QLabel("Cursor: Hover over plot to inspect coordinates")
        self.lbl_plot_hud.setStyleSheet("font-size: 8.5pt; font-family: monospace; color: #94a3b8; padding: 2px 4px;")
        graph_layout.addWidget(self.lbl_plot_hud)

        right_col.addWidget(graph_box, 1)
        main_layout.addLayout(right_col, 1)

    # -------------------------------------------------------------------------
    # TAB 2: HIGH-SPEED DATA LOGGER & HISTORICAL SESSION ANALYTICS
    # -------------------------------------------------------------------------
    def _build_logger_tab(self, parent: QWidget):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # Upper Container: Logger Configuration, Controls & Live Stream Preview
        top_container = QWidget()
        top_layout = QVBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(8)

        cfg_box = QGroupBox("Logging Destination & Channels")
        c_layout = QGridLayout(cfg_box)
        c_layout.setSpacing(8)

        c_layout.addWidget(QLabel("Output CSV File:"), 0, 0)
        self.txt_log_path = QLineEdit()
        default_csv = str(Path.cwd() / f"labhp_log_{datetime.date.today().strftime('%Y%m%d')}.csv")
        self.txt_log_path.setText(default_csv)
        c_layout.addWidget(self.txt_log_path, 0, 1)

        self.btn_browse_csv = QToolButton()
        self.btn_browse_csv.setText("Browse...")
        self.btn_browse_csv.clicked.connect(self._browse_log_file)
        c_layout.addWidget(self.btn_browse_csv, 0, 2)

        c_layout.addWidget(QLabel("Sampling Interval:"), 1, 0)
        h_spin = QHBoxLayout()
        self.spin_log_rate = QDoubleSpinBox()
        self.spin_log_rate.setRange(0.05, 3600.0)
        self.spin_log_rate.setValue(0.5)
        self.spin_log_rate.setSingleStep(0.1)
        self.spin_log_rate.setSuffix(" s")
        h_spin.addWidget(self.spin_log_rate)
        h_spin.addWidget(QLabel("(supports high-speed 50ms)"))
        h_spin.addStretch()
        c_layout.addLayout(h_spin, 1, 1, 1, 2)

        # Channel selectors
        ch_row = QHBoxLayout()
        self.chk_log_v = QCheckBox("Voltage (V)")
        self.chk_log_v.setChecked(True)
        self.chk_log_i = QCheckBox("Current (I)")
        self.chk_log_i.setChecked(True)
        self.chk_log_p = QCheckBox("Power (P)")
        self.chk_log_p.setChecked(True)
        self.chk_log_r = QCheckBox("Resistance (R)")
        self.chk_log_r.setChecked(True)
        self.chk_log_out = QCheckBox("Output State")
        self.chk_log_out.setChecked(True)

        ch_row.addWidget(self.chk_log_v)
        ch_row.addWidget(self.chk_log_i)
        ch_row.addWidget(self.chk_log_p)
        ch_row.addWidget(self.chk_log_r)
        ch_row.addWidget(self.chk_log_out)
        ch_row.addStretch()
        c_layout.addLayout(ch_row, 2, 0, 1, 3)

        top_layout.addWidget(cfg_box)

        # Logger Action Buttons
        act_row = QHBoxLayout()
        self.btn_start_log = QPushButton("START LOGGING")
        self.btn_start_log.setObjectName("success")
        self.btn_start_log.setEnabled(False)
        self.btn_start_log.clicked.connect(self._start_logging)
        act_row.addWidget(self.btn_start_log)

        self.btn_pause_log = QPushButton("PAUSE")
        self.btn_pause_log.setEnabled(False)
        self.btn_pause_log.clicked.connect(self._pause_resume_logging)
        act_row.addWidget(self.btn_pause_log)

        self.btn_stop_log = QPushButton("STOP LOGGING")
        self.btn_stop_log.setObjectName("danger")
        self.btn_stop_log.setEnabled(False)
        self.btn_stop_log.clicked.connect(self._stop_logging)
        act_row.addWidget(self.btn_stop_log)

        act_row.addStretch()
        self.lbl_log_stats = QLabel("Records: 0  |  Elapsed: 00:00:00  |  Status: IDLE")
        self.lbl_log_stats.setStyleSheet("font-size: 9.5pt; font-weight: 700; color: #94a3b8;")
        act_row.addWidget(self.lbl_log_stats)
        top_layout.addLayout(act_row)

        # Live Logger Terminal Preview (compact)
        self.log_terminal = QTextEdit()
        self.log_terminal.setReadOnly(True)
        self.log_terminal.document().setMaximumBlockCount(500)
        self.log_terminal.setMinimumHeight(65)
        self.log_terminal.setMaximumHeight(105)
        top_layout.addWidget(self.log_terminal)

        splitter.addWidget(top_container)

        # Lower Container: Full-Session Historical Log Plotter & Analytics
        hist_box = QGroupBox("Full-Session Historical Log Waveform Plotter & Analytics")
        hist_layout = QVBoxLayout(hist_box)
        hist_layout.setContentsMargins(10, 10, 10, 10)
        hist_layout.setSpacing(8)

        # Historical Toolbar
        hist_tb = QHBoxLayout()
        hist_tb.addWidget(QLabel("Source:"))
        self.lbl_hist_source = QLabel("None loaded")
        self.lbl_hist_source.setStyleSheet("font-weight: 700; color: #38bdf8; font-size: 8.5pt;")
        hist_tb.addWidget(self.lbl_hist_source)

        self.btn_load_csv = QPushButton("Open CSV Log...")
        self.btn_load_csv.setToolTip("Open and analyze any previously recorded CSV log file from disk")
        self.btn_load_csv.clicked.connect(self._load_csv_file_dialog)
        hist_tb.addWidget(self.btn_load_csv)

        self.btn_plot_current = QPushButton("Plot Active Log")
        self.btn_plot_current.setToolTip("Plot all points recorded in the current logging target file")
        self.btn_plot_current.clicked.connect(self._plot_active_log)
        hist_tb.addWidget(self.btn_plot_current)

        hist_tb.addSpacing(10)
        hist_tb.addWidget(QLabel("Channels:"))

        self.chk_hist_v = QCheckBox("V (Sky)")
        self.chk_hist_v.setChecked(True)
        self.chk_hist_v.setStyleSheet("color: #38bdf8; font-weight: bold;")
        self.chk_hist_v.stateChanged.connect(self._refresh_hist_plot_visibility)
        hist_tb.addWidget(self.chk_hist_v)

        self.chk_hist_i = QCheckBox("I (Green)")
        self.chk_hist_i.setChecked(True)
        self.chk_hist_i.setStyleSheet("color: #4ade80; font-weight: bold;")
        self.chk_hist_i.stateChanged.connect(self._refresh_hist_plot_visibility)
        hist_tb.addWidget(self.chk_hist_i)

        self.chk_hist_p = QCheckBox("P (Gold)")
        self.chk_hist_p.setChecked(True)
        self.chk_hist_p.setStyleSheet("color: #fbbf24; font-weight: bold;")
        self.chk_hist_p.stateChanged.connect(self._refresh_hist_plot_visibility)
        hist_tb.addWidget(self.chk_hist_p)

        self.chk_hist_r = QCheckBox("R (Purple)")
        self.chk_hist_r.setChecked(False)
        self.chk_hist_r.setStyleSheet("color: #a855f7; font-weight: bold;")
        self.chk_hist_r.stateChanged.connect(self._refresh_hist_plot_visibility)
        hist_tb.addWidget(self.chk_hist_r)

        hist_tb.addStretch()

        self.btn_hist_autorange = QToolButton()
        self.btn_hist_autorange.setText("Auto-Range")
        self.btn_hist_autorange.clicked.connect(self._hist_plot_autorange)
        hist_tb.addWidget(self.btn_hist_autorange)

        self.btn_pub_mode_hist = QToolButton()
        self.btn_pub_mode_hist.setText("📌 Pub Mode")
        self.btn_pub_mode_hist.setCheckable(True)
        self.btn_pub_mode_hist.setToolTip("Toggle Publication Mode: freezes style and locks view for steady publication figure inspection")
        self.btn_pub_mode_hist.clicked.connect(self._toggle_publication_mode)
        hist_tb.addWidget(self.btn_pub_mode_hist)

        self.btn_hist_batch_export = QToolButton()
        self.btn_hist_batch_export.setText("📦 Batch Export...")
        self.btn_hist_batch_export.setToolTip("Batch export all session traces as multi-panel PDF or individual image files")
        self.btn_hist_batch_export.clicked.connect(self._batch_export_historical)
        hist_tb.addWidget(self.btn_hist_batch_export)

        self.btn_hist_settings = QToolButton()
        self.btn_hist_settings.setText("⚙ Settings...")
        self.btn_hist_settings.setToolTip("Customize Title, Axis Labels, Legend Placement, Line Widths, and Grid")
        self.btn_hist_settings.clicked.connect(self._open_plot_settings_dialog)
        hist_tb.addWidget(self.btn_hist_settings)

        self.btn_hist_export = QPushButton("Export Plot...")
        self.btn_hist_export.setObjectName("primary")
        self.btn_hist_export.setToolTip("Export historical session waveform to PDF, PNG, JPEG, SVG, or LaTeX TikZ")
        self.btn_hist_export.clicked.connect(self._export_historical_plot)
        hist_tb.addWidget(self.btn_hist_export)

        hist_layout.addLayout(hist_tb)

        # Summary statistics banner
        self.lbl_hist_stats = QLabel("Session Duration: --  |  Peak V: --  |  Peak I: --  |  Peak P: --  |  Total Energy: --")
        self.lbl_hist_stats.setStyleSheet("""
            background-color: #121418;
            border: 1px solid #232730;
            border-radius: 4px;
            color: #e2e8f0;
            font-size: 8.5pt;
            font-family: monospace;
            padding: 5px 10px;
            font-weight: 600;
        """)
        hist_layout.addWidget(self.lbl_hist_stats)

        # Canvas widget setup
        if HAVE_PYQTGRAPH:
            self.hist_plot_widget = pg.PlotWidget()
            self.hist_plot_widget.showGrid(x=True, y=True, alpha=0.15)
            self.hist_plot_widget.setLabel('bottom', 'Elapsed Time', units='s')
            self.hist_plot_widget.setLabel('left', 'Magnitude')
            self.hist_legend = self.hist_plot_widget.addLegend(offset=(10, 10))
            self.hist_plot_widget.plotItem.setDownsampling(auto=True, mode='peak')
            self.hist_plot_widget.plotItem.setClipToView(True)

            pen_v = pg.mkPen(color="#38bdf8", width=2.0)
            pen_i = pg.mkPen(color="#4ade80", width=2.0)
            pen_p = pg.mkPen(color="#fbbf24", width=2.0)
            pen_r = pg.mkPen(color="#a855f7", width=2.0)

            self.hist_curve_v = self.hist_plot_widget.plot(name="Voltage (V)", pen=pen_v)
            self.hist_curve_i = self.hist_plot_widget.plot(name="Current (A)", pen=pen_i)
            self.hist_curve_p = self.hist_plot_widget.plot(name="Power (W)", pen=pen_p)
            self.hist_curve_r = self.hist_plot_widget.plot(name="Resistance (Ω)", pen=pen_r)

            # Interactive Crosshair Hover HUD
            self.hist_v_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#64748b', style=Qt.PenStyle.DashLine))
            self.hist_h_line = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('#64748b', style=Qt.PenStyle.DashLine))
            self.hist_plot_widget.addItem(self.hist_v_line, ignoreBounds=True)
            self.hist_plot_widget.addItem(self.hist_h_line, ignoreBounds=True)
            self.hist_plot_widget.scene().sigMouseMoved.connect(self._on_hist_plot_mouse_moved)

            hist_layout.addWidget(self.hist_plot_widget, 1)
        else:
            self.hist_mpl_fig = Figure(facecolor="#121316")
            self.hist_mpl_ax = self.hist_mpl_fig.add_subplot(111)
            self.hist_mpl_ax.set_facecolor("#181a1f")
            self.hist_mpl_ax.tick_params(colors="#94a3b8")
            self.hist_mpl_line_v, = self.hist_mpl_ax.plot([], [], "#38bdf8", label="Voltage (V)")
            self.hist_mpl_line_i, = self.hist_mpl_ax.plot([], [], "#4ade80", label="Current (A)")
            self.hist_mpl_line_p, = self.hist_mpl_ax.plot([], [], "#fbbf24", label="Power (W)")
            self.hist_mpl_line_r, = self.hist_mpl_ax.plot([], [], "#a855f7", label="Resistance (Ω)")
            self.hist_mpl_canvas = FigureCanvas(self.hist_mpl_fig)
            hist_layout.addWidget(self.hist_mpl_canvas, 1)

        # Plot HUD cursor inspector
        self.lbl_hist_hud = QLabel("Cursor: Hover over session waveform to inspect precise point telemetry")
        self.lbl_hist_hud.setStyleSheet("font-size: 8pt; font-family: monospace; color: #94a3b8; padding: 2px 4px;")
        hist_layout.addWidget(self.lbl_hist_hud)

        splitter.addWidget(hist_box)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 7)

        layout.addWidget(splitter)

    # -------------------------------------------------------------------------
    # TAB 3: SAFE OPERATING AREA (SOA)
    # -------------------------------------------------------------------------
    def _build_soa_tab(self, parent: QWidget):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        soa_desc = QLabel(
            "Safe Operating Area (SOA): Shows the 1000 V × 7 A × 4000 W hyperbolic power envelope.\n"
            "The yellow dot tracks your real-time operating point (Voltage vs. Current) against the maximum hardware limit."
        )
        soa_desc.setStyleSheet("color: #94a3b8; font-size: 9.5pt;")
        layout.addWidget(soa_desc)

        if HAVE_PYQTGRAPH:
            self.soa_plot = pg.PlotWidget()
            self.soa_plot.showGrid(x=True, y=True, alpha=0.2)
            self.soa_plot.setLabel('bottom', 'Voltage', units='V')
            self.soa_plot.setLabel('left', 'Current', units='A')
            self.soa_plot.setXRange(0, 1050)
            self.soa_plot.setYRange(0, 8)

            # Draw hyperbolic 4 kW boundary: I = min(7.0, 4000 / V)
            v_vals = np.linspace(10, 1000, 200)
            i_boundary = np.minimum(7.0, 4000.0 / v_vals)
            self.soa_plot.plot(v_vals, i_boundary, pen=pg.mkPen('#ef4444', width=2, style=Qt.PenStyle.DashLine), name="4000 W Limit")

            # Real-time marker dot
            self.soa_marker = pg.ScatterPlotItem(
                size=14, pen=pg.mkPen('#ffffff', width=1.5), brush=pg.mkBrush('#fbbf24')
            )
            self.soa_plot.addItem(self.soa_marker)
            layout.addWidget(self.soa_plot, 1)
        else:
            lbl_fallback = QLabel("PyQtGraph is required for interactive hardware-accelerated SOA mapping.")
            layout.addWidget(lbl_fallback)

    # -------------------------------------------------------------------------
    # TAB 4: ASCII COMMAND TERMINAL
    # -------------------------------------------------------------------------
    def _build_terminal_tab(self, parent: QWidget):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Quick Commands Bar
        quick_row = QHBoxLayout()
        quick_row.addWidget(QLabel("Presets:"))
        quick_cmds = [
            ("IDN?", "ID"), ("Measure V", "MU"), ("Measure I", "MI"),
            ("Status", "STATUS"), ("Output State", "SB"), ("Limits", "LIMU"),
            ("Go Remote", "GTR"), ("Go Local", "GTL"), ("Save Setup", "SS")
        ]
        for name, cmd in quick_cmds:
            btn = QToolButton()
            btn.setText(name)
            btn.clicked.connect(lambda checked, c=cmd: self._send_terminal_cmd(c))
            quick_row.addWidget(btn)
        quick_row.addStretch()
        layout.addLayout(quick_row)

        # Output Log
        self.term_log = QTextEdit()
        self.term_log.setReadOnly(True)
        layout.addWidget(self.term_log, 1)

        # Command Input Field
        in_row = QHBoxLayout()
        in_row.addWidget(QLabel("ASCII Command:"))
        self.txt_term_cmd = QLineEdit()
        self.txt_term_cmd.setPlaceholderText("Enter ASCII command (e.g. UA,24.5 or MI or GTR)...")
        self.txt_term_cmd.returnPressed.connect(lambda: self._send_terminal_cmd(self.txt_term_cmd.text()))
        in_row.addWidget(self.txt_term_cmd, 1)

        self.btn_send_cmd = QPushButton("SEND")
        self.btn_send_cmd.clicked.connect(lambda: self._send_terminal_cmd(self.txt_term_cmd.text()))
        in_row.addWidget(self.btn_send_cmd)

        self.btn_clear_term = QToolButton()
        self.btn_clear_term.setText("Clear")
        self.btn_clear_term.clicked.connect(self.term_log.clear)
        in_row.addWidget(self.btn_clear_term)

        layout.addLayout(in_row)

    # -------------------------------------------------------------------------
    # CONNECTION & LOCAL / REMOTE MODE SWITCH LOGIC
    # -------------------------------------------------------------------------
    def _toggle_connection(self):
        if self.controller.connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        ip = self.combo_ip.currentText().strip()
        port = self.spin_port.value()
        if not ip:
            QMessageBox.warning(self, "Connection Error", "Please specify a valid IP address.")
            return

        self.status_bar.showMessage(f"Connecting to {ip}:{port}...")
        QApplication.processEvents()

        try:
            self.controller.connect(ip, port)
            idn = self.controller.get_idn()
            self.controller.set_remote()  # Start in Remote mode by default

            self.lbl_conn_status.setText("● Connected")
            self.lbl_conn_status.setStyleSheet("color: #22c55e; font-weight: 700; font-size: 9.5pt;")
            self.btn_connect.setText("DISCONNECT")
            self.btn_connect.setObjectName("danger")
            self.btn_connect.setStyleSheet("")

            # Update settings
            self._save_settings()

            # Enable general UI
            self._set_ui_connected(True)
            self._set_local_mode_ui(False)  # Remote active

            # Start Background Telemetry Worker
            self.telemetry_worker = TelemetryWorker(self.controller, interval_s=0.2)
            self.telemetry_worker.telemetry_received.connect(self._on_telemetry_received)
            self.telemetry_worker.output_state_received.connect(self._on_output_state_received)
            self.telemetry_worker.status_received.connect(self._on_status_word_received)
            self.telemetry_worker.connection_lost.connect(self._on_connection_lost)
            self.telemetry_worker.start()

            self.status_bar.showMessage(f"Connected to {idn} on {ip}:{port}")

        except Exception as e:
            self.controller.disconnect()
            QMessageBox.critical(self, "Connection Failed", f"Could not connect to {ip}:{port}\nError: {e}")
            self.status_bar.showMessage("Connection failed.")

    def _disconnect(self):
        if self.logger_thread and self.logger_thread.isRunning():
            self._stop_logging()

        if self.telemetry_worker:
            self.telemetry_worker.stop()
            self.telemetry_worker = None

        self.controller.disconnect()
        self.lbl_conn_status.setText("● Disconnected")
        self.lbl_conn_status.setStyleSheet("color: #ef4444; font-weight: 700; font-size: 9.5pt;")
        self.btn_connect.setText("CONNECT")
        self.btn_connect.setObjectName("primary")
        self.btn_connect.setStyleSheet("")

        self._set_ui_connected(False)
        self.status_bar.showMessage("Disconnected.")

    def _on_connection_lost(self, err_msg: str):
        self._disconnect()
        QMessageBox.warning(self, "Connection Lost", f"The connection to the LAB-HP instrument was lost:\n{err_msg}")

    def _watchdog_heartbeat(self):
        """Background health check."""
        if not self.controller.connected:
            return
        # If no telemetry thread running, probe manually
        if not self.telemetry_worker or not self.telemetry_worker.isRunning():
            try:
                self.controller.get_idn()
            except Exception:
                self._on_connection_lost("Watchdog ping failed")

    # =========================================================================
    # CORE LOGIC: LOCAL vs. REMOTE MODE SWITCHING
    # =========================================================================
    def _toggle_local_remote_mode(self):
        """
        Switches between Remote mode (computer controls setpoints)
        and Local mode (operator controls setpoints at physical front panel).
        In both modes, data logging, graphing, and readouts stay 100% active!
        """
        if not self.controller.connected:
            return

        new_local = not self.is_local_mode
        try:
            if new_local:
                # Transition to Local
                self.controller.set_local()
                self._set_local_mode_ui(True)
                self.status_bar.showMessage("Switched to LOCAL MODE: Front-panel physical knobs active.")
            else:
                # Transition to Remote
                self.controller.set_remote()
                self._set_local_mode_ui(False)
                self.status_bar.showMessage("Switched to REMOTE MODE: Software setpoint controls enabled.")
        except Exception as e:
            QMessageBox.critical(self, "Mode Switch Error", f"Failed to send mode command: {e}")

    def _set_local_mode_ui(self, is_local: bool):
        """
        Update UI controls when switching between Local and Remote.
        Notice: Data logger, graph controls, and readouts are NEVER disabled!
        """
        self.is_local_mode = is_local

        if is_local:
            # Local Mode Presentation
            self.btn_mode_toggle.setText("🔒 LOCAL (PANEL)")
            self.btn_mode_toggle.setObjectName("mode_local")
            self.btn_mode_toggle.style().unpolish(self.btn_mode_toggle)
            self.btn_mode_toggle.style().polish(self.btn_mode_toggle)

            # Lock setpoint adjustment controls to prevent conflict with operator
            self.spin_v_set.setEnabled(False)
            self.spin_i_set.setEnabled(False)
            self.spin_p_set.setEnabled(False)
            self.spin_ovp_set.setEnabled(False)
            self.btn_apply_v.setEnabled(False)
            self.btn_apply_i.setEnabled(False)
            self.btn_apply_p.setEnabled(False)
            self.btn_apply_ovp.setEnabled(False)
            self.btn_zero_v.setEnabled(False)
            self.btn_max_i.setEnabled(False)
            self.btn_max_p.setEnabled(False)
            self.combo_op_mode.setEnabled(False)
            self.btn_apply_mode.setEnabled(False)
            self.lbl_local_notice.setVisible(True)

            # Front-panel has control of output, so disable software output switches
            self.btn_output_on.setEnabled(False)
            self.btn_output_off.setEnabled(False)
        else:
            # Remote Mode Presentation
            self.btn_mode_toggle.setText("⚡ REMOTE MODE")
            self.btn_mode_toggle.setObjectName("mode_remote")
            self.btn_mode_toggle.style().unpolish(self.btn_mode_toggle)
            self.btn_mode_toggle.style().polish(self.btn_mode_toggle)

            # Unlock all remote setpoint adjustments
            self.spin_v_set.setEnabled(True)
            self.spin_i_set.setEnabled(True)
            self.spin_p_set.setEnabled(True)
            self.spin_ovp_set.setEnabled(True)
            self.btn_apply_v.setEnabled(True)
            self.btn_apply_i.setEnabled(True)
            self.btn_apply_p.setEnabled(True)
            self.btn_apply_ovp.setEnabled(True)
            self.btn_zero_v.setEnabled(True)
            self.btn_max_i.setEnabled(True)
            self.btn_max_p.setEnabled(True)
            self.combo_op_mode.setEnabled(True)
            self.btn_apply_mode.setEnabled(True)
            self.lbl_local_notice.setVisible(False)

            # Enable software output control
            self.btn_output_on.setEnabled(True)
            self.btn_output_off.setEnabled(True)

    def _set_ui_connected(self, connected: bool):
        """General UI state transitions on connect/disconnect."""
        self.btn_estop.setEnabled(connected)
        self.btn_mode_toggle.setEnabled(connected)
        self.btn_start_log.setEnabled(connected and (self.logger_thread is None))
        self.btn_send_cmd.setEnabled(connected)

        if not connected:
            self._set_local_mode_ui(True)  # Lock setpoints
            self.btn_output_on.setEnabled(False)
            self.btn_output_off.setEnabled(False)
            self.btn_start_log.setEnabled(False)
            self.btn_pause_log.setEnabled(False)
            self.btn_stop_log.setEnabled(False)

    # -------------------------------------------------------------------------
    # TELEMETRY RECEPTION & 60 FPS GRAPHING
    # -------------------------------------------------------------------------
    def _on_telemetry_received(self, meas: dict):
        v = meas["voltage"]
        i = meas["current"]
        p = meas["power"]
        r = meas["resistance"]

        # Update Vector Metric Readout Cards
        self.card_volt.update_measurement(v, decimals=2)
        self.card_curr.update_measurement(i, decimals=4)
        self.card_pow.update_measurement(p, decimals=1)

        # Resistance Card (handles open circuit / zero current gracefully)
        if math.isinf(r) or r > 999999:
            self.card_res.lbl_value.setText("OPEN")
            self.card_res.lbl_delta.setText("I < 0.5 mA")
        elif r >= 1000.0:
            self.card_res.lbl_value.setText(f"{r / 1000.0:.2f} k")
            self.card_res.lbl_delta.setText("Calculated (V/I)")
        else:
            self.card_res.lbl_value.setText(f"{r:.2f}")
            self.card_res.lbl_delta.setText("Calculated (V/I)")

        # Push to Ring Buffers for Real-time Chart
        now = time.time()
        if self.history_t0 is None:
            self.history_t0 = now
        t_rel = now - self.history_t0

        self.history_t.append(t_rel)
        self.history_v.append(v)
        self.history_i.append(i)
        self.history_p.append(p)

        if len(self.history_t) > self.max_history_points:
            self.history_t.pop(0)
            self.history_v.pop(0)
            self.history_i.pop(0)
            self.history_p.pop(0)

        # 60 FPS update via PyQtGraph (Frozen if publication mode is active)
        if getattr(self, "publication_mode", False):
            return

        if HAVE_PYQTGRAPH:
            _, _, _, is_step = parse_plot_style(self.plot_settings.get("plot_style", ""))
            if is_step and len(self.history_t) > 1:
                t_step = np.repeat(self.history_t, 2)[1:]
                if self.chk_show_v.isChecked(): self.curve_v.setData(t_step, np.repeat(self.history_v, 2)[:-1])
                if self.chk_show_i.isChecked(): self.curve_i.setData(t_step, np.repeat(self.history_i, 2)[:-1])
                if self.chk_show_p.isChecked(): self.curve_p.setData(t_step, np.repeat(self.history_p, 2)[:-1])
            else:
                if self.chk_show_v.isChecked(): self.curve_v.setData(self.history_t, self.history_v)
                if self.chk_show_i.isChecked(): self.curve_i.setData(self.history_t, self.history_i)
                if self.chk_show_p.isChecked(): self.curve_p.setData(self.history_t, self.history_p)

            # Update SOA Scatter Marker
            self.soa_marker.setData([{'pos': (v, i), 'data': 1}])
        else:
            self.mpl_line_v.set_data(self.history_t, self.history_v)
            self.mpl_line_i.set_data(self.history_t, self.history_i)
            self.mpl_line_p.set_data(self.history_t, self.history_p)
            self.mpl_ax.relim()
            self.mpl_ax.autoscale_view()
            self.mpl_canvas.draw_idle()

    def _on_output_state_received(self, out_on: bool):
        if out_on:
            self.lbl_output_badge.setText("OUTPUT: LIVE (ACTIVE)")
            self.lbl_output_badge.setStyleSheet("""
                background-color: #14532d;
                border: 1px solid #16a34a;
                color: #4ade80;
                font-weight: 800;
                font-size: 11pt;
                padding: 6px;
                border-radius: 5px;
            """)
        else:
            self.lbl_output_badge.setText("OUTPUT: STANDBY (OFF)")
            self.lbl_output_badge.setStyleSheet("""
                background-color: #272a31;
                border: 1px solid #373c47;
                color: #94a3b8;
                font-weight: 800;
                font-size: 11pt;
                padding: 6px;
                border-radius: 5px;
            """)

    def _on_status_word_received(self, status: dict):
        # Update Hardware Status Badges
        key_map = {
            "OVP": "OVP shutdown",
            "CurrLim": "Current limit",
            "PowLim": "Power limit",
            "Standby": "Standby",
            "Remote": "Remote mode",
            "Local": "Local mode",
        }
        for badge_key, status_field in key_map.items():
            active = status.get(status_field, False)
            badge, active_color = self.status_badges[badge_key]
            if active:
                badge.setStyleSheet(f"""
                    background-color: {active_color};
                    border: 1px solid {active_color};
                    color: #ffffff;
                    font-size: 8pt;
                    font-weight: 800;
                    padding: 4px;
                    border-radius: 4px;
                """)
            else:
                badge.setStyleSheet("""
                    background-color: #1a1c22;
                    border: 1px solid #2b2f38;
                    color: #555b68;
                    font-size: 8pt;
                    font-weight: 700;
                    padding: 4px;
                    border-radius: 4px;
                """)

        # Sync GUI state if instrument was switched to Local via front-panel knob
        is_inst_local = status.get("Local mode", False)
        if is_inst_local != self.is_local_mode:
            self._set_local_mode_ui(is_inst_local)

    def _on_plot_mouse_moved(self, pos):
        """Crosshair inspection HUD."""
        if not HAVE_PYQTGRAPH:
            return
        if self.plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
            x = mouse_point.x()
            y = mouse_point.y()
            self.v_line.setPos(x)
            self.h_line.setPos(y)

            # Find closest sample
            if self.history_t:
                idx = np.searchsorted(self.history_t, x)
                idx = max(0, min(idx, len(self.history_t) - 1))
                t_val = self.history_t[idx]
                v_val = self.history_v[idx]
                i_val = self.history_i[idx]
                p_val = self.history_p[idx]
                r_val = (v_val / i_val) if i_val > 0.0005 else float('inf')
                r_str = f"{r_val:.2f} Ω" if not math.isinf(r_val) else "OPEN"
                self.lbl_plot_hud.setText(
                    f"HUD Cursor @ {t_val:6.2f}s  |  Voltage: {v_val:6.2f} V  |  Current: {i_val:6.4f} A  |  Power: {p_val:6.1f} W  |  Load: {r_str}"
                )

    def _refresh_plot_visibility(self):
        if HAVE_PYQTGRAPH:
            self.curve_v.setVisible(self.chk_show_v.isChecked())
            self.curve_i.setVisible(self.chk_show_i.isChecked())
            self.curve_p.setVisible(self.chk_show_p.isChecked())

    def _plot_autorange(self):
        if HAVE_PYQTGRAPH:
            self.plot_widget.autoRange()

    def _plot_clear_buffer(self):
        self.history_t.clear()
        self.history_v.clear()
        self.history_i.clear()
        self.history_p.clear()
        self.history_t0 = None
        if HAVE_PYQTGRAPH:
            self.curve_v.clear()
            self.curve_i.clear()
            self.curve_p.clear()

    # -------------------------------------------------------------------------
    # SETPOINT APPLY ACTIONS
    # -------------------------------------------------------------------------
    def _apply_voltage(self):
        v = self.spin_v_set.value()
        if self.chk_high_volt_safety.isChecked() and v > 50.0:
            res = QMessageBox.warning(
                self, "High Voltage Warning",
                f"You are requesting {v:.1f} V (> 50 V safety limit).\nEnsure safe isolation before proceeding.",
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
            )
            if res != QMessageBox.StandardButton.Ok:
                return

        try:
            self.controller.set_voltage(v)
            self.card_volt.update_setpoint(v, decimals=2)
            self.status_bar.showMessage(f"Voltage setpoint applied: {v:.2f} V")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _apply_current(self):
        i = self.spin_i_set.value()
        try:
            self.controller.set_current(i)
            self.card_curr.update_setpoint(i, decimals=4)
            self.status_bar.showMessage(f"Current limit applied: {i:.4f} A")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _apply_power(self):
        p = self.spin_p_set.value()
        try:
            self.controller.set_power(p)
            self.card_pow.update_setpoint(p, decimals=1)
            self.status_bar.showMessage(f"Power limit applied: {p:.1f} W")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _apply_ovp(self):
        v = self.spin_ovp_set.value()
        try:
            self.controller.set_ovp(v)
            self.status_bar.showMessage(f"OVP limit applied: {v:.1f} V")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _apply_mode(self):
        mode = self.combo_op_mode.currentText()
        try:
            self.controller.set_mode(mode)
            self.status_bar.showMessage(f"Operating mode set: {mode}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _turn_output_on(self):
        try:
            self.controller.output_on()
            self._on_output_state_received(True)
            self.status_bar.showMessage("Output ENABLED (Live)")
        except Exception as e:
            QMessageBox.critical(self, "Output Error", str(e))

    def _turn_output_off(self):
        try:
            self.controller.output_off()
            self._on_output_state_received(False)
            self.status_bar.showMessage("Output DISABLED (Standby)")
        except Exception as e:
            QMessageBox.critical(self, "Output Error", str(e))

    def _toggle_output_shortcut(self):
        if not self.controller.connected or self.is_local_mode:
            return
        curr = self.controller.get_output_state()
        if curr:
            self._turn_output_off()
        else:
            self._turn_output_on()

    def _toggle_emergency_stop(self):
        """Emergency Stop with latching mechanism."""
        if not self.controller.connected:
            return

        if not self.emergency_latched:
            try:
                self.controller.output_off()
                self.controller.set_local()
                self.emergency_latched = True
                self.btn_estop.setProperty("latched", "true")
                self.btn_estop.setText("LATCHED\nRESET?")
                self.btn_estop.style().unpolish(self.btn_estop)
                self.btn_estop.style().polish(self.btn_estop)
                self._on_output_state_received(False)
                self.status_bar.showMessage("EMERGENCY SHUTDOWN TRIPPED: Output Off & Local set.")
                QMessageBox.critical(self, "Emergency Shutdown", "Output has been immediately cut off.")
            except Exception as e:
                QMessageBox.critical(self, "E-Stop Failure", f"Failed to send emergency stop: {e}")
        else:
            # Unlatch
            self.emergency_latched = False
            self.btn_estop.setProperty("latched", "false")
            self.btn_estop.setText("EMERGENCY\nSTOP")
            self.btn_estop.style().unpolish(self.btn_estop)
            self.btn_estop.style().polish(self.btn_estop)
            self.status_bar.showMessage("Emergency stop unlatched. Ready.")

    # -------------------------------------------------------------------------
    # DATA LOGGER IMPLEMENTATION
    # -------------------------------------------------------------------------
    def _browse_log_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "Select CSV Log File", self.txt_log_path.text(), "CSV Files (*.csv)")
        if path:
            self.txt_log_path.setText(path)

    def _start_logging(self):
        path = self.txt_log_path.text().strip()
        if not path:
            QMessageBox.warning(self, "Logger Error", "Please specify a valid destination file path.")
            return

        channels = {
            'v': self.chk_log_v.isChecked(),
            'i': self.chk_log_i.isChecked(),
            'p': self.chk_log_p.isChecked(),
            'r': self.chk_log_r.isChecked(),
            'out': self.chk_log_out.isChecked(),
        }

        interval = self.spin_log_rate.value()
        self.logger_thread = HighSpeedLogger(self.controller, path, interval, channels)
        self.logger_thread.row_logged.connect(self._on_log_row_added)
        self.logger_thread.error_occurred.connect(lambda err: QMessageBox.critical(self, "Log Error", err))
        self.logger_thread.start()

        self.btn_start_log.setEnabled(False)
        self.btn_pause_log.setEnabled(True)
        self.btn_stop_log.setEnabled(True)
        self.status_bar.showMessage(f"Data logging active -> {path}")

    def _pause_resume_logging(self):
        if not self.logger_thread:
            return
        if self.btn_pause_log.text() == "PAUSE":
            self.logger_thread.pause()
            self.btn_pause_log.setText("RESUME")
            self.status_bar.showMessage("Logging PAUSED.")
        else:
            self.logger_thread.resume()
            self.btn_pause_log.setText("PAUSE")
            self.status_bar.showMessage("Logging RESUMED.")

    def _stop_logging(self):
        if self.logger_thread:
            self.logger_thread.stop()
            self.logger_thread = None

        self.btn_start_log.setEnabled(True)
        self.btn_pause_log.setEnabled(False)
        self.btn_stop_log.setEnabled(False)
        self.btn_pause_log.setText("PAUSE")
        self.status_bar.showMessage("Data logging stopped.")

        # Automatically plot the completed session in the historical plotter!
        path = self.txt_log_path.text().strip()
        if os.path.exists(path):
            self._load_and_plot_csv(path)

    def _on_log_row_added(self, count: int, preview: str):
        self.lbl_log_stats.setText(f"Records: {count:05d}  |  File: Active  |  Status: RECORDING")
        self.log_terminal.append(preview)

    # -------------------------------------------------------------------------
    # HISTORICAL SESSION PLOTTER & CSV ANALYTICS
    # -------------------------------------------------------------------------
    def _load_csv_file_dialog(self):
        default_dir = str(Path(self.txt_log_path.text().strip()).parent)
        path, _ = QFileDialog.getOpenFileName(
            self, "Open CSV Log File", default_dir, "CSV Files (*.csv);;All Files (*.*)"
        )
        if path:
            self._load_and_plot_csv(path)

    def _plot_active_log(self):
        path = self.txt_log_path.text().strip()
        if not os.path.exists(path):
            QMessageBox.information(
                self, "Log File Not Found",
                f"The log file does not exist yet:\n{path}\n\nStart a logging session first to generate data."
            )
            return
        self._load_and_plot_csv(path)

    def _load_and_plot_csv(self, filepath: str):
        if not os.path.exists(filepath):
            QMessageBox.warning(self, "File Error", f"Cannot find file:\n{filepath}")
            return

        try:
            t_data, v_data, i_data, p_data, r_data = [], [], [], [], []
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if not header:
                    QMessageBox.warning(self, "Empty CSV", "The selected CSV file has no content.")
                    return

                col_t, col_v, col_i, col_p, col_r = -1, -1, -1, -1, -1
                for idx, col in enumerate(header):
                    cl = col.strip().lower()
                    if "elapsed" in cl or cl == "time" or "sec" in cl:
                        if col_t == -1: col_t = idx
                    elif "voltage_meas" in cl or cl.startswith("volt") or "v_meas" in cl:
                        col_v = idx
                    elif "current_meas" in cl or cl.startswith("curr") or "i_meas" in cl:
                        col_i = idx
                    elif "power_meas" in cl or cl.startswith("pow") or "p_meas" in cl:
                        col_p = idx
                    elif "resistance" in cl or cl.startswith("res"):
                        col_r = idx

                # Fallback for elapsed column
                if col_t == -1 and len(header) > 2:
                    col_t = 2

                row_idx = 0
                for row in reader:
                    if not row or len(row) < 2:
                        continue
                    try:
                        t_val = float(row[col_t]) if (col_t >= 0 and col_t < len(row)) else (row_idx * 0.1)
                        v_val = float(row[col_v]) if (col_v >= 0 and col_v < len(row)) else 0.0
                        i_val = float(row[col_i]) if (col_i >= 0 and col_i < len(row)) else 0.0
                        p_val = float(row[col_p]) if (col_p >= 0 and col_p < len(row)) else (v_val * i_val)
                        
                        r_val = float('inf')
                        if col_r >= 0 and col_r < len(row):
                            try:
                                r_val = float(row[col_r])
                            except ValueError:
                                r_val = (v_val / i_val) if i_val > 0.001 else float('inf')
                        else:
                            r_val = (v_val / i_val) if i_val > 0.001 else float('inf')

                        t_data.append(t_val)
                        v_data.append(v_val)
                        i_data.append(i_val)
                        p_data.append(p_val)
                        r_data.append(r_val)
                        row_idx += 1
                    except (ValueError, IndexError):
                        continue

            if not t_data:
                QMessageBox.information(self, "No Valid Rows", "No valid numerical telemetry rows were found in the CSV.")
                return

            self.hist_t = t_data
            self.hist_v = v_data
            self.hist_i = i_data
            self.hist_p = p_data
            self.hist_r = r_data
            self.current_loaded_csv = filepath
            self.lbl_hist_source.setText(f"{Path(filepath).name} ({len(t_data):,} pts)")

            # Compute session metrics
            dur = t_data[-1] - t_data[0] if len(t_data) > 1 else 0.0
            v_max = max(v_data) if v_data else 0.0
            i_max = max(i_data) if i_data else 0.0
            p_max = max(p_data) if p_data else 0.0

            # Trapezoidal numerical integration for cumulative energy (Wh)
            energy_wh = 0.0
            for k in range(1, len(t_data)):
                dt = t_data[k] - t_data[k-1]
                if 0 < dt < 600.0:  # ignore prolonged pause gaps
                    energy_wh += 0.5 * (p_data[k] + p_data[k-1]) * dt / 3600.0

            self.lbl_hist_stats.setText(
                f"Duration: {dur:.1f} s  |  Peak V: {v_max:.2f} V  |  Peak I: {i_max:.3f} A  |  Peak P: {p_max:.1f} W  |  Energy: {energy_wh:.2f} Wh"
            )

            self._render_historical_plot()
            self.status_bar.showMessage(f"Loaded {len(t_data):,} samples from {Path(filepath).name}")

        except Exception as e:
            QMessageBox.critical(self, "CSV Loading Error", f"Error loading CSV data:\n{e}")

    def _render_historical_plot(self):
        if not self.hist_t:
            return

        lw = float(self.plot_settings.get("line_width", 2.0))
        show_x = ("X" in self.plot_settings.get("grid_style", "Both X & Y")) or ("Both" in self.plot_settings.get("grid_style", "Both X & Y"))
        show_y = ("Y" in self.plot_settings.get("grid_style", "Both X & Y")) or ("Both" in self.plot_settings.get("grid_style", "Both X & Y"))
        show_title = self.plot_settings.get("show_title", True)
        title_text = self.plot_settings.get("title", "")
        title_align = self.plot_settings.get("title_align", "Center").lower()
        x_lbl = self.plot_settings.get("x_label", "Elapsed Time")
        x_unit = self.plot_settings.get("x_unit", "s")
        y_lbl = self.plot_settings.get("y_label", "Magnitude")
        y_unit = self.plot_settings.get("y_unit", "")
        show_leg = self.plot_settings.get("show_legend", True)
        leg_loc = self.plot_settings.get("legend_loc", "Top-Right")

        if HAVE_PYQTGRAPH:
            self.hist_plot_widget.showGrid(x=show_x, y=show_y, alpha=0.15)

            # Title
            if show_title and title_text:
                title_col = "#e2e8f0" if self.current_theme == "dark" else "#0f172a"
                self.hist_plot_widget.setTitle(title_text, color=title_col, size="11pt", justify=title_align)
            else:
                self.hist_plot_widget.setTitle(None)

            # Axis Labels
            self.hist_plot_widget.setLabel('bottom', x_lbl, units=x_unit if x_unit else None)
            self.hist_plot_widget.setLabel('left', y_lbl, units=y_unit if y_unit else None)

            # Auto-legend resolution if requested
            if leg_loc == "Auto (Lowest Density)" and self.hist_t:
                active_dict = {}
                if self.chk_hist_v.isChecked(): active_dict['v'] = self.hist_v
                if self.chk_hist_i.isChecked(): active_dict['i'] = self.hist_i
                if self.chk_hist_p.isChecked(): active_dict['p'] = self.hist_p
                if self.chk_hist_r.isChecked(): active_dict['r'] = self.hist_r
                _, pg_pos = calculate_lowest_density_quadrant(self.hist_t, active_dict)
                leg_loc = pg_pos

            # Legend Placement
            if hasattr(self, 'hist_legend') and self.hist_legend is not None:
                if (not show_leg) or (leg_loc == "Hidden"):
                    self.hist_legend.setVisible(False)
                else:
                    self.hist_legend.setVisible(True)
                    try:
                        if leg_loc == "Top-Left":
                            self.hist_legend.anchor(itemPos=(0, 0), parentPos=(0, 0), offset=(15, 15))
                        elif leg_loc == "Bottom-Right":
                            self.hist_legend.anchor(itemPos=(1, 1), parentPos=(1, 1), offset=(-15, -15))
                        elif leg_loc == "Bottom-Left":
                            self.hist_legend.anchor(itemPos=(0, 1), parentPos=(0, 1), offset=(15, -15))
                        elif leg_loc == "Top-Center":
                            self.hist_legend.anchor(itemPos=(0.5, 0), parentPos=(0.5, 0), offset=(0, 15))
                        elif leg_loc == "Bottom-Center":
                            self.hist_legend.anchor(itemPos=(0.5, 1), parentPos=(0.5, 1), offset=(0, -15))
                        else:  # Top-Right
                            self.hist_legend.anchor(itemPos=(1, 0), parentPos=(1, 0), offset=(-15, 15))
                    except Exception:
                        pass

            # Update trace pen widths, markers, and line styles
            plot_style = self.plot_settings.get("plot_style", "Continuous: Solid Line (Default)")
            marker_size = int(self.plot_settings.get("marker_size", 6))
            is_dark = (self.current_theme == "dark")
            col_v = "#38bdf8" if is_dark else "#0284c7"
            col_i = "#4ade80" if is_dark else "#16a34a"
            col_p = "#fbbf24" if is_dark else "#d97706"
            col_r = "#c084fc" if is_dark else "#9333ea"

            apply_pyqtgraph_curve_style(self.hist_curve_v, col_v, lw, plot_style, marker_size)
            apply_pyqtgraph_curve_style(self.hist_curve_i, col_i, lw, plot_style, marker_size)
            apply_pyqtgraph_curve_style(self.hist_curve_p, col_p, lw, plot_style, marker_size)
            apply_pyqtgraph_curve_style(self.hist_curve_r, col_r, lw, plot_style, marker_size)

            _, _, _, is_step = parse_plot_style(plot_style)
            has_multiple_points = len(self.hist_t) > 1

            def _step_data(t_data, y_data):
                if is_step and has_multiple_points:
                    t_step = np.repeat(t_data, 2)[1:]
                    y_step = np.repeat(y_data, 2)[:-1]
                    return t_step, y_step
                return t_data, y_data

            if self.chk_hist_v.isChecked() and self.hist_v:
                t_plot, v_plot = _step_data(self.hist_t, self.hist_v)
                self.hist_curve_v.setData(t_plot, v_plot)
            else:
                self.hist_curve_v.clear()

            if self.chk_hist_i.isChecked() and self.hist_i:
                t_plot, i_plot = _step_data(self.hist_t, self.hist_i)
                self.hist_curve_i.setData(t_plot, i_plot)
            else:
                self.hist_curve_i.clear()

            if self.chk_hist_p.isChecked() and self.hist_p:
                t_plot, p_plot = _step_data(self.hist_t, self.hist_p)
                self.hist_curve_p.setData(t_plot, p_plot)
            else:
                self.hist_curve_p.clear()

            if self.chk_hist_r.isChecked() and self.hist_r:
                r_clean = [r if (r is not None and not math.isinf(r) and not math.isnan(r) and r < 1e6) else 0.0 for r in self.hist_r]
                t_plot, r_plot = _step_data(self.hist_t, r_clean)
                self.hist_curve_r.setData(t_plot, r_plot)
            else:
                self.hist_curve_r.clear()

            if self.plot_settings.get("auto_limits_percentile"):
                active_dict = {}
                if self.chk_hist_v.isChecked() and self.hist_v: active_dict['v'] = self.hist_v
                if self.chk_hist_i.isChecked() and self.hist_i: active_dict['i'] = self.hist_i
                if self.chk_hist_p.isChecked() and self.hist_p: active_dict['p'] = self.hist_p
                if self.chk_hist_r.isChecked() and self.hist_r: active_dict['r'] = self.hist_r
                lims = calculate_percentile_limits(active_dict)
                if lims:
                    self.hist_plot_widget.setYRange(lims[0], lims[1])
                else:
                    self.hist_plot_widget.autoRange()
            else:
                self.hist_plot_widget.autoRange()
        else:
            self.hist_mpl_ax.clear()
            is_dark = (self.current_theme == "dark")
            ax_bg = "#171922" if is_dark else "#ffffff"
            fg_col = "#94a3b8" if is_dark else "#0f172a"
            grid_col = "#282c37" if is_dark else "#e2e8f0"
            col_v = "#38bdf8" if is_dark else "#0284c7"
            col_i = "#4ade80" if is_dark else "#16a34a"
            col_p = "#fbbf24" if is_dark else "#d97706"
            col_r = "#c084fc" if is_dark else "#9333ea"
            plot_style = self.plot_settings.get("plot_style", "Continuous: Solid Line (Default)")
            marker_size = int(self.plot_settings.get("marker_size", 6))

            kw_v = get_matplotlib_plot_kwargs(col_v, lw, plot_style, marker_size)
            kw_i = get_matplotlib_plot_kwargs(col_i, lw, plot_style, marker_size)
            kw_p = get_matplotlib_plot_kwargs(col_p, lw, plot_style, marker_size)
            kw_r = get_matplotlib_plot_kwargs(col_r, lw, plot_style, marker_size)

            self.hist_mpl_ax.set_facecolor(ax_bg)
            self.hist_mpl_ax.tick_params(colors=fg_col)

            if show_x or show_y:
                self.hist_mpl_ax.grid(True, linestyle="--", alpha=0.3, color=grid_col)

            if show_title and title_text:
                self.hist_mpl_ax.set_title(title_text, loc=title_align, color=fg_col, fontsize=11, fontweight="bold")

            x_full = f"{x_lbl} ({x_unit})" if x_unit else x_lbl
            y_full = f"{y_lbl} ({y_unit})" if y_unit else y_lbl
            self.hist_mpl_ax.set_xlabel(x_full, color=fg_col)
            self.hist_mpl_ax.set_ylabel(y_full, color=fg_col)

            if self.chk_hist_v.isChecked() and self.hist_v:
                self.hist_mpl_ax.plot(self.hist_t, self.hist_v, label="Voltage (V)", **kw_v)
            if self.chk_hist_i.isChecked() and self.hist_i:
                self.hist_mpl_ax.plot(self.hist_t, self.hist_i, label="Current (A)", **kw_i)
            if self.chk_hist_p.isChecked() and self.hist_p:
                self.hist_mpl_ax.plot(self.hist_t, self.hist_p, label="Power (W)", **kw_p)
            if self.chk_hist_r.isChecked() and self.hist_r:
                r_clean = [r if (r is not None and not math.isinf(r) and not math.isnan(r) and r < 1e6) else 0.0 for r in self.hist_r]
                self.hist_mpl_ax.plot(self.hist_t, r_clean, label="Resistance (Ω)", **kw_r)

            if show_leg and leg_loc != "Hidden":
                mpl_map = {
                    "Top-Right": "upper right", "Top-Left": "upper left",
                    "Bottom-Right": "lower right", "Bottom-Left": "lower left",
                    "Top-Center": "upper center", "Bottom-Center": "lower center",
                }
                mpl_loc = mpl_map.get(leg_loc, "upper right")
                leg_bg = "#181a1f" if is_dark else "#ffffff"
                leg_edge = "#272a31" if is_dark else "#cbd5e1"
                self.hist_mpl_ax.legend(loc=mpl_loc, facecolor=leg_bg, edgecolor=leg_edge, labelcolor=fg_col)

            self.hist_mpl_canvas.draw_idle()

    def _refresh_hist_plot_visibility(self):
        self._render_historical_plot()

    def _hist_plot_autorange(self):
        if HAVE_PYQTGRAPH:
            self.hist_plot_widget.autoRange()

    def _on_hist_plot_mouse_moved(self, pos):
        if not HAVE_PYQTGRAPH or not self.hist_t:
            return
        if self.hist_plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = self.hist_plot_widget.plotItem.vb.mapSceneToView(pos)
            x = mouse_point.x()
            y = mouse_point.y()
            self.hist_v_line.setPos(x)
            self.hist_h_line.setPos(y)

            idx = np.searchsorted(self.hist_t, x)
            idx = max(0, min(idx, len(self.hist_t) - 1))
            t_val = self.hist_t[idx]
            v_val = self.hist_v[idx] if idx < len(self.hist_v) else 0.0
            i_val = self.hist_i[idx] if idx < len(self.hist_i) else 0.0
            p_val = self.hist_p[idx] if idx < len(self.hist_p) else 0.0
            r_val = self.hist_r[idx] if idx < len(self.hist_r) else 0.0
            r_str = f"{r_val:.2f} Ω" if (r_val and not math.isinf(r_val) and not math.isnan(r_val)) else "OPEN"

            self.lbl_hist_hud.setText(
                f"HUD Cursor @ {t_val:6.2f}s  |  Voltage: {v_val:6.2f} V  |  Current: {i_val:6.4f} A  |  Power: {p_val:6.1f} W  |  Load: {r_str}"
            )

    # -------------------------------------------------------------------------
    # PLOT PRESENTATION & THEME MANAGEMENT
    # -------------------------------------------------------------------------
    def _open_plot_settings_dialog(self):
        """Open the presentation & export customization dialog."""
        dlg = PlotPresentationDialog(self.plot_settings, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.plot_settings.update(dlg.get_settings())
            self._apply_plot_settings()
            self.status_bar.showMessage("Chart presentation & export settings updated.")

    def _apply_plot_settings(self):
        """Propagate current presentation preferences across both active plots."""
        lw = float(self.plot_settings.get("line_width", 2.0))
        show_x = ("X" in self.plot_settings.get("grid_style", "Both X & Y")) or ("Both" in self.plot_settings.get("grid_style", "Both X & Y"))
        show_y = ("Y" in self.plot_settings.get("grid_style", "Both X & Y")) or ("Both" in self.plot_settings.get("grid_style", "Both X & Y"))
        show_leg = self.plot_settings.get("show_legend", True)
        leg_loc = self.plot_settings.get("legend_loc", "Top-Right")
        x_lbl = self.plot_settings.get("x_label", "Elapsed Time")
        x_unit = self.plot_settings.get("x_unit", "s")
        y_lbl = self.plot_settings.get("y_label", "Magnitude")
        y_unit = self.plot_settings.get("y_unit", "")

        # 1. Update Historical Plot
        self._render_historical_plot()

        # 2. Update Live Oscilloscope Plot
        if HAVE_PYQTGRAPH and hasattr(self, 'plot_widget'):
            self.plot_widget.showGrid(x=show_x, y=show_y, alpha=0.15)
            self.plot_widget.setLabel('bottom', x_lbl, units=x_unit if x_unit else None)
            self.plot_widget.setLabel('left', y_lbl, units=y_unit if y_unit else None)

            if leg_loc == "Auto (Lowest Density)" and self.history_t:
                active_dict = {}
                if self.chk_show_v.isChecked(): active_dict['v'] = self.history_v
                if self.chk_show_i.isChecked(): active_dict['i'] = self.history_i
                if self.chk_show_p.isChecked(): active_dict['p'] = self.history_p
                _, pg_pos = calculate_lowest_density_quadrant(self.history_t, active_dict)
                leg_loc = pg_pos

            if hasattr(self, 'live_legend') and self.live_legend is not None:
                if (not show_leg) or (leg_loc == "Hidden"):
                    self.live_legend.setVisible(False)
                else:
                    self.live_legend.setVisible(True)
                    try:
                        if leg_loc == "Top-Left":
                            self.live_legend.anchor(itemPos=(0, 0), parentPos=(0, 0), offset=(15, 15))
                        elif leg_loc == "Bottom-Right":
                            self.live_legend.anchor(itemPos=(1, 1), parentPos=(1, 1), offset=(-15, -15))
                        elif leg_loc == "Bottom-Left":
                            self.live_legend.anchor(itemPos=(0, 1), parentPos=(0, 1), offset=(15, -15))
                        elif leg_loc == "Top-Center":
                            self.live_legend.anchor(itemPos=(0.5, 0), parentPos=(0.5, 0), offset=(0, 15))
                        elif leg_loc == "Bottom-Center":
                            self.live_legend.anchor(itemPos=(0.5, 1), parentPos=(0.5, 1), offset=(0, -15))
                        else:
                            self.live_legend.anchor(itemPos=(1, 0), parentPos=(1, 0), offset=(-15, 15))
                    except Exception:
                        pass

            plot_style = self.plot_settings.get("plot_style", "Continuous: Solid Line (Default)")
            marker_size = int(self.plot_settings.get("marker_size", 6))
            is_dark = (self.current_theme == "dark")
            col_v = "#38bdf8" if is_dark else "#0284c7"
            col_i = "#4ade80" if is_dark else "#16a34a"
            col_p = "#fbbf24" if is_dark else "#d97706"

            if hasattr(self, 'curve_v'):
                apply_pyqtgraph_curve_style(self.curve_v, col_v, lw, plot_style, marker_size)
            if hasattr(self, 'curve_i'):
                apply_pyqtgraph_curve_style(self.curve_i, col_i, lw, plot_style, marker_size)
            if hasattr(self, 'curve_p'):
                apply_pyqtgraph_curve_style(self.curve_p, col_p, lw, plot_style, marker_size)

            if self.plot_settings.get("auto_limits_percentile") and self.history_t:
                active_dict = {}
                if self.chk_show_v.isChecked(): active_dict['v'] = self.history_v
                if self.chk_show_i.isChecked(): active_dict['i'] = self.history_i
                if self.chk_show_p.isChecked(): active_dict['p'] = self.history_p
                lims = calculate_percentile_limits(active_dict)
                if lims:
                    self.plot_widget.setYRange(lims[0], lims[1])

        self._save_settings()

    def _toggle_theme(self):
        """Toggle between Dark Mode and Light Mode."""
        new_theme = "light" if self.current_theme == "dark" else "dark"
        self._apply_theme(new_theme)

    def _apply_theme(self, theme_name: str):
        """Apply global Dark or Light theme across all controls, readouts, and plots."""
        self.current_theme = theme_name
        is_dark = (theme_name == "dark")

        if is_dark:
            self.setStyleSheet(MODERN_DARK_STYLESHEET)
            self.btn_theme_toggle.setText("☀️ Light Mode")
            if hasattr(self, 'header_card'):
                self.header_card.setStyleSheet("""
                    QFrame#header_card {
                        background-color: #16181d;
                        border: 1px solid #272a31;
                        border-radius: 8px;
                    }
                """)
            if hasattr(self, 'lbl_header_title'):
                self.lbl_header_title.setStyleSheet("font-size: 14pt; font-weight: 800; color: #38bdf8; letter-spacing: 0.5px;")
            if hasattr(self, 'lbl_header_sub'):
                self.lbl_header_sub.setStyleSheet("font-size: 8.5pt; color: #94a3b8;")
            if hasattr(self, 'lbl_hist_stats'):
                self.lbl_hist_stats.setStyleSheet("""
                    background-color: #121418;
                    border: 1px solid #232730;
                    border-radius: 4px;
                    color: #e2e8f0;
                    font-size: 8.5pt;
                    font-family: monospace;
                    padding: 5px 10px;
                    font-weight: 600;
                """)
            if hasattr(self, 'lbl_hist_hud'):
                self.lbl_hist_hud.setStyleSheet("""
                    background-color: #16181d;
                    border: 1px solid #272a31;
                    border-radius: 4px;
                    color: #38bdf8;
                    font-size: 8.5pt;
                    font-family: monospace;
                    padding: 4px 8px;
                    font-weight: 600;
                """)
        else:
            self.setStyleSheet(MODERN_LIGHT_STYLESHEET)
            self.btn_theme_toggle.setText("🌙 Dark Mode")
            if hasattr(self, 'header_card'):
                self.header_card.setStyleSheet("""
                    QFrame#header_card {
                        background-color: #ffffff;
                        border: 1px solid #e2e8f0;
                        border-radius: 8px;
                    }
                """)
            if hasattr(self, 'lbl_header_title'):
                self.lbl_header_title.setStyleSheet("font-size: 14pt; font-weight: 800; color: #0284c7; letter-spacing: 0.5px;")
            if hasattr(self, 'lbl_header_sub'):
                self.lbl_header_sub.setStyleSheet("font-size: 8.5pt; color: #64748b;")
            if hasattr(self, 'lbl_hist_stats'):
                self.lbl_hist_stats.setStyleSheet("""
                    background-color: #f1f5f9;
                    border: 1px solid #cbd5e1;
                    border-radius: 4px;
                    color: #0f172a;
                    font-size: 8.5pt;
                    font-family: monospace;
                    padding: 5px 10px;
                    font-weight: 600;
                """)
            if hasattr(self, 'lbl_hist_hud'):
                self.lbl_hist_hud.setStyleSheet("""
                    background-color: #f1f5f9;
                    border: 1px solid #cbd5e1;
                    border-radius: 4px;
                    color: #0284c7;
                    font-size: 8.5pt;
                    font-family: monospace;
                    padding: 4px 8px;
                    font-weight: 600;
                """)

        # Adapt Metric Cards
        for card in [getattr(self, 'card_volt', None), getattr(self, 'card_curr', None),
                     getattr(self, 'card_pow', None), getattr(self, 'card_res', None)]:
            if card is not None:
                card.set_theme(is_dark)

        # Adapt Canvas backgrounds & axis pens (Atmos & Media.io palette)
        if HAVE_PYQTGRAPH:
            bg_color = "#0f1117" if is_dark else "#ffffff"
            axis_pen = "#94a3b8" if is_dark else "#475569"
            for pw in [getattr(self, 'plot_widget', None), getattr(self, 'hist_plot_widget', None)]:
                if pw is not None:
                    pw.setBackground(bg_color)
                    pw.getAxis('bottom').setTextPen(axis_pen)
                    pw.getAxis('left').setTextPen(axis_pen)
                    pw.getAxis('bottom').setPen(axis_pen)
                    pw.getAxis('left').setPen(axis_pen)
        else:
            bg_col = "#0f1117" if is_dark else "#f8fafc"
            ax_bg = "#171922" if is_dark else "#ffffff"
            fg_col = "#94a3b8" if is_dark else "#0f172a"
            if hasattr(self, 'mpl_fig'):
                self.mpl_fig.patch.set_facecolor(bg_col)
                self.mpl_ax.set_facecolor(ax_bg)
                self.mpl_ax.tick_params(colors=fg_col)
                self.mpl_canvas.draw_idle()
            if hasattr(self, 'hist_mpl_fig'):
                self.hist_mpl_fig.patch.set_facecolor(bg_col)
                self.hist_mpl_ax.set_facecolor(ax_bg)
                self.hist_mpl_ax.tick_params(colors=fg_col)
                self.hist_mpl_canvas.draw_idle()

        self._apply_plot_settings()
        self._save_settings()
        self.status_bar.showMessage(f"Applied {'Dark' if is_dark else 'Light'} theme.")

    # -------------------------------------------------------------------------
    # MULTI-FORMAT EXPORT & PUBLICATION SUITE (PDF, PNG, JPEG, SVG, LaTeX TikZ)
    # -------------------------------------------------------------------------
    def _export_plot(self, default_title: str, default_name: str, plot_widget, data_dict: dict = None):
        """
        Universal multi-format export for both Live Oscilloscope Trend and Historical Session Waveforms.
        Supports PDF, PNG, JPEG, SVG, and LaTeX TikZ/pgfplots.
        Incorporates publication presets, smart auto-legend, percentile outlier suppression,
        transparent backgrounds, watermarks, and companion .meta JSON provenance.
        """
        filters = (
            "PDF Document (*.pdf);;"
            "PNG Image (*.png);;"
            "JPEG Image (*.jpg *.jpeg);;"
            "Scalable Vector Graphic (*.svg);;"
            "LaTeX TikZ / pgfplots (*.pgf *.tex);;"
            "All Files (*.*)"
        )
        default_path = str(Path.cwd() / default_name)
        filepath, selected_filter = QFileDialog.getSaveFileName(self, default_title, default_path, filters)
        if not filepath:
            return

        ext = Path(filepath).suffix.lower()
        if not ext:
            if "pdf" in selected_filter.lower():
                ext = ".pdf"
            elif "png" in selected_filter.lower():
                ext = ".png"
            elif "jpg" in selected_filter.lower() or "jpeg" in selected_filter.lower():
                ext = ".jpg"
            elif "svg" in selected_filter.lower():
                ext = ".svg"
            elif "pgf" in selected_filter.lower() or "tikz" in selected_filter.lower() or "tex" in selected_filter.lower():
                ext = ".pgf"
            else:
                ext = ".png"
            filepath += ext

        # Presentation configuration parameters
        title_text = self.plot_settings.get("title", default_title)
        show_title = self.plot_settings.get("show_title", True)
        title_align = self.plot_settings.get("title_align", "Center").lower()
        x_lbl = self.plot_settings.get("x_label", "Elapsed Time")
        x_unit = self.plot_settings.get("x_unit", "s")
        x_full = f"{x_lbl} ({x_unit})" if x_unit else x_lbl

        y_lbl = self.plot_settings.get("y_label", "Magnitude")
        y_unit = self.plot_settings.get("y_unit", "")
        y_full = f"{y_lbl} ({y_unit})" if y_unit else y_lbl

        show_legend = self.plot_settings.get("show_legend", True)
        legend_loc = self.plot_settings.get("legend_loc", "Top-Right")
        mpl_loc_map = {
            "Top-Right": "upper right", "Top-Left": "upper left",
            "Bottom-Right": "lower right", "Bottom-Left": "lower left",
            "Top-Center": "upper center", "Bottom-Center": "lower center",
        }

        # Auto-legend detection
        if legend_loc == "Auto (Lowest Density)" and data_dict and data_dict.get('t'):
            mpl_loc, _ = calculate_lowest_density_quadrant(data_dict.get('t', []), data_dict)
        else:
            mpl_loc = mpl_loc_map.get(legend_loc, "upper right")

        line_width = float(self.plot_settings.get("line_width", 2.0))
        plot_style = self.plot_settings.get("plot_style", "Continuous: Solid Line (Default)")
        marker_size = int(self.plot_settings.get("marker_size", 6))
        grid_style = self.plot_settings.get("grid_style", "Both X & Y")
        show_x_grid = ("X" in grid_style) or ("Both" in grid_style)
        show_y_grid = ("Y" in grid_style) or ("Both" in grid_style)
        export_dpi = int(self.plot_settings.get("export_dpi", 300))
        transparent_bg = bool(self.plot_settings.get("transparent_pdf", False)) and ext in [".pdf", ".png", ".svg"]
        show_watermark = bool(self.plot_settings.get("show_watermark", True))
        watermark_text = self.plot_settings.get("watermark_text", "ETPS LAB-HP 41000 Telemetry")
        auto_limits = bool(self.plot_settings.get("auto_limits_percentile", False))
        trace_order_pref = self.plot_settings.get("trace_order", ["Voltage (V)", "Current (A)", "Power (W)", "Resistance (Ω)"])

        # Determine color palette for export
        exp_theme_opt = self.plot_settings.get("export_theme", "Match Active GUI Theme")
        if exp_theme_opt == "Dark Mode (Slate)":
            is_export_dark = True
        elif exp_theme_opt == "Publication Clean Light (White)":
            is_export_dark = False
        else:
            is_export_dark = (self.current_theme == "dark")

        if is_export_dark:
            bg_fig = "#0f1117"
            bg_ax = "#171922"
            fg_text = "#f1f5f9"
            color_grid = "#282c37"
            col_v = "#38bdf8"
            col_i = "#4ade80"
            col_p = "#fbbf24"
            col_r = "#c084fc"
            bg_leg = "#171922"
            edge_leg = "#282c37"
        else:
            bg_fig = "#f8fafc"
            bg_ax = "#ffffff"
            fg_text = "#0f172a"
            color_grid = "#e2e8f0"
            col_v = "#0284c7"
            col_i = "#16a34a"
            col_p = "#d97706"
            col_r = "#9333ea"
            bg_leg = "#ffffff"
            edge_leg = "#e2e8f0"

        kw_v = get_matplotlib_plot_kwargs(col_v, line_width, plot_style, marker_size)
        kw_i = get_matplotlib_plot_kwargs(col_i, line_width, plot_style, marker_size)
        kw_p = get_matplotlib_plot_kwargs(col_p, line_width, plot_style, marker_size)
        kw_r = get_matplotlib_plot_kwargs(col_r, line_width, plot_style, marker_size)

        try:
            # 0. LaTeX TikZ / pgfplots Export
            if ext in [".pgf", ".tex"]:
                if not data_dict or not data_dict.get('t'):
                    raise ValueError("No numeric data points available for LaTeX TikZ export.")
                export_tikz_pgf(filepath, data_dict, self.plot_settings, is_export_dark)
                if self.plot_settings.get("export_companion_meta", True):
                    generate_companion_metadata(filepath, self.plot_settings, data_dict)
                self.status_bar.showMessage(f"LaTeX TikZ plot exported -> {Path(filepath).name}")
                QMessageBox.information(self, "Export Successful", f"LaTeX TikZ code successfully generated to:\n{filepath}\n\nInclude in LaTeX via: \\input{{{Path(filepath).name}}}")
                return

            def _plot_traces_ordered(ax_obj):
                t_arr = data_dict.get('t', [])
                for pref in trace_order_pref:
                    if "Voltage" in pref and 'v' in data_dict and data_dict['v']:
                        ax_obj.plot(t_arr, data_dict['v'], label="Voltage (V)", **kw_v)
                    elif "Current" in pref and 'i' in data_dict and data_dict['i']:
                        ax_obj.plot(t_arr, data_dict['i'], label="Current (A)", **kw_i)
                    elif "Power" in pref and 'p' in data_dict and data_dict['p']:
                        ax_obj.plot(t_arr, data_dict['p'], label="Power (W)", **kw_p)
                    elif "Resistance" in pref and 'r' in data_dict and data_dict['r']:
                        r_clean = [r if (r is not None and not math.isinf(r) and not math.isnan(r) and r < 1e6) else 0.0 for r in data_dict['r']]
                        ax_obj.plot(t_arr, r_clean, label="Resistance (Ω)", **kw_r)

                if auto_limits:
                    lims = calculate_percentile_limits(data_dict)
                    if lims:
                        ax_obj.set_ylim(lims[0], lims[1])

            # 1. PNG Raster Image (High-DPI rendering)
            if ext == ".png":
                exported = False
                if data_dict and data_dict.get('t'):
                    try:
                        import matplotlib.pyplot as plt
                        fig, ax = plt.subplots(figsize=(11, 6.5), facecolor=bg_fig if not transparent_bg else "none", dpi=export_dpi)
                        if transparent_bg:
                            fig.patch.set_alpha(0.0)
                            ax.patch.set_alpha(0.0)
                        else:
                            ax.set_facecolor(bg_ax)

                        ax.tick_params(colors=fg_text)
                        for spine in ax.spines.values():
                            spine.set_color(color_grid)

                        if show_x_grid or show_y_grid:
                            ax.grid(True, linestyle="--", alpha=0.35, color=color_grid)

                        _plot_traces_ordered(ax)

                        if show_title and title_text:
                            ax.set_title(title_text, loc=title_align, fontsize=12, fontweight="bold", color=fg_text)
                        ax.set_xlabel(x_full, fontsize=10, color=fg_text)
                        ax.set_ylabel(y_full, fontsize=10, color=fg_text)

                        if show_legend and legend_loc != "Hidden":
                            ax.legend(loc=mpl_loc, facecolor=bg_leg, edgecolor=edge_leg, labelcolor=fg_text)

                        if show_watermark and watermark_text:
                            fig.text(0.98, 0.012, watermark_text, fontsize=8, color=fg_text, alpha=0.55, ha="right", va="bottom")

                        fig.tight_layout()
                        save_kw = {"format": "png", "dpi": export_dpi}
                        if transparent_bg:
                            save_kw["transparent"] = True
                        else:
                            save_kw["facecolor"] = bg_fig
                        fig.savefig(filepath, **save_kw)
                        plt.close(fig)
                        exported = True
                    except Exception:
                        exported = False

                if not exported:
                    pixmap = plot_widget.grab()
                    ok = pixmap.save(filepath, "PNG")
                    if not ok:
                        raise RuntimeError("Failed to write PNG image file")

            # 2. JPEG Raster Image
            elif ext in [".jpg", ".jpeg"]:
                exported = False
                if data_dict and data_dict.get('t'):
                    try:
                        import matplotlib.pyplot as plt
                        fig, ax = plt.subplots(figsize=(11, 6.5), facecolor=bg_fig, dpi=export_dpi)
                        ax.set_facecolor(bg_ax)
                        ax.tick_params(colors=fg_text)
                        for spine in ax.spines.values():
                            spine.set_color(color_grid)

                        if show_x_grid or show_y_grid:
                            ax.grid(True, linestyle="--", alpha=0.35, color=color_grid)

                        _plot_traces_ordered(ax)

                        if show_title and title_text:
                            ax.set_title(title_text, loc=title_align, fontsize=12, fontweight="bold", color=fg_text)
                        ax.set_xlabel(x_full, fontsize=10, color=fg_text)
                        ax.set_ylabel(y_full, fontsize=10, color=fg_text)

                        if show_legend and legend_loc != "Hidden":
                            ax.legend(loc=mpl_loc, facecolor=bg_leg, edgecolor=edge_leg, labelcolor=fg_text)

                        if show_watermark and watermark_text:
                            fig.text(0.98, 0.012, watermark_text, fontsize=8, color=fg_text, alpha=0.55, ha="right", va="bottom")

                        fig.tight_layout()
                        fig.savefig(filepath, format="jpeg", dpi=export_dpi, facecolor=bg_fig)
                        plt.close(fig)
                        exported = True
                    except Exception:
                        exported = False

                if not exported:
                    pixmap = plot_widget.grab()
                    img = pixmap.toImage()
                    img_rgb = img.convertToFormat(QImage.Format.Format_RGB888)
                    ok = img_rgb.save(filepath, "JPEG", 95)
                    if not ok:
                        raise RuntimeError("Failed to write JPEG image file")

            # 3. SVG Vector Graphic
            elif ext == ".svg":
                exported = False
                if data_dict and data_dict.get('t'):
                    try:
                        import matplotlib.pyplot as plt
                        fig, ax = plt.subplots(figsize=(10.5, 6), facecolor=bg_fig if not transparent_bg else "none")
                        if transparent_bg:
                            fig.patch.set_alpha(0.0)
                            ax.patch.set_alpha(0.0)
                        else:
                            ax.set_facecolor(bg_ax)

                        ax.tick_params(colors=fg_text)
                        for spine in ax.spines.values():
                            spine.set_color(color_grid)

                        if show_x_grid or show_y_grid:
                            ax.grid(True, linestyle="--", alpha=0.35, color=color_grid)

                        _plot_traces_ordered(ax)

                        if show_title and title_text:
                            ax.set_title(title_text, loc=title_align, fontsize=12, fontweight="bold", color=fg_text)
                        ax.set_xlabel(x_full, fontsize=10, color=fg_text)
                        ax.set_ylabel(y_full, fontsize=10, color=fg_text)

                        if show_legend and legend_loc != "Hidden":
                            ax.legend(loc=mpl_loc, facecolor=bg_leg, edgecolor=edge_leg, labelcolor=fg_text)

                        if show_watermark and watermark_text:
                            fig.text(0.98, 0.012, watermark_text, fontsize=8, color=fg_text, alpha=0.55, ha="right", va="bottom")

                        fig.tight_layout()
                        save_kw = {"format": "svg"}
                        if transparent_bg:
                            save_kw["transparent"] = True
                        else:
                            save_kw["facecolor"] = bg_fig
                        fig.savefig(filepath, **save_kw)
                        plt.close(fig)
                        exported = True
                    except Exception:
                        exported = False

                if not exported and HAVE_PYQTGRAPH and hasattr(plot_widget, 'plotItem'):
                    try:
                        import pyqtgraph.exporters
                        exp = pyqtgraph.exporters.SVGExporter(plot_widget.plotItem)
                        exp.export(filepath)
                        exported = True
                    except Exception:
                        exported = False

                if not exported and QSvgGenerator is not None:
                    try:
                        gen = QSvgGenerator()
                        gen.setFileName(filepath)
                        gen.setSize(plot_widget.size())
                        gen.setViewBox(plot_widget.rect())
                        gen.setTitle(title_text)
                        painter = QPainter(gen)
                        plot_widget.render(painter)
                        painter.end()
                        exported = True
                    except Exception:
                        exported = False

                if not exported:
                    raise RuntimeError("SVG export is not supported by current system libraries.")

            # 4. PDF Vector Document
            elif ext == ".pdf":
                exported = False
                if data_dict and data_dict.get('t'):
                    try:
                        import matplotlib.pyplot as plt
                        fig, ax = plt.subplots(figsize=(11, 7), facecolor=bg_fig if not transparent_bg else "none", dpi=export_dpi)
                        if transparent_bg:
                            fig.patch.set_alpha(0.0)
                            ax.patch.set_alpha(0.0)
                        else:
                            ax.set_facecolor(bg_ax)

                        ax.tick_params(colors=fg_text)
                        for spine in ax.spines.values():
                            spine.set_color(color_grid)

                        if show_x_grid or show_y_grid:
                            ax.grid(True, linestyle="--", alpha=0.4, color=color_grid)

                        _plot_traces_ordered(ax)

                        if show_title and title_text:
                            ax.set_title(title_text, loc=title_align, fontsize=13, fontweight="bold", color=fg_text)
                        ax.set_xlabel(x_full, fontsize=11, color=fg_text)
                        ax.set_ylabel(y_full, fontsize=11, color=fg_text)

                        if show_legend and legend_loc != "Hidden":
                            ax.legend(loc=mpl_loc, facecolor=bg_leg, edgecolor=edge_leg, labelcolor=fg_text)

                        if show_watermark and watermark_text:
                            fig.text(0.98, 0.012, watermark_text, fontsize=8, color=fg_text, alpha=0.55, ha="right", va="bottom")

                        fig.tight_layout()
                        save_kw = {"format": "pdf", "dpi": export_dpi}
                        if transparent_bg:
                            save_kw["transparent"] = True
                        else:
                            save_kw["facecolor"] = bg_fig
                        fig.savefig(filepath, **save_kw)
                        plt.close(fig)
                        exported = True
                    except Exception:
                        exported = False

                if not exported:
                    writer = QPdfWriter(filepath)
                    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
                    writer.setPageOrientation(QPageLayout.Orientation.Landscape)
                    writer.setResolution(export_dpi)
                    painter = QPainter(writer)
                    pixmap = plot_widget.grab()
                    viewport = painter.viewport()
                    scaled = pixmap.scaled(viewport.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    x = (viewport.width() - scaled.width()) // 2
                    y = (viewport.height() - scaled.height()) // 2
                    painter.drawPixmap(x, y, scaled)
                    painter.end()
                    exported = True

            # Generate companion .meta file if requested
            if self.plot_settings.get("export_companion_meta", True) and data_dict:
                try:
                    generate_companion_metadata(filepath, self.plot_settings, data_dict)
                except Exception as meta_err:
                    logger.warning(f"Failed to generate companion .meta file: {meta_err}")

            self.status_bar.showMessage(f"Plot exported successfully -> {Path(filepath).name}")
            QMessageBox.information(self, "Export Successful", f"Plot successfully saved to:\n{filepath}")

        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to export plot:\n{e}")

    def _export_live_plot(self):
        data = {
            't': list(self.history_t),
            'v': list(self.history_v) if self.chk_show_v.isChecked() else [],
            'i': list(self.history_i) if self.chk_show_i.isChecked() else [],
            'p': list(self.history_p) if self.chk_show_p.isChecked() else [],
        }
        widget = self.plot_widget if HAVE_PYQTGRAPH else self.mpl_canvas
        default_name = f"labhp_live_oscilloscope_{datetime.date.today().strftime('%Y%m%d_%H%M%S')}.png"
        self._export_plot("Live Oscilloscope Trend Plot", default_name, widget, data)

    def _export_historical_plot(self):
        if not self.hist_t:
            QMessageBox.information(
                self, "No Historical Data",
                "No session data is currently loaded to export.\nLoad a CSV file or complete a logging session first."
            )
            return
        data = {
            't': self.hist_t,
            'v': self.hist_v if self.chk_hist_v.isChecked() else [],
            'i': self.hist_i if self.chk_hist_i.isChecked() else [],
            'p': self.hist_p if self.chk_hist_p.isChecked() else [],
            'r': self.hist_r if self.chk_hist_r.isChecked() else [],
        }
        widget = self.hist_plot_widget if HAVE_PYQTGRAPH else self.hist_mpl_canvas
        stem = Path(self.current_loaded_csv).stem if self.current_loaded_csv else "session"
        default_name = f"{stem}_analytics_{datetime.date.today().strftime('%Y%m%d')}.png"
        self._export_plot("Historical Session Analytics Plot", default_name, widget, data)

    def _batch_export_live(self):
        data = {
            't': list(self.history_t),
            'v': list(self.history_v) if self.chk_show_v.isChecked() else [],
            'i': list(self.history_i) if self.chk_show_i.isChecked() else [],
            'p': list(self.history_p) if self.chk_show_p.isChecked() else [],
        }
        default_prefix = f"labhp_live_batch_{datetime.date.today().strftime('%Y%m%d_%H%M%S')}"
        self._run_batch_export(default_prefix, data, is_live=True)

    def _batch_export_historical(self):
        if not self.hist_t:
            QMessageBox.information(
                self, "No Historical Data",
                "No session data is currently loaded to export.\nLoad a CSV file or complete a logging session first."
            )
            return
        data = {
            't': self.hist_t,
            'v': self.hist_v if self.chk_hist_v.isChecked() else [],
            'i': self.hist_i if self.chk_hist_i.isChecked() else [],
            'p': self.hist_p if self.chk_hist_p.isChecked() else [],
            'r': self.hist_r if self.chk_hist_r.isChecked() else [],
        }
        stem = Path(self.current_loaded_csv).stem if self.current_loaded_csv else "session"
        default_prefix = f"{stem}_pub_batch_{datetime.date.today().strftime('%Y%m%d')}"
        self._run_batch_export(default_prefix, data, is_live=False)

    def _run_batch_export(self, default_prefix: str, data_dict: dict, is_live: bool = False):
        t = data_dict.get('t', [])
        if not t:
            QMessageBox.warning(self, "No Data", "No data points available for batch export.")
            return

        active_channels = []
        ch_meta = [
            ('v', "Voltage (V)", "Voltage", "V", "#38bdf8", "#0284c7"),
            ('i', "Current (A)", "Current", "A", "#4ade80", "#16a34a"),
            ('p', "Power (W)", "Power", "W", "#fbbf24", "#d97706"),
            ('r', "Resistance (Ω)", "Resistance", "Ω", "#c084fc", "#9333ea"),
        ]
        for k, label, name, unit, col_dark, col_light in ch_meta:
            if k in data_dict and data_dict[k]:
                active_channels.append((k, label, name, unit, col_dark, col_light))

        if not active_channels:
            QMessageBox.warning(self, "No Active Traces", "No channels are currently active to export.")
            return

        dlg = BatchExportDialog(self, default_prefix)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        opts = dlg.get_options()
        out_dir = Path(opts["dir"])
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "Directory Error", f"Cannot access export directory:\n{e}")
            return

        prefix = opts["prefix"] or "export"
        ext = opts["ext"]
        dpi = opts["dpi"]
        multipanel = opts["multipanel"]
        is_dark = (opts["theme"] == "Dark Mode (Slate)") or (opts["theme"] == "Match Active GUI Theme" and self.current_theme == "dark")
        gen_meta = opts["generate_meta"]
        watermark = opts["watermark"]
        transparent = opts["transparent"]
        watermark_text = self.plot_settings.get("watermark_text", "ETPS LAB-HP 41000 Telemetry")
        lw = float(self.plot_settings.get("line_width", 2.0))
        plot_style = self.plot_settings.get("plot_style", "Continuous: Solid Line (Default)")
        marker_size = int(self.plot_settings.get("marker_size", 6))

        bg_fig = "none" if transparent else ("#0f1117" if is_dark else "#f8fafc")
        bg_ax = "none" if transparent else ("#171922" if is_dark else "#ffffff")
        fg_text = "#f1f5f9" if is_dark else "#0f172a"
        color_grid = "#282c37" if is_dark else "#e2e8f0"

        exported_files = []

        try:
            import matplotlib.pyplot as plt

            if ext == ".pgf":
                if multipanel:
                    out_path = str(out_dir / f"{prefix}_multipanel.pgf")
                    export_tikz_pgf(out_path, data_dict, self.plot_settings, is_dark)
                    exported_files.append(out_path)
                else:
                    for k, label, name, unit, _, _ in active_channels:
                        sub_data = {'t': t, k: data_dict[k]}
                        out_path = str(out_dir / f"{prefix}_{name.lower()}.pgf")
                        export_tikz_pgf(out_path, sub_data, self.plot_settings, is_dark)
                        exported_files.append(out_path)
            else:
                if multipanel:
                    n_panels = len(active_channels)
                    fig, axes = plt.subplots(
                        nrows=n_panels, ncols=1,
                        figsize=(11, 2.6 * n_panels + 1.2),
                        sharex=True,
                        facecolor=bg_fig if not transparent else "none",
                        dpi=dpi
                    )
                    if n_panels == 1:
                        axes = [axes]

                    if transparent:
                        fig.patch.set_alpha(0.0)

                    title_str = self.plot_settings.get("title", "LAB-HP 41000 Session Telemetry")
                    if self.plot_settings.get("show_title", True) and title_str:
                        fig.suptitle(title_str, fontsize=13, fontweight="bold", color=fg_text)

                    for idx, (k, label, name, unit, col_dark, col_light) in enumerate(active_channels):
                        ax = axes[idx]
                        col = col_dark if is_dark else col_light
                        kw = get_matplotlib_plot_kwargs(col, lw, plot_style, marker_size)
                        ax.set_facecolor(bg_ax if not transparent else "none")
                        if transparent:
                            ax.patch.set_alpha(0.0)
                        ax.tick_params(colors=fg_text)
                        for spine in ax.spines.values():
                            spine.set_color(color_grid)
                        ax.grid(True, linestyle="--", alpha=0.35, color=color_grid)

                        y_vals = data_dict[k]
                        if k == 'r':
                            y_vals = [r if (r is not None and not math.isinf(r) and not math.isnan(r) and r < 1e6) else 0.0 for r in y_vals]
                        ax.plot(t, y_vals, label=label, **kw)
                        ax.set_ylabel(f"{name} ({unit})", fontsize=10, color=fg_text)

                        if self.plot_settings.get("auto_limits_percentile"):
                            lims = calculate_percentile_limits({k: y_vals})
                            if lims:
                                ax.set_ylim(lims[0], lims[1])

                    axes[-1].set_xlabel(f"{self.plot_settings.get('x_label', 'Elapsed Time')} ({self.plot_settings.get('x_unit', 's')})", fontsize=10, color=fg_text)

                    if watermark and watermark_text:
                        fig.text(0.98, 0.012, watermark_text, fontsize=8, color=fg_text, alpha=0.55, ha="right", va="bottom")

                    fig.tight_layout()
                    out_path = str(out_dir / f"{prefix}_multipanel{ext}")
                    save_kwargs = {"dpi": dpi}
                    if transparent:
                        save_kwargs["transparent"] = True
                    else:
                        save_kwargs["facecolor"] = bg_fig
                    fig.savefig(out_path, **save_kwargs)
                    plt.close(fig)
                    exported_files.append(out_path)

                else:
                    for k, label, name, unit, col_dark, col_light in active_channels:
                        fig, ax = plt.subplots(figsize=(10, 5.5), facecolor=bg_fig if not transparent else "none", dpi=dpi)
                        if transparent:
                            fig.patch.set_alpha(0.0)
                            ax.patch.set_alpha(0.0)
                        col = col_dark if is_dark else col_light
                        kw = get_matplotlib_plot_kwargs(col, lw, plot_style, marker_size)
                        ax.set_facecolor(bg_ax if not transparent else "none")
                        ax.tick_params(colors=fg_text)
                        for spine in ax.spines.values():
                            spine.set_color(color_grid)
                        ax.grid(True, linestyle="--", alpha=0.35, color=color_grid)

                        y_vals = data_dict[k]
                        if k == 'r':
                            y_vals = [r if (r is not None and not math.isinf(r) and not math.isnan(r) and r < 1e6) else 0.0 for r in y_vals]
                        ax.plot(t, y_vals, label=label, **kw)
                        ax.set_title(f"{name} vs Time", fontsize=11, fontweight="bold", color=fg_text)
                        ax.set_xlabel(f"{self.plot_settings.get('x_label', 'Elapsed Time')} ({self.plot_settings.get('x_unit', 's')})", fontsize=10, color=fg_text)
                        ax.set_ylabel(f"{name} ({unit})", fontsize=10, color=fg_text)

                        if self.plot_settings.get("auto_limits_percentile"):
                            lims = calculate_percentile_limits({k: y_vals})
                            if lims:
                                ax.set_ylim(lims[0], lims[1])

                        if watermark and watermark_text:
                            fig.text(0.98, 0.015, watermark_text, fontsize=8, color=fg_text, alpha=0.55, ha="right", va="bottom")

                        fig.tight_layout()
                        out_path = str(out_dir / f"{prefix}_{name.lower()}{ext}")
                        save_kwargs = {"dpi": dpi}
                        if transparent:
                            save_kwargs["transparent"] = True
                        else:
                            save_kwargs["facecolor"] = bg_fig
                        fig.savefig(out_path, **save_kwargs)
                        plt.close(fig)
                        exported_files.append(out_path)

            if gen_meta:
                meta_path = generate_companion_metadata(str(out_dir / f"{prefix}.meta"), self.plot_settings, data_dict)
                exported_files.append(meta_path)

            self.status_bar.showMessage(f"Batch export completed: {len(exported_files)} file(s) generated.")
            file_list_str = "\n".join([f"• {Path(f).name}" for f in exported_files])
            QMessageBox.information(self, "Batch Export Successful", f"Successfully exported {len(exported_files)} file(s) to:\n{out_dir}\n\nFiles:\n{file_list_str}")

        except Exception as e:
            QMessageBox.critical(self, "Batch Export Failed", f"An error occurred during batch export:\n{e}")

    def _toggle_publication_mode(self):
        """Toggles Publication Mode: freezes style and prevents live auto-range jitter."""
        self.publication_mode = not getattr(self, "publication_mode", False)
        is_active = self.publication_mode

        if hasattr(self, 'btn_pub_mode_live'):
            self.btn_pub_mode_live.setChecked(is_active)
            if is_active:
                self.btn_pub_mode_live.setText("📌 Pub Mode (ON)")
                self.btn_pub_mode_live.setStyleSheet("color: #4ade80; font-weight: bold; border: 1px solid #16a34a;")
            else:
                self.btn_pub_mode_live.setText("📌 Pub Mode")
                self.btn_pub_mode_live.setStyleSheet("")

        if hasattr(self, 'btn_pub_mode_hist'):
            self.btn_pub_mode_hist.setChecked(is_active)
            if is_active:
                self.btn_pub_mode_hist.setText("📌 Pub Mode (ON)")
                self.btn_pub_mode_hist.setStyleSheet("color: #4ade80; font-weight: bold; border: 1px solid #16a34a;")
            else:
                self.btn_pub_mode_hist.setText("📌 Pub Mode")
                self.btn_pub_mode_hist.setStyleSheet("")

        if is_active:
            self.status_bar.showMessage("Publication Mode ACTIVE: Live refresh frozen for steady inspection and publication export.")
        else:
            self.status_bar.showMessage("Publication Mode DEACTIVATED: Resumed live oscilloscope streaming.")
            if HAVE_PYQTGRAPH and hasattr(self, 'plot_widget'):
                if self.chk_show_v.isChecked(): self.curve_v.setData(self.history_t, self.history_v)
                if self.chk_show_i.isChecked(): self.curve_i.setData(self.history_t, self.history_i)
                if self.chk_show_p.isChecked(): self.curve_p.setData(self.history_t, self.history_p)

    # -------------------------------------------------------------------------
    # TERMINAL & SCANNER ACTIONS
    # -------------------------------------------------------------------------
    def _send_terminal_cmd(self, cmd: str):
        cmd = cmd.strip()
        if not cmd or not self.controller.connected:
            return
        try:
            query_cmds = {"ID", "IDN?", "MU", "MI", "UA", "IA", "PA", "OVP",
                          "STATUS", "MODE", "LIMU", "LIMI", "LIMP", "SB"}
            is_query = ("," not in cmd) and (cmd.upper() in query_cmds)
            t0 = time.perf_counter()
            if is_query:
                resp = self.controller._send(cmd, expect_response=True)
                dt = (time.perf_counter() - t0) * 1000.0
                self.term_log.append(f">>> {cmd}\n<<< {resp}  ({dt:.1f} ms)\n")
            else:
                self.controller._send(cmd)
                dt = (time.perf_counter() - t0) * 1000.0
                self.term_log.append(f">>> {cmd}  [Sent] ({dt:.1f} ms)\n")
            self.txt_term_cmd.clear()
        except Exception as e:
            self.term_log.append(f">>> {cmd}\n[ERROR]: {e}\n")

    def _start_network_scan(self):
        if self.scanner_thread and self.scanner_thread.isRunning():
            return
        self.btn_scan.setEnabled(False)
        self.status_bar.showMessage("Scanning local network on port 10001...")
        self.scanner_thread = FastNetworkScanner(port=self.spin_port.value())
        self.scanner_thread.device_found.connect(self._on_scanner_found)
        self.scanner_thread.scan_finished.connect(self._on_scanner_done)
        self.scanner_thread.start()

    def _on_scanner_found(self, ip: str, idn: str):
        items = [self.combo_ip.itemText(i) for i in range(self.combo_ip.count())]
        if ip not in items:
            self.combo_ip.addItem(ip)
        self.status_bar.showMessage(f"Discovered LAB-HP at {ip} ({idn})")

    def _on_scanner_done(self, results: list):
        self.btn_scan.setEnabled(True)
        self.status_bar.showMessage(f"Network scan finished. {len(results)} device(s) found.")

    # -------------------------------------------------------------------------
    # SETTINGS & LIFECYCLE
    # -------------------------------------------------------------------------
    def _save_settings(self):
        ip = self.combo_ip.currentText().strip()
        if ip:
            self.settings.setValue("last_ip", ip)
        self.settings.setValue("last_port", self.spin_port.value())
        self.settings.setValue("app_theme", self.current_theme)
        for k, v in self.plot_settings.items():
            self.settings.setValue(f"plot_{k}", v)

    def _load_saved_settings(self):
        last_ip = self.settings.value("last_ip", "192.168.1.100")
        self.combo_ip.setCurrentText(str(last_ip))
        last_port = self.settings.value("last_port", 10001, type=int)
        self.spin_port.setValue(last_port)

        saved_theme = self.settings.value("app_theme", "dark")
        self.plot_settings["title"] = str(self.settings.value("plot_title", self.plot_settings["title"]))
        self.plot_settings["show_title"] = self.settings.value("plot_show_title", True, type=bool)
        self.plot_settings["title_align"] = str(self.settings.value("plot_title_align", self.plot_settings["title_align"]))
        self.plot_settings["x_label"] = str(self.settings.value("plot_x_label", self.plot_settings["x_label"]))
        self.plot_settings["x_unit"] = str(self.settings.value("plot_x_unit", self.plot_settings["x_unit"]))
        self.plot_settings["y_label"] = str(self.settings.value("plot_y_label", self.plot_settings["y_label"]))
        self.plot_settings["y_unit"] = str(self.settings.value("plot_y_unit", self.plot_settings["y_unit"]))
        self.plot_settings["show_legend"] = self.settings.value("plot_show_legend", True, type=bool)
        self.plot_settings["legend_loc"] = str(self.settings.value("plot_legend_loc", self.plot_settings["legend_loc"]))
        self.plot_settings["plot_style"] = str(self.settings.value("plot_plot_style", self.plot_settings.get("plot_style", "Continuous: Solid Line (Default)")))
        self.plot_settings["marker_size"] = self.settings.value("plot_marker_size", self.plot_settings.get("marker_size", 6), type=int)
        self.plot_settings["line_width"] = self.settings.value("plot_line_width", 2.0, type=float)
        self.plot_settings["grid_style"] = str(self.settings.value("plot_grid_style", self.plot_settings["grid_style"]))
        self.plot_settings["export_theme"] = str(self.settings.value("plot_export_theme", self.plot_settings["export_theme"]))
        self.plot_settings["export_dpi"] = self.settings.value("plot_export_dpi", 300, type=int)

        self._apply_theme(saved_theme)

    def closeEvent(self, event):
        self._save_settings()
        self._disconnect()
        event.accept()


# =============================================================================
# ENTRY POINT
# =============================================================================
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("LABHPControllerV5")
    app.setStyle("Fusion")

    window = LABHPControllerV5()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
