"""ScopeWorker — Continuous real-time waveform and measurement acquisition worker."""
import time
import queue
from typing import Dict, Any, Optional, Callable

try:
    from PyQt6.QtCore import QThread, pyqtSignal
except ImportError:
    class QThread:
        def __init__(self, parent=None): pass
        def start(self): pass
        def wait(self, timeout=None): pass
        def isRunning(self): return False
    def pyqtSignal(*args, **kwargs):
        class Sig:
            def connect(self, s): pass
            def emit(self, *a): pass
        return Sig()


class ScopeWorker(QThread):
    """
    Background worker thread polling scalar measurements, capturing live multi-channel
    waveforms, and safely dispatching hardware control commands via a thread-safe queue.
    """

    waveform_captured = pyqtSignal(dict)  # {"time": [...], "ch1": [...], "ch2": [...]}
    telemetry_received = pyqtSignal(dict) # Scalar measurement metrics
    status_verified = pyqtSignal(dict)    # Status feedback
    connection_lost = pyqtSignal(str)

    def __init__(self, instrument, capture_interval_s: float = 0.2, parent=None):
        super().__init__(parent)
        self.instrument = instrument
        self.capture_interval_s = capture_interval_s
        self.running = False
        self.cmd_queue: queue.Queue = queue.Queue()
        self.last_telemetry: Dict[str, Any] = {}

    def queue_command(self, cmd_fn: Callable):
        """Thread-safe command submission to execute on worker thread."""
        self.cmd_queue.put(cmd_fn)

    def run(self):
        self.running = True
        while self.running:
            start_loop = time.time()

            # 1. Process any pending hardware commands
            while not self.cmd_queue.empty():
                try:
                    fn = self.cmd_queue.get_nowait()
                    fn(self.instrument.driver)
                    # Query status to verify
                    st = self.instrument.status()
                    self.status_verified.emit(st)
                except Exception as e:
                    pass

            # 2. Poll scalar measurements & status
            try:
                meas = self.instrument.poll_measurements()
                self.last_telemetry = meas
                self.telemetry_received.emit(meas)
            except Exception as e:
                self.connection_lost.emit(str(e))
                break

            # 3. Capture waveforms for active channels
            try:
                wf_dict: Dict[str, Any] = {}
                time_arr = None

                # Capture CH1 if active
                if getattr(self.instrument.driver, "channel_state", {}).get(1, True):
                    trace1 = self.instrument.get_waveform(1)
                    if trace1 is not None and len(trace1.y_volts) > 0:
                        time_arr = trace1.x_time.tolist()
                        wf_dict["ch1"] = trace1.y_volts.tolist()

                # Capture CH2 if active
                if getattr(self.instrument.driver, "channel_state", {}).get(2, True):
                    trace2 = self.instrument.get_waveform(2)
                    if trace2 is not None and len(trace2.y_volts) > 0:
                        if time_arr is None:
                            time_arr = trace2.x_time.tolist()
                        wf_dict["ch2"] = trace2.y_volts.tolist()

                if time_arr is not None:
                    wf_dict["time"] = time_arr
                    self.waveform_captured.emit(wf_dict)

            except Exception:
                pass

            elapsed = time.time() - start_loop
            sleep_time = max(0.01, self.capture_interval_s - elapsed)
            time.sleep(sleep_time)

    def stop(self):
        self.running = False
        self.wait(1000)
