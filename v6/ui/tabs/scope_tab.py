"""ScopeTab — Rohde & Schwarz RTB2000 oscilloscope front panel card with responsive layout."""
from typing import Dict, Any, List

from ..qt_compat import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QComboBox, QDoubleSpinBox, QPushButton, QCheckBox,
    QTabWidget, QSplitter, QScrollArea, QFrame, QSizePolicy,
    Qt, pyqtSignal
)

from ..scope.display import ScopeDisplayWidget
from ..scope.channel_control import ChannelControlWidget
from ..scope.timebase_control import TimebaseControlWidget
from ..scope.trigger_control import TriggerControlWidget
from ..scope.measurements_card import MeasurementsCard
from ..scope.softkey_bar import SoftkeyBar
from ..widgets.collapsible import CollapsibleSection
from ..styles.tokens import SCOPE_CH1_COLOR, SCOPE_CH2_COLOR, SCOPE_MATH_COLOR


class ScopeTab(QWidget):
    """
    Complete benchtop oscilloscope front panel mirroring R&S RTB2000 hardware capabilities:
    4 analog channels, timebase, edge trigger, math channels, cursors, and hardware measurements.
    """

    timebase_scale_requested = pyqtSignal(float)
    channel_scale_requested = pyqtSignal(int, float)
    channel_state_requested = pyqtSignal(int, bool)
    trigger_level_requested = pyqtSignal(float)
    trigger_source_requested = pyqtSignal(str)
    run_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    single_capture_requested = pyqtSignal()
    autoscale_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_dark = True

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(10, 10, 10, 10)
        outer_layout.setSpacing(6)

        # Main horizontal splitter: Left (Waveform display + Softkeys) vs Right (Controls)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # ---------------------------------------------------------------------
        # LEFT REGION: Live Graticule Scope Display & Bottom Softkeys
        # ---------------------------------------------------------------------
        left_box = QWidget()
        left_layout = QVBoxLayout(left_box)
        left_layout.setContentsMargins(0, 0, 4, 0)
        left_layout.setSpacing(6)

        self.display = ScopeDisplayWidget(self)
        left_layout.addWidget(self.display, 1)

        self.softkeys = SoftkeyBar(self)
        self.softkeys.autoscale_clicked.connect(self.autoscale_requested.emit)
        self.softkeys.single_capture_clicked.connect(self.single_capture_requested.emit)
        self.softkeys.clear_sweeps_clicked.connect(self.display.clear_sweeps)
        left_layout.addWidget(self.softkeys)

        self.splitter.addWidget(left_box)

        # ---------------------------------------------------------------------
        # RIGHT REGION: Controls wrapped in QScrollArea with CollapsibleSections
        # ---------------------------------------------------------------------
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(4, 0, 0, 0)
        right_layout.setSpacing(8)

        # 1. Channels Section (Expanded)
        self.sec_channels = CollapsibleSection("Analog Channels (CH1 / CH2)")
        self.sec_channels.setStatus("CH1: 1V/div | CH2: 1V/div")
        ch_container = QWidget()
        ch_layout = QVBoxLayout(ch_container)
        ch_layout.setContentsMargins(0, 4, 0, 4)
        ch_layout.setSpacing(8)

        self.ch1_ctrl = ChannelControlWidget(1, SCOPE_CH1_COLOR, self)
        self.ch1_ctrl.scale_changed.connect(self.channel_scale_requested.emit)
        self.ch1_ctrl.state_changed.connect(self.channel_state_requested.emit)
        ch_layout.addWidget(self.ch1_ctrl)

        self.ch2_ctrl = ChannelControlWidget(2, SCOPE_CH2_COLOR, self)
        self.ch2_ctrl.scale_changed.connect(self.channel_scale_requested.emit)
        self.ch2_ctrl.state_changed.connect(self.channel_state_requested.emit)
        ch_layout.addWidget(self.ch2_ctrl)

        self.sec_channels.setContentWidget(ch_container)
        self.sec_channels.setExpanded(True)
        right_layout.addWidget(self.sec_channels)

        # 2. Math & Waveform Analysis (Collapsed)
        self.sec_math = CollapsibleSection("Math & Advanced Operations")
        self.sec_math.setStatus("Math Off")
        math_container = QWidget()
        m_layout = QVBoxLayout(math_container)
        m_layout.setContentsMargins(0, 4, 0, 4)
        m_layout.setSpacing(6)

        m_row = QHBoxLayout()
        self.chk_math_on = QCheckBox("Enable Math (CH1 - CH2)")
        self.chk_math_on.setStyleSheet(f"color: {SCOPE_MATH_COLOR}; font-weight: bold;")
        self.chk_math_on.toggled.connect(self._on_math_toggled)
        m_row.addWidget(self.chk_math_on)
        m_layout.addLayout(m_row)

        self.sec_math.setContentWidget(math_container)
        self.sec_math.setExpanded(False)
        right_layout.addWidget(self.sec_math)

        # 3. Horizontal Timebase (Expanded)
        self.sec_timebase = CollapsibleSection("Horizontal Timebase & Acquisition")
        self.sec_timebase.setStatus("1 ms/div")
        self.timebase_ctrl = TimebaseControlWidget(self)
        self.timebase_ctrl.scale_changed.connect(self.timebase_scale_requested.emit)
        self.timebase_ctrl.run_requested.connect(self.run_requested.emit)
        self.timebase_ctrl.stop_requested.connect(self.stop_requested.emit)
        self.timebase_ctrl.single_requested.connect(self.single_capture_requested.emit)
        self.sec_timebase.setContentWidget(self.timebase_ctrl)
        self.sec_timebase.setExpanded(True)
        right_layout.addWidget(self.sec_timebase)

        # 4. Trigger Controls (Collapsed)
        self.sec_trigger = CollapsibleSection("Edge Trigger System")
        self.sec_trigger.setStatus("CH1 Edge, 0.00V")
        self.trigger_ctrl = TriggerControlWidget(self)
        self.trigger_ctrl.source_changed.connect(self.trigger_source_requested.emit)
        self.trigger_ctrl.level_changed.connect(self.trigger_level_requested.emit)
        self.sec_trigger.setContentWidget(self.trigger_ctrl)
        self.sec_trigger.setExpanded(False)
        right_layout.addWidget(self.sec_trigger)

        # 5. Live Measurements Card
        self.sec_measurements = CollapsibleSection("Hardware Measurements")
        self.sec_measurements.setStatus("Vrms, Vpp, Freq")
        self.measurements = MeasurementsCard(self)
        self.sec_measurements.setContentWidget(self.measurements)
        self.sec_measurements.setExpanded(True)
        right_layout.addWidget(self.sec_measurements)

        right_layout.addStretch()
        right_scroll.setWidget(right_widget)
        self.splitter.addWidget(right_scroll)

        # Set Splitter Stretch Factors (68% Left, 32% Right)
        self.splitter.setStretchFactor(0, 68)
        self.splitter.setStretchFactor(1, 32)

        outer_layout.addWidget(self.splitter)

    def _on_math_toggled(self, checked: bool):
        self.sec_math.setStatus("CH1 - CH2 Active" if checked else "Math Off")

    def update_waveform_display(self, wf_dict: Dict[str, Any]):
        self.display.render_waveforms(wf_dict)

    def update_measurements(self, metrics: Dict[str, Any]):
        self.measurements.update_metrics(metrics)

    def set_verified_settings(self, scale_v_div: float, time_div: float):
        self.ch1_ctrl.set_verified_scale(scale_v_div)
        self.timebase_ctrl.set_verified_scale(time_div)
        self.sec_timebase.setStatus(f"{time_div*1e3:.1f} ms/div" if time_div >= 1e-3 else f"{time_div*1e6:.0f} µs/div")

    def set_theme(self, is_dark: bool):
        self.is_dark = is_dark
        self.display.set_theme(is_dark)
