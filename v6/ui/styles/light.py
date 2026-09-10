"""MODERN_LIGHT_STYLESHEET — Clean Laboratory light stylesheet (inherited verbatim from v5)."""

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
