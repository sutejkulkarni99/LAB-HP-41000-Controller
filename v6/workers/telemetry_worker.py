"""TelemetryWorker — Generic background poller for any InstrumentBase instance."""
import time
import threading

try:
    from PyQt6.QtCore import QThread, pyqtSignal
except ImportError:
    class QThread:
        def __init__(self, parent=None): pass
        def start(self): pass
        def wait(self, timeout=None): pass
        def isRunning(self): return False
    def pyqtSignal(*args, **kwargs):
        class SignalMock:
            def __init__(self): self._slots = []
            def emit(self, *a, **kw):
                for s in self._slots:
                    try: s(*a, **kw)
                    except Exception: pass
            def connect(self, s): self._slots.append(s)
            def disconnect(self, s=None): pass
        return SignalMock()

from ..core.instrument_base import InstrumentBase


class TelemetryWorker(QThread):
    """
    Generic high-speed background polling thread for any InstrumentBase subclass.
    Continuously retrieves measurement dictionary and operating status,
    emitting PyQt signals to update GUI widgets without blocking the main event loop.
    """

    measurements = pyqtSignal(str, dict)    # short_id, measurements_dict
    status_update = pyqtSignal(str, dict)   # short_id, status_dict
    connection_lost = pyqtSignal(str, str)  # short_id, error_message

    def __init__(self, instrument: InstrumentBase, interval_s: float = 0.2, parent=None):
        super().__init__(parent)
        self.instrument = instrument
        self.interval_s = max(0.04, interval_s)
        self._stop_event = threading.Event()
        self._force_trigger = threading.Event()

    def set_interval(self, interval_s: float):
        self.interval_s = max(0.04, interval_s)

    def trigger_now(self):
        self._force_trigger.set()

    def stop(self):
        self._stop_event.set()
        self._force_trigger.set()
        self.wait(1500)

    def run(self):
        while not self._stop_event.is_set():
            if not self.instrument.connected:
                self.connection_lost.emit(self.instrument.short_id, "Device disconnected")
                break

            try:
                meas = self.instrument.poll_measurements()
                self.measurements.emit(self.instrument.short_id, meas)

                stat = self.instrument.status()
                self.status_update.emit(self.instrument.short_id, stat)

            except Exception as e:
                if not self._stop_event.is_set():
                    self.connection_lost.emit(self.instrument.short_id, str(e))
                    break

            # Sleep with interruptibility
            self._stop_event.wait(self.interval_s)
            self._force_trigger.clear()
