"""LoggingSession — Session coordinator orchestrating multiple concurrent instrument loggers."""
import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

try:
    from PyQt6.QtCore import QObject, pyqtSignal
except ImportError:
    class QObject:
        def __init__(self, parent=None): pass
    def pyqtSignal(*args, **kwargs):
        class SignalStub:
            def connect(self, slot): pass
            def emit(self, *a, **kw): pass
        return SignalStub()

from .session_clock import SessionClock
from .instrument_base import InstrumentBase
from ..workers.logger_worker import InstrumentLogger


class LoggingSession(QObject):
    """
    Orchestrates synchronized multi-instrument data logging sessions.
    Coordinates individual InstrumentLogger threads under a shared SessionClock,
    manages CSV paths, and writes sealed manifest.json upon completion.
    """

    started = pyqtSignal(str)              # session_dir
    stopped = pyqtSignal(str, dict)        # session_dir, final_csv_paths
    row = pyqtSignal(str, int, str)        # short_id, count, preview
    error = pyqtSignal(str, str)           # short_id, error_message

    def __init__(self, clock: Optional[SessionClock] = None, parent=None):
        super().__init__(parent)
        self.clock = clock or SessionClock()
        self.session_dir = ""
        self.loggers: Dict[str, InstrumentLogger] = {}
        self.temp_csv_paths: Dict[str, str] = {}
        self.instruments_meta: Dict[str, Any] = {}
        self.is_running = False
        self.is_paused = False
        self.metadata: Dict[str, Any] = {}

    def set_metadata(self, meta: Dict[str, Any]):
        """Sets user manifest metadata (operator, test ID, notes, etc.)."""
        self.metadata = meta

    def start(self, session_dir: str, instruments_with_intervals: List[Tuple[InstrumentBase, float]]):
        """
        Starts recording session for all passed instruments.
        instruments_with_intervals is a list of tuples: (instrument, interval_seconds).
        The interval_seconds is always treated strictly as elapsed seconds between logged rows.
        """
        self.session_dir = session_dir
        Path(self.session_dir).mkdir(parents=True, exist_ok=True)

        self.clock.reset()
        self.clock.start()

        t0_clean = time.strftime("%Y%m%d_%H%M%S")
        self.loggers.clear()
        self.temp_csv_paths.clear()
        self.instruments_meta.clear()

        for inst, interval_s in instruments_with_intervals:
            interval = max(0.001, float(interval_s))
            short_id = inst.short_id
            temp_csv = str(Path(self.session_dir) / f"{short_id}_{t0_clean}.csv")
            self.temp_csv_paths[short_id] = temp_csv

            self.instruments_meta[short_id] = {
                "name": inst.name,
                "columns": inst.measurement_columns(),
                "interval_seconds": interval,
                "rate_hz": round(1.0 / interval, 2)
            }

            logger = InstrumentLogger(
                instrument=inst,
                clock=self.clock,
                csv_filepath=temp_csv,
                interval_s=interval
            )
            logger.row_logged.connect(lambda sid, cnt, prev: self.row.emit(sid, cnt, prev))
            logger.error_occurred.connect(lambda sid, err: self.error.emit(sid, err))
            self.loggers[short_id] = logger
            logger.start()

        self.is_running = True
        self.is_paused = False
        self.started.emit(self.session_dir)

    def pause(self):
        """Pauses acquisition on all child loggers and pauses session clock."""
        if not self.is_running or self.is_paused:
            return
        self.clock.pause()
        for logger in self.loggers.values():
            logger.pause()
        self.is_paused = True

    def resume(self):
        """Resumes acquisition on all child loggers and resumes session clock."""
        if not self.is_running or not self.is_paused:
            return
        self.clock.resume()
        for logger in self.loggers.values():
            logger.resume()
        self.is_paused = False

    def stop(self) -> Dict[str, str]:
        """
        Stops all loggers, renames temporary CSVs to canonical filenames,
        seals manifest.json, and emits stopped(session_dir, final_csv_paths).
        """
        if not self.is_running:
            return {}

        self.clock.pause()

        # Stop all child logging threads
        for logger in self.loggers.values():
            logger.stop()

        final_csv_paths: Dict[str, str] = {}
        total_rows: Dict[str, int] = {}

        # Canonicalize filenames
        for short_id, temp_path in self.temp_csv_paths.items():
            canonical_path = str(Path(self.session_dir) / f"{short_id}.csv")
            try:
                if os.path.exists(temp_path):
                    if os.path.exists(canonical_path):
                        os.remove(canonical_path)
                    os.rename(temp_path, canonical_path)
                    final_csv_paths[short_id] = canonical_path
                else:
                    final_csv_paths[short_id] = temp_path
            except Exception:
                final_csv_paths[short_id] = temp_path

            logger = self.loggers.get(short_id)
            total_rows[short_id] = logger.row_count if logger else 0

        # Build and seal manifest.json
        manifest = {
            "status": "COMPLETED",
            "session_dir": self.session_dir,
            "created_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "elapsed_seconds": round(self.clock.now(), 4),
            "metadata": self.metadata,
            "instruments": self.instruments_meta,
            "files": final_csv_paths,
            "rows_recorded": total_rows
        }

        manifest_file = Path(self.session_dir) / "manifest.json"
        try:
            with open(manifest_file, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)
        except Exception:
            pass

        self.is_running = False
        self.is_paused = False
        self.stopped.emit(self.session_dir, final_csv_paths)
        return final_csv_paths
