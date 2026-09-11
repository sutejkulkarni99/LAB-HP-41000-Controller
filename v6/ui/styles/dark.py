"""MODERN_DARK_STYLESHEET — Polaris Dark Palette industrial stylesheet."""

MODERN_DARK_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #05070E;
    color: #E8ECF5;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 10pt;
}

/* Containers & Cards (Elevation Depth Level 1) */
QGroupBox {
    background-color: #0E1220;
    border: 1px solid #1B2238;
    border-radius: 8px;
    margin-top: 14px;
    padding: 14px 10px 10px 10px;
    font-weight: 600;
    font-size: 9.5pt;
    color: #8B94AD;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    background-color: #0E1220;
    border-radius: 3px;
    color: #F5E6C8;
}

/* Inputs & Spinboxes (Elevation Level 2) */
QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox, QListWidget {
    background-color: #05070E;
    border: 1px solid #1B2238;
    border-radius: 5px;
    padding: 5px 8px;
    color: #E8ECF5;
    font-size: 10pt;
    selection-background-color: #7DD3FC;
    selection-color: #05070E;
}

QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus, QListWidget:focus {
    border: 1px solid #7DD3FC;
    background-color: #121828;
}

QLineEdit:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled, QComboBox:disabled, QListWidget:disabled {
    background-color: #05070E;
    border-color: #1B2238;
    color: #8B94AD;
}

/* Modern Push Buttons */
QPushButton {
    background-color: #121828;
    border: 1px solid #1B2238;
    border-radius: 6px;
    padding: 6px 14px;
    color: #E8ECF5;
    font-weight: 600;
    font-size: 9.5pt;
}

QPushButton:hover {
    background-color: #1B2238;
    border-color: #2A3455;
    color: #FFFFFF;
}

QPushButton:pressed {
    background-color: #0E1220;
    border-color: #1B2238;
}

QPushButton:disabled {
    background-color: #05070E;
    border-color: #1B2238;
    color: #8B94AD;
}

/* Button Variants */
QPushButton#primary {
    background-color: #7DD3FC;
    border: 1px solid #7DD3FC;
    color: #05070E;
}
QPushButton#primary:hover {
    background-color: #BAE6FD;
    border-color: #7DD3FC;
}

QPushButton#success {
    background-color: #4ADE80;
    border: 1px solid #4ADE80;
    color: #05070E;
}
QPushButton#success:hover {
    background-color: #86EFAC;
    border-color: #4ADE80;
}

QPushButton#danger {
    background-color: #F87171;
    border: 1px solid #F87171;
    color: #05070E;
}
QPushButton#danger:hover {
    background-color: #FCA5A5;
    border-color: #F87171;
}

/* Tool Buttons */
QToolButton {
    background-color: #121828;
    border: 1px solid #1B2238;
    border-radius: 5px;
    padding: 5px;
    color: #E8ECF5;
}
QToolButton:hover {
    background-color: #1B2238;
    border-color: #2A3455;
}
QToolButton:pressed {
    background-color: #0E1220;
}
QToolButton:disabled {
    background-color: #05070E;
    border-color: #1B2238;
    color: #8B94AD;
}

/* Industrial E-Stop Button */
QPushButton#emergency {
    background-color: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
                                      stop:0 #F87171, stop:0.7 #991B1B, stop:1 #450A0A);
    border: 3px solid #F5E6C8;
    border-radius: 36px;
    font-size: 11pt;
    font-weight: 800;
    letter-spacing: 0.5px;
    color: #FFFFFF;
    padding: 0;
}
QPushButton#emergency:hover {
    background-color: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
                                      stop:0 #F87171, stop:0.7 #DC2626, stop:1 #7F1D1D);
    border-color: #F5E6C8;
}
QPushButton#emergency:disabled {
    background-color: #121828;
    border-color: #1B2238;
    color: #8B94AD;
}
QPushButton#emergency[latched="true"] {
    background-color: #450A0A;
    border: 3px solid #F87171;
    color: #FCA5A5;
}

/* Mode Switch Button */
QPushButton#mode_remote {
    background-color: #121828;
    border: 1px solid #7DD3FC;
    color: #7DD3FC;
    font-weight: bold;
    border-radius: 6px;
    padding: 6px 14px;
}
QPushButton#mode_remote:hover {
    background-color: #1B2238;
    border-color: #7DD3FC;
}

QPushButton#mode_local {
    background-color: #2A1A05;
    border: 1px solid #FBBF24;
    color: #FBBF24;
    font-weight: bold;
    border-radius: 6px;
    padding: 6px 14px;
}
QPushButton#mode_local:hover {
    background-color: #3F2908;
    border-color: #FBBF24;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #1B2238;
    background-color: #0E1220;
    border-radius: 6px;
    top: -1px;
}
QTabBar::tab {
    background-color: #05070E;
    border: 1px solid #1B2238;
    padding: 9px 20px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 600;
    color: #8B94AD;
}
QTabBar::tab:selected {
    background-color: #0E1220;
    border-bottom: 2px solid #7DD3FC;
    color: #7DD3FC;
}
QTabBar::tab:hover:!selected {
    background-color: #121828;
    color: #E8ECF5;
}

/* Text Terminal & Logs */
QTextEdit {
    background-color: #05070E;
    border: 1px solid #1B2238;
    border-radius: 6px;
    color: #E8ECF5;
    font-family: "JetBrains Mono", "SF Mono", "Consolas", "Courier New", monospace;
    font-size: 9pt;
    line-height: 1.4;
}

/* Checkboxes & Sliders */
QCheckBox {
    color: #E8ECF5;
    font-size: 9.5pt;
    spacing: 7px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #1B2238;
    background-color: #05070E;
}
QCheckBox::indicator:checked {
    background-color: #7DD3FC;
    border-color: #7DD3FC;
}

/* Status Bar */
QStatusBar {
    background-color: #0E1220;
    border-top: 1px solid #1B2238;
    color: #8B94AD;
    font-size: 9pt;
}

/* Sliders */
QSlider::groove:horizontal {
    height: 5px;
    background: #1B2238;
    border-radius: 2px;
}
QSlider::sub-page:horizontal {
    background: #7DD3FC;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #E8ECF5;
    border: 1px solid #8B94AD;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover {
    background: #FFFFFF;
    border-color: #7DD3FC;
}

/* Dialogs */
QDialog {
    background-color: #05070E;
    color: #E8ECF5;
}

/* Collapsible Section */
QWidget#collapsible_section {
    background-color: #0E1220;
    border: 1px solid #1B2238;
    border-radius: 8px;
}

QWidget#collapsible_header {
    background-color: #0E1220;
    border-radius: 8px;
}

QWidget#collapsible_header:hover {
    background-color: #121828;
}

QLabel#collapsible_title {
    font-weight: bold;
    color: #F5E6C8;
    font-size: 9.5pt;
}

QLabel#collapsible_status {
    color: #8B94AD;
    font-size: 8.5pt;
}
"""
