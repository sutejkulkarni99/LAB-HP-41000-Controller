import os
import csv
import time
from typing import Optional, List
from PySide6.QtCore import QThread, Signal

from .contracts import Instrument
from .clock import SessionClock
from .waveform import WaveformStore

class TelemetryWorker(QThread):
    """Periodic telemetry polling thread for Bench mode monitoring."""

    measurements = Signal(str, dict)
    status = Signal(str, dict)
    connection_lost = Signal(str, str)

    def __init__(self, instrument: Instrument, interval_s: float = 0.2, parent=None):
        super().__init__(parent)
        self.instrument = instrument
        self.interval_s = max(0.05, interval_s)
        self._running = False

    def run(self) -> None:
        self._running = True
        while self._running:
            if not self.instrument.connected:
                self.connection_lost.emit(self.instrument.short_id, "Instrument disconnected")
                break
            try:
                meas = self.instrument.poll_measurements()
                self.measurements.emit(self.instrument.short_id, meas)
            except Exception as e:
                self.connection_lost.emit(self.instrument.short_id, f"Polling error: {e}")
                break

            try:
                st = self.instrument.status()
                self.status.emit(self.instrument.short_id, st)
            except Exception:
                pass

            time.sleep(self.interval_s)

    def stop(self) -> None:
        self._running = False
        self.wait(1000)


class LoggerWorker(QThread):
    """High-reliability synchronized CSV telemetry recording worker."""

    row_written = Signal(str, int, str)
    error = Signal(str, str)

    def __init__(self, instrument: Instrument, clock: SessionClock, csv_path: str, interval_s: float, parent=None):
        super().__init__(parent)
        self.instrument = instrument
        self.clock = clock
        self.csv_path = csv_path
        self.interval_s = max(0.02, interval_s)
        self._running = False
        self._paused = False
        self._row_count = 0

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def stop(self) -> None:
        self._running = False
        self.wait(1000)

    def run(self) -> None:
        self._running = True
        self._paused = False
        os.makedirs(os.path.dirname(os.path.abspath(self.csv_path)), exist_ok=True)

        cols = self.instrument.measurement_columns()
        header = ["iso_timestamp", "epoch_s", "elapsed_s"] + cols

        try:
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(header)
                f.flush()

                while self._running:
                    t_start = time.perf_counter()
                    if not self._paused and self.instrument.connected:
                        try:
                            iso_ts, epoch_s, elapsed_s = self.clock.row_timecodes()
                            meas = self.instrument.poll_measurements()
                            row_vals = [iso_ts, f"{epoch_s:.6f}", f"{elapsed_s:.6f}"]
                            for c in cols:
                                row_vals.append(str(meas.get(c, 0.0)))
                            writer.writerow(row_vals)
                            f.flush()
                            self._row_count += 1
                            self.row_written.emit(self.instrument.short_id, self._row_count, iso_ts)
                        except Exception as e:
                            self.error.emit(self.instrument.short_id, str(e))

                    elapsed_cycle = time.perf_counter() - t_start
                    sleep_time = max(0.005, self.interval_s - elapsed_cycle)
                    time.sleep(sleep_time)
        except Exception as e:
            self.error.emit(self.instrument.short_id, f"File write error: {e}")


class CaptureWorker(QThread):
    """Background waveform acquisition worker saving compressed NPZ archives."""

    captured = Signal(str, str, dict)
    failed = Signal(str, str)

    def __init__(self, instrument: Instrument, session_dir: str, channels: list[str], parent=None):
        super().__init__(parent)
        self.instrument = instrument
        self.session_dir = session_dir
        self.channels = channels

    def run(self) -> None:
        try:
            ts_str = time.strftime("%Y%m%d_%H%M%S")
            ch_tag = "_".join(self.channels)
            filename = f"{self.instrument.short_id}_{ts_str}_{ch_tag}.npz"
            save_path = os.path.join(self.session_dir, "waveforms", filename)

            raw = self.instrument.capture_waveform(self.channels)
            time_vec = raw.get("time")
            ch_data = raw.get("channels", {})
            meta = raw.get("metadata", {})

            saved_path = WaveformStore.save_npz(save_path, time_vec, ch_data, meta)

            # Record to waveforms.csv index
            wf_csv = os.path.join(self.session_dir, "waveforms.csv")
            os.makedirs(os.path.dirname(wf_csv), exist_ok=True)
            write_header = not os.path.exists(wf_csv)
            with open(wf_csv, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if write_header:
                    writer.writerow(["elapsed_s", "instrument", "channels", "npz_path"])
                writer.writerow([f"{time.time():.4f}", self.instrument.short_id, ch_tag, saved_path])

            self.captured.emit(self.instrument.short_id, saved_path, meta)
        except Exception as e:
            self.failed.emit(self.instrument.short_id, str(e))
