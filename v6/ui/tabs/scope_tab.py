"""ScopeTab — Rohde & Schwarz RTB2000 digital oscilloscope studio workspace."""
import time
from typing import Dict, Any, List, Optional

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame, QMessageBox, QFileDialog
    )
    from PyQt6.QtCore import Qt, pyqtSignal
except ImportError:
    class QWidget:
        def __init__(self, parent=None): pass
    class QVBoxLayout:
        def __init__(self, parent=None): pass
    class QHBoxLayout:
        def __init__(self, parent=None): pass
    class QScrollArea:
        def __init__(self, parent=None): pass
    class QFrame:
        def __init__(self, parent=None): pass
    def pyqtSignal(*args, **kwargs):
        class Sig:
            def connect(self, s): pass
            def emit(self, *a): pass
        return Sig()

from ..scope.scope_screen import ScopeScreen
from ..scope.channel_control import ChannelControlWidget
from ..scope.timebase_control import TimebaseControlWidget
from ..scope.trigger_control import TriggerControlWidget
from ..scope.math_panel import MathPanelWidget
from ..scope.softkey_bar import SoftkeyBar
from ..styles.tokens import SCOPE_CH1_COLOR, SCOPE_CH2_COLOR
from ...instruments.rtb2000.math_engine import ScopeMathEngine
from ...core.waveform_store import WaveformStore


class ScopeTab(QWidget):
    """
    Dedicated Oscilloscope workspace providing live multi-channel visualization,
    interactive timebase/channel/trigger controls, waveform math, and one-click
    NPZ/CSV acquisition storage.
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
        self.math_config = {"enabled": False, "operation": "ADD", "window": "hann"}
        self.last_waveform_data: Dict[str, Any] = {}

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(10)

        # Center/Left: Scope Display Screen + Bottom Benchtop Softkeys
        left_box = QVBoxLayout()
        left_box.setSpacing(0)

        self.screen = ScopeScreen(self)
        left_box.addWidget(self.screen, 1)

        self.softkeys = SoftkeyBar(self)
        self.softkeys.autoscale_clicked.connect(self.autoscale_requested.emit)
        self.softkeys.single_capture_clicked.connect(self.single_capture_requested.emit)
        self.softkeys.snapshot_clicked.connect(self._save_waveform_dialog)
        left_box.addWidget(self.softkeys)

        root_layout.addLayout(left_box, 1)

        # Right: Hardware Front-Panel Controls Sidebar (Scrollable)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(310)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        sidebar_container = QWidget()
        side_layout = QVBoxLayout(sidebar_container)
        side_layout.setContentsMargins(4, 0, 4, 0)
        side_layout.setSpacing(10)

        # Timebase
        self.timebase_ctrl = TimebaseControlWidget(self)
        self.timebase_ctrl.scale_changed.connect(self.timebase_scale_requested.emit)
        self.timebase_ctrl.run_requested.connect(self.run_requested.emit)
        self.timebase_ctrl.stop_requested.connect(self.stop_requested.emit)
        self.timebase_ctrl.single_requested.connect(self.single_capture_requested.emit)
        side_layout.addWidget(self.timebase_ctrl)

        # Trigger
        self.trigger_ctrl = TriggerControlWidget(self)
        self.trigger_ctrl.level_changed.connect(self._on_trigger_level_changed)
        self.trigger_ctrl.source_changed.connect(self.trigger_source_requested.emit)
        side_layout.addWidget(self.trigger_ctrl)

        # Channels
        self.ch1_ctrl = ChannelControlWidget(1, SCOPE_CH1_COLOR, self)
        self.ch1_ctrl.scale_changed.connect(lambda ch, s: self.channel_scale_requested.emit(ch, s))
        self.ch1_ctrl.state_changed.connect(lambda ch, en: self.channel_state_requested.emit(ch, en))
        side_layout.addWidget(self.ch1_ctrl)

        self.ch2_ctrl = ChannelControlWidget(2, SCOPE_CH2_COLOR, self)
        self.ch2_ctrl.scale_changed.connect(lambda ch, s: self.channel_scale_requested.emit(ch, s))
        self.ch2_ctrl.state_changed.connect(lambda ch, en: self.channel_state_requested.emit(ch, en))
        side_layout.addWidget(self.ch2_ctrl)

        # Waveform Math
        self.math_ctrl = MathPanelWidget(self)
        self.math_ctrl.math_changed.connect(self._on_math_configured)
        side_layout.addWidget(self.math_ctrl)

        side_layout.addStretch()
        scroll.setWidget(sidebar_container)
        root_layout.addWidget(scroll)

    def _on_trigger_level_changed(self, level: float):
        self.trigger_level_requested.emit(level)
        self.screen.set_trigger_level(level)

    def _on_math_configured(self, cfg: dict):
        self.math_config = cfg
        self._recompute_math_trace()

    def update_waveform_display(self, waveform_dict: Dict[str, Any]):
        """Receives multi-channel waveform capture and renders on canvas."""
        self.last_waveform_data = waveform_dict
        t_arr = waveform_dict.get("time", [])

        if "ch1" in waveform_dict:
            self.screen.set_channel_data(1, t_arr, waveform_dict["ch1"])
        if "ch2" in waveform_dict:
            self.screen.set_channel_data(2, t_arr, waveform_dict["ch2"])

        self._recompute_math_trace()

    def _recompute_math_trace(self):
        if not self.math_config.get("enabled", False) or not self.last_waveform_data:
            return

        t_arr = self.last_waveform_data.get("time", [])
        ch1_arr = self.last_waveform_data.get("ch1", [])
        ch2_arr = self.last_waveform_data.get("ch2", [])

        op = self.math_config.get("operation", "ADD")
        if op == "ADD" and ch1_arr and ch2_arr:
            math_y = ScopeMathEngine.add(ch1_arr, ch2_arr)
            self.screen.set_channel_data(99, t_arr, math_y)
        elif op == "SUB" and ch1_arr and ch2_arr:
            math_y = ScopeMathEngine.subtract(ch1_arr, ch2_arr)
            self.screen.set_channel_data(99, t_arr, math_y)
        elif op == "MUL" and ch1_arr and ch2_arr:
            math_y = ScopeMathEngine.multiply(ch1_arr, ch2_arr)
            self.screen.set_channel_data(99, t_arr, math_y)
        elif op.startswith("FFT"):
            source = ch1_arr if op == "FFT1" else ch2_arr
            if source and len(t_arr) > 1:
                dt = (t_arr[-1] - t_arr[0]) / len(t_arr)
                freqs, mag = ScopeMathEngine.fft(source, dt, self.math_config.get("window", "hann"))
                self.screen.set_channel_data(99, freqs, mag)

    def update_measurements(self, telemetry: Dict[str, Any]):
        ch1_d = {
            "vrms": telemetry.get("ch1_vrms", 0.0),
            "vpp": telemetry.get("ch1_vpp", 0.0),
            "freq_hz": telemetry.get("ch1_freq_hz", 0.0),
        }
        ch2_d = {
            "vrms": telemetry.get("ch2_vrms", 0.0),
            "vpp": telemetry.get("ch2_vpp", 0.0),
            "freq_hz": telemetry.get("ch2_freq_hz", 0.0),
        }
        self.screen.update_measurements(ch1_d, ch2_d)

    def set_verified_settings(self, status: Dict[str, Any]):
        if "timebase_scale" in status:
            self.timebase_ctrl.set_verified_scale(status["timebase_scale"])
        if "ch1_scale" in status:
            self.ch1_ctrl.set_verified_scale(status["ch1_scale"])
        if "ch2_scale" in status:
            self.ch2_ctrl.set_verified_scale(status["ch2_scale"])
        if "ch1_on" in status:
            self.ch1_ctrl.set_verified_state(status["ch1_on"])
        if "ch2_on" in status:
            self.ch2_ctrl.set_verified_state(status["ch2_on"])
        if "trigger_level" in status:
            self.trigger_ctrl.set_verified_level(status["trigger_level"])

    def set_theme(self, is_dark: bool):
        self.is_dark = is_dark
        self.screen.set_theme(is_dark)

    def _save_waveform_dialog(self):
        if not self.last_waveform_data:
            QMessageBox.information(self, "No Waveform", "No waveform data currently captured to save.")
            return

        p, _ = QFileDialog.getSaveFileName(
            self, "Save Oscilloscope Capture (.npz)",
            f"rtb2000_trace_{int(time.time())}.npz", "NumPy Archive (*.npz);;CSV (*.csv)"
        )
        if not p:
            return

        try:
            WaveformStore.save(p, self.last_waveform_data)
            QMessageBox.information(self, "Waveform Stored", f"Successfully saved waveform to:\n{p}")
        except Exception as e:
            QMessageBox.critical(self, "Save Failed", f"Failed to write waveform:\n{e}")
