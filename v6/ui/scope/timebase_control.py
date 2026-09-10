"""TimebaseControlWidget — Horizontal deflection (time/div), acquisition RUN/STOP/SINGLE."""
try:
    from PyQt6.QtWidgets import (
        QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
        QComboBox, QDoubleSpinBox, QPushButton
    )
    from PyQt6.QtCore import pyqtSignal
except ImportError:
    class QGroupBox:
        def __init__(self, title="", parent=None): pass
    class QVBoxLayout:
        def __init__(self, parent=None): pass
    class QHBoxLayout:
        def __init__(self, parent=None): pass
    class QGridLayout:
        def __init__(self, parent=None): pass
    class QLabel:
        def __init__(self, text=""): pass
    class QComboBox:
        def __init__(self, parent=None): pass
    class QDoubleSpinBox:
        def __init__(self, parent=None): pass
    class QPushButton:
        def __init__(self, text=""): pass
    def pyqtSignal(*args, **kwargs):
        class Sig:
            def connect(self, s): pass
            def emit(self, *a): pass
        return Sig()


class TimebaseControlWidget(QGroupBox):
    """
    Horizontal timebase panel for configuring acquisition sampling rate,
    horizontal deflection scale, position offset, and trigger run/stop modes.
    """

    scale_changed = pyqtSignal(float)
    position_changed = pyqtSignal(float)
    run_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    single_requested = pyqtSignal()

    TIME_DIV_OPTIONS = [
        ("100 ns/div", 1e-7), ("500 ns/div", 5e-7),
        ("1 µs/div", 1e-6), ("5 µs/div", 5e-6), ("10 µs/div", 1e-5),
        ("50 µs/div", 5e-5), ("100 µs/div", 1e-4), ("500 µs/div", 5e-4),
        ("1 ms/div", 1e-3), ("2 ms/div", 2e-3), ("5 ms/div", 5e-3),
        ("10 ms/div", 1e-2), ("20 ms/div", 2e-2), ("50 ms/div", 5e-2),
        ("100 ms/div", 1e-1), ("500 ms/div", 5e-1), ("1 s/div", 1.0)
    ]

    def __init__(self, parent=None):
        super().__init__("Horizontal Timebase", parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Action Buttons: RUN / STOP / SINGLE
        btn_row = QHBoxLayout()
        self.btn_run = QPushButton("▶ RUN")
        self.btn_run.setObjectName("success")
        self.btn_run.clicked.connect(self.run_requested.emit)
        btn_row.addWidget(self.btn_run)

        self.btn_stop = QPushButton("⏹ STOP")
        self.btn_stop.setObjectName("danger")
        self.btn_stop.clicked.connect(self.stop_requested.emit)
        btn_row.addWidget(self.btn_stop)

        self.btn_single = QPushButton("⚡ SINGLE")
        self.btn_single.clicked.connect(self.single_requested.emit)
        btn_row.addWidget(self.btn_single)
        layout.addLayout(btn_row)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)

        # Time/Div Scale
        grid.addWidget(QLabel("Scale:"), 0, 0)
        self.combo_scale = QComboBox()
        for label, val in self.TIME_DIV_OPTIONS:
            self.combo_scale.addItem(label, val)
        self.combo_scale.setCurrentIndex(8)  # 1 ms/div
        self.combo_scale.currentIndexChanged.connect(self._on_scale_changed)
        grid.addWidget(self.combo_scale, 0, 1)

        # Position (s)
        grid.addWidget(QLabel("Position:"), 1, 0)
        self.spin_pos = QDoubleSpinBox()
        self.spin_pos.setRange(-10.0, 10.0)
        self.spin_pos.setSingleStep(0.001)
        self.spin_pos.setValue(0.0)
        self.spin_pos.setSuffix(" s")
        self.spin_pos.valueChanged.connect(self.position_changed.emit)
        grid.addWidget(self.spin_pos, 1, 1)

        layout.addLayout(grid)

    def _on_scale_changed(self, idx: int):
        val = self.combo_scale.currentData()
        if val is not None:
            self.scale_changed.emit(float(val))

    def set_verified_scale(self, scale: float):
        for idx in range(self.combo_scale.count()):
            if abs(self.combo_scale.itemData(idx) - scale) < 1e-9:
                self.combo_scale.blockSignals(True)
                self.combo_scale.setCurrentIndex(idx)
                self.combo_scale.blockSignals(False)
                break
