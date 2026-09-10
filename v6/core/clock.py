"""SessionClock — Unified precision monotonic and wall clock for multi-instrument telemetry."""
import time
import datetime


class SessionClock:
    """Centralized timing reference shared across all instrument logging workers."""

    def __init__(self):
        self._paused = False
        self._pause_start = 0.0
        self._pause_accum = 0.0
        self.reset()

    def start(self):
        self.reset()

    def reset(self):
        self.t0_mono = time.monotonic()
        self.t0_wall_epoch = time.time()
        self.t0_wall_iso = datetime.datetime.now().isoformat()
        self._paused = False
        self._pause_start = 0.0
        self._pause_accum = 0.0

    def pause(self):
        if not self._paused:
            self._paused = True
            self._pause_start = time.monotonic()

    def resume(self):
        if self._paused:
            self._pause_accum += time.monotonic() - self._pause_start
            self._paused = False

    def elapsed(self) -> float:
        if self._paused:
            return (self._pause_start - self.t0_mono) - self._pause_accum
        return (time.monotonic() - self.t0_mono) - self._pause_accum

    def now(self) -> float:
        return self.elapsed()

    def row_timecodes(self):
        """Returns (iso_timestamp, epoch_seconds, elapsed_seconds) tuple for a CSV row."""
        return (self.wall_iso(), self.wall_epoch(), self.elapsed())

    def formatted_time(self) -> str:
        sec = self.elapsed()
        m, s = divmod(int(sec), 60)
        h, m = divmod(m, 60)
        millis = int((sec - int(sec)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d}.{millis:03d}"

    def wall_iso(self) -> str:
        return datetime.datetime.now().isoformat()

    def wall_epoch(self) -> float:
        return time.time()
