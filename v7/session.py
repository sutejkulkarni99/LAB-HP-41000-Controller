import os
import json
import csv
from typing import List, Tuple, Dict, Optional
from PySide6.QtCore import QObject, Signal

from .contracts import Instrument
from .clock import SessionClock
from .workers import LoggerWorker

class LoggingSession(QObject):
    """Orchestrates synchronized multi-instrument data logging sessions."""

    started = Signal(str)
    stopped = Signal(str, dict)
    row = Signal(str, int, str)
    error = Signal(str, str)

    def __init__(self, clock: SessionClock, parent=None):
        super().__init__(parent)
        self.clock = clock
        self._session_dir: str = ""
        self._metadata: dict = {
            "operator": "Lab Engineer",
            "project": "Bench Test",
            "purpose": "Validation"
        }
        self._workers: list[LoggerWorker] = []
        self._instruments: list[tuple[Instrument, float]] = []
        self._row_counts: dict[str, int] = {}
        self._files: dict[str, str] = {}
        self._is_running: bool = False
        self._is_paused: bool = False

    def set_metadata(self, meta: dict) -> None:
        """Assign session metadata for the final session.json manifest."""
        self._metadata.update(meta)

    def start(self, session_dir: str, instruments: list[tuple[Instrument, float]]) -> None:
        """Start synchronized data recording across all configured instruments."""
        self._session_dir = os.path.abspath(session_dir)
        os.makedirs(self._session_dir, exist_ok=True)
        self._instruments = instruments
        self._workers.clear()
        self._row_counts.clear()
        self._files.clear()

        self.clock.reset()
        self._metadata["started_at"] = self.clock.wall_iso()
        self._is_running = True
        self._is_paused = False

        for inst, interval_s in self._instruments:
            csv_path = os.path.join(self._session_dir, f"{inst.short_id}.csv")
            self._files[inst.short_id] = csv_path
            worker = LoggerWorker(inst, self.clock, csv_path, interval_s)
            worker.row_written.connect(self._on_row_written)
            worker.error.connect(self._on_worker_error)
            self._workers.append(worker)
            worker.start()

        self.started.emit(self._session_dir)

    def _on_row_written(self, short_id: str, count: int, iso_ts: str) -> None:
        self._row_counts[short_id] = count
        self.row.emit(short_id, count, iso_ts)

    def _on_worker_error(self, short_id: str, err: str) -> None:
        self.error.emit(short_id, err)

    def pause(self) -> None:
        """Pause session elapsed time and data workers."""
        if self._is_running and not self._is_paused:
            self.clock.pause()
            self._is_paused = True
            for w in self._workers:
                w.pause()

    def resume(self) -> None:
        """Resume session elapsed time and data workers."""
        if self._is_running and self._is_paused:
            self.clock.resume()
            self._is_paused = False
            for w in self._workers:
                w.resume()

    def stop(self) -> dict[str, str]:
        """Stop logging workers, finalize manifest session.json, and return file paths."""
        if not self._is_running:
            return self._files

        for w in self._workers:
            w.stop()
        self._workers.clear()

        self._metadata["stopped_at"] = self.clock.wall_iso()
        self._is_running = False
        self._is_paused = False

        # Gather events if any instrument supports events
        for inst, _ in self._instruments:
            if inst.supports_events:
                evs = inst.events()
                if evs:
                    ev_csv = os.path.join(self._session_dir, "events.csv")
                    with open(ev_csv, "w", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow(["elapsed_s", "instrument", "event", "detail"])
                        for ev in evs:
                            writer.writerow([ev.get("elapsed_s", 0.0), inst.short_id, ev.get("event", ""), ev.get("detail", "")])
                    self._files["events"] = ev_csv

        # Generate session.json
        manifest = {
            "meta": self._metadata,
            "instruments": {
                inst.short_id: {
                    "idn": inst.idn(),
                    "config": inst.configuration()
                } for inst, _ in self._instruments
            },
            "files": self._files,
            "rows_recorded": self._row_counts
        }

        manifest_path = os.path.join(self._session_dir, "session.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        self.stopped.emit(self._session_dir, manifest)
        return self._files
