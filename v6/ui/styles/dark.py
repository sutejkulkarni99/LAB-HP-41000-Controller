"""MODERN_DARK_STYLESHEET — Slate Control dark industrial stylesheet (inherited verbatim from v5)."""

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
