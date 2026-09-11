"""TelemetryWorker — High-speed background telemetry and status poller for instruments."""
import time
import threading
import math
from typing import Optional, Any

try:
    from PyQt6.QtCore import QThread, pyqtSignal
except ImportError:
    class QThread:
        def __init__(self, parent=None):
            self._th = None
        def start(self):
            self._th = threading.Thread(target=self.run, daemon=True)
            self._th.start()
        def wait(self, timeout=None):
            if self._th:
                self._th.join(timeout=timeout)
        def isRunning(self):
            return self._th.is_alive() if self._th else False
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


class TelemetryWorker(QThread):
    """
    High-speed background polling thread for DC power supply (and generic instruments).
    Continuously queries voltage, current, power, resistance, output state, and protection
    badges without blocking the Qt GUI thread.
    """

    # Primary UI signals expected by MainWindow and PSUTab
    telemetry_received = pyqtSignal(float, float, float, float, float)  # t_sec, v, i, p, r
    output_state_received = pyqtSignal(bool)                           # is_output_on
    status_received = pyqtSignal(bool, bool, bool, bool)               # ovp, ocp, otp, opp
    connection_lost = pyqtSignal(str)                                  # error_message

    # Generic telemetry signals
    measurements = pyqtSignal(str, dict)                               # short_id, measurements_dict
    status_update = pyqtSignal(str, dict)                              # short_id, status_dict

    def __init__(self, target: Any, interval_s: float = 0.1, parent=None):
        super().__init__(parent)
        self.target = target
        self.interval_s = max(0.04, interval_s)
        self._stop_event = threading.Event()
        self._force_trigger = threading.Event()
        self._start_time = time.monotonic()
        self._consecutive_errors = 0

    @property
    def driver(self):
        """Returns the underlying driver object if wrapped in an InstrumentBase."""
        return getattr(self.target, "driver", self.target)

    @property
    def is_connected(self) -> bool:
        return bool(getattr(self.target, "connected", False) or getattr(self.driver, "connected", False))

    def set_interval(self, interval_s: float):
        self.interval_s = max(0.04, interval_s)

    def trigger_now(self):
        self._force_trigger.set()

    def stop(self):
        self._stop_event.set()
        self._force_trigger.set()
        self.wait(1500)

    def run(self):
        self._start_time = time.monotonic()
        self._consecutive_errors = 0

        while not self._stop_event.is_set():
            if not self.is_connected:
                self.connection_lost.emit("Instrument disconnected")
                break

            drv = self.driver
            t_elapsed = round(time.monotonic() - self._start_time, 3)

            try:
                # 1. Query voltage & current
                v = 0.0
                i = 0.0
                if hasattr(drv, "measure_voltage"):
                    v = drv.measure_voltage()
                elif hasattr(drv, "get_voltage"):
                    v = drv.get_voltage()

                if hasattr(drv, "measure_current"):
                    i = drv.measure_current()
                elif hasattr(drv, "get_current"):
                    i = drv.get_current()

                p = round(v * i, 2)
                r = round(v / i, 2) if i > 0.0005 else float('inf')

                # Emit telemetry
                self.telemetry_received.emit(t_elapsed, v, i, p, r)
                self.measurements.emit("labhp_41000", {
                    "voltage": v, "current": i, "power": p, "resistance": r, "elapsed_s": t_elapsed
                })

                # 2. Query output state
                out_state = False
                if hasattr(drv, "get_output_state"):
                    out_state = drv.get_output_state()
                elif hasattr(drv, "output_state"):
                    out_state = drv.output_state
                self.output_state_received.emit(bool(out_state))

                # 3. Query status / protection trips
                ovp = False
                ocp = False
                otp = False
                opp = False
                if hasattr(drv, "get_status_raw") and hasattr(drv, "decode_status"):
                    raw = drv.get_status_raw()
                    dec = drv.decode_status(raw)
                    ovp = dec.get("OVP shutdown", False)
                    ocp = dec.get("Current limit", False)
                    opp = dec.get("Power limit", False)
                    self.status_update.emit("labhp_41000", dec)

                self.status_received.emit(ovp, ocp, otp, opp)
                self._consecutive_errors = 0

            except Exception as e:
                self._consecutive_errors += 1
                if self._consecutive_errors >= 5:
                    if not self._stop_event.is_set():
                        self.connection_lost.emit(str(e))
                        break

            # Sleep with interruptibility
            self._stop_event.wait(self.interval_s)
            self._force_trigger.clear()
