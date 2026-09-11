"""InstrumentLogger — Dedicated thread logging an individual instrument under a SessionClock."""
import os
import csv
import time
import threading
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any

try:
    from PyQt6.QtCore import QThread, pyqtSignal
except ImportError:
    class QThread:
        def __init__(self, parent=None):
            self._th = None
        def isRunning(self):
            return self._th.is_alive() if self._th else False
        def start(self):
            self._th = threading.Thread(target=self.run, daemon=True)
            self._th.start()
        def wait(self, msecs=None):
            if self._th:
                self._th.join(timeout=(msecs / 1000.0) if msecs else None)
        def quit(self):
            pass

    def pyqtSignal(*args, **kwargs):
        class SignalStub:
            def __init__(self):
                self._slots = []
            def connect(self, slot):
                self._slots.append(slot)
            def emit(self, *a, **kw):
                for s in self._slots:
                    try: s(*a, **kw)
                    except Exception: pass
        return SignalStub()

from ..core.session_clock import SessionClock
from ..core.instrument_base import InstrumentBase


class InstrumentLogger(QThread):
    """
    Dedicated high-reliability logging thread for an individual instrument.
    Streams scalar telemetry rows to CSV and logs waveform references to waveforms.csv
    synchronized against a shared SessionClock.
    """

    row_logged = pyqtSignal(str, int, str)        # short_id, count, preview
    error_occurred = pyqtSignal(str, str)        # short_id, error_message

    def __init__(
        self,
        instrument: InstrumentBase,
        clock: SessionClock,
        csv_filepath: str,
        interval_s: float = 0.1,
        parent=None
    ):
        super().__init__(parent)
        self.instrument = instrument
        self.clock = clock
        self.csv_filepath = csv_filepath
        self.interval_s = max(0.001, float(interval_s))

        self._running = False
        self._paused = False
        self._lock = threading.Lock()
        self.row_count = 0
        self._pending_waveforms: List[Tuple[float, str, str, str]] = []

    def queue_waveform(self, elapsed_s: float, instrument: str, channels: str, npz_path: str):
        """Queues a waveform record for the parallel waveforms.csv index."""
        with self._lock:
            self._pending_waveforms.append((elapsed_s, instrument, channels, npz_path))

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def stop(self):
        self._running = False
        if hasattr(self, "wait"):
            self.wait(1000)

    def run(self):
        self._running = True
        parent_dir = Path(self.csv_filepath).parent
        parent_dir.mkdir(parents=True, exist_ok=True)
        waveforms_csv_path = parent_dir / "waveforms.csv"

        columns = self.instrument.measurement_columns()
        header = ["iso_timestamp", "epoch_s", "elapsed_s"] + list(columns)

        write_wf_header = not waveforms_csv_path.exists() or waveforms_csv_path.stat().st_size == 0

        try:
            with open(self.csv_filepath, "w", newline="", encoding="utf-8") as f_main, \
                 open(waveforms_csv_path, "a", newline="", encoding="utf-8") as f_wf:
                writer = csv.writer(f_main)
                writer.writerow(header)
                f_main.flush()

                wf_writer = csv.writer(f_wf)
                if write_wf_header:
                    wf_writer.writerow(["elapsed_s", "instrument", "channels", "npz_path"])
                    f_wf.flush()

                next_tick = time.perf_counter()
                while self._running:
                    if self._paused:
                        time.sleep(0.05)
                        next_tick = time.perf_counter()
                        continue

                    # 1. Flush any pending waveforms to waveforms.csv
                    with self._lock:
                        wf_batch = self._pending_waveforms[:]
                        self._pending_waveforms.clear()

                    if wf_batch:
                        for el_s, inst_name, chs, npz in wf_batch:
                            wf_writer.writerow([f"{el_s:.4f}", inst_name, chs, npz])
                        f_wf.flush()

                    # 2. Query instrument scalar measurements
                    try:
                        meas = self.instrument.poll_measurements()
                    except Exception as e:
                        self.error_occurred.emit(self.instrument.short_id, str(e))
                        meas = {}

                    wall_iso, epoch_s, elapsed_s = self.clock.row_timecodes()
                    row_vals = [wall_iso, f"{epoch_s:.4f}", f"{elapsed_s:.4f}"]
                    for col in columns:
                        val = meas.get(col, "")
                        row_vals.append(f"{val:.4f}" if isinstance(val, (int, float)) else str(val))

                    writer.writerow(row_vals)
                    f_main.flush()

                    self.row_count += 1
                    preview = f"t={elapsed_s:.2f}s | " + ", ".join(f"{c}={meas.get(c, '')}" for c in columns[:2])
                    self.row_logged.emit(self.instrument.short_id, self.row_count, preview)

                    next_tick += self.interval_s
                    sleep_time = next_tick - time.perf_counter()
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                    else:
                        next_tick = time.perf_counter()

                # Flush final batch of waveforms if any queued during teardown
                with self._lock:
                    final_wfs = self._pending_waveforms[:]
                    self._pending_waveforms.clear()
                if final_wfs:
                    for el_s, inst_name, chs, npz in final_wfs:
                        wf_writer.writerow([f"{el_s:.4f}", inst_name, chs, npz])
                    f_wf.flush()

        except Exception as e:
            self.error_occurred.emit(self.instrument.short_id, f"File logging exception: {e}")
