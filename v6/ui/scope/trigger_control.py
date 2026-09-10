"""TriggerControlWidget — Oscilloscope trigger source, mode, edge slope, and level."""
try:
    from PyQt6.QtWidgets import (
        QGroupBox, QVBoxLayout, QGridLayout, QLabel,
        QComboBox, QDoubleSpinBox, QSlider
    )
    from PyQt6.QtCore import Qt, pyqtSignal
except ImportError:
    class QGroupBox:
        def __init__(self, title="", parent=None): pass
    class QVBoxLayout:
        def __init__(self, parent=None): pass
    class QGridLayout:
        def __init__(self, parent=None): pass
    class QLabel:
        def __init__(self, text=""): pass
    class QComboBox:
        def __init__(self, parent=None): pass
    class QDoubleSpinBox:
        def __init__(self, parent=None): pass
    class QSlider:
        def __init__(self, orientation, parent=None): pass
    def pyqtSignal(*args, **kwargs):
        class Sig:
            def connect(self, s): pass
            def emit(self, *a): pass
        return Sig()


class TriggerControlWidget(QGroupBox):
    """
    Oscilloscope edge trigger configuration card with live level adjustment,
    trigger source assignment, and mode switching (Auto / Normal / Single).
    """

    source_changed = pyqtSignal(str)
    level_changed = pyqtSignal(float)
    slope_changed = pyqtSignal(str)
    mode_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__("Edge Trigger System", parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)

        # Source
        grid.addWidget(QLabel("Source:"), 0, 0)
        self.combo_source = QComboBox()
        self.combo_source.addItems(["CH1", "CH2", "EXT"])
        self.combo_source.currentIndexChanged.connect(self._on_source_changed)
        grid.addWidget(self.combo_source, 0, 1)

        # Mode
        grid.addWidget(QLabel("Mode:"), 1, 0)
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["AUTO", "NORM", "SINGLE"])
        self.combo_mode.currentIndexChanged.connect(self._on_mode_changed)
        grid.addWidget(self.combo_mode, 1, 1)

        # Slope
        grid.addWidget(QLabel("Slope:"), 2, 0)
        self.combo_slope = QComboBox()
        self.combo_slope.addItems(["Rising (Positive / ↑)", "Falling (Negative / ↓)"])
        self.combo_slope.currentIndexChanged.connect(self._on_slope_changed)
        grid.addWidget(self.combo_slope, 2, 1)

        # Level
        grid.addWidget(QLabel("Level:"), 3, 0)
        self.spin_level = QDoubleSpinBox()
        self.spin_level.setRange(-50.0, 50.0)
        self.spin_level.setSingleStep(0.1)
        self.spin_level.setValue(0.5)
        self.spin_level.setSuffix(" V")
        self.spin_level.valueChanged.connect(self.level_changed.emit)
        grid.addWidget(self.spin_level, 3, 1)

        layout.addLayout(grid)

    def _on_source_changed(self, idx: int):
        self.source_changed.emit(self.combo_source.currentText())

    def _on_mode_changed(self, idx: int):
        self.mode_changed.emit(self.combo_mode.currentText())

    def _on_slope_changed(self, idx: int):
        slope = "POS" if "Rising" in self.combo_slope.currentText() else "NEG"
        self.slope_changed.emit(slope)

    def set_verified_level(self, level: float):
        self.spin_level.blockSignals(True)
        self.spin_level.setValue(level)
        self.spin_level.blockSignals(False)
