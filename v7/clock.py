import time
from datetime import datetime, timezone

class SessionClock:
    """Monotonic session clock providing synchronised wall and elapsed timecodes."""

    def __init__(self):
        self._start_perf: float = time.perf_counter()
        self._paused_perf: float = 0.0
        self._accumulated_paused: float = 0.0
        self._is_paused: bool = False

    def reset(self) -> None:
        """Reset elapsed time counter to zero."""
        self._start_perf = time.perf_counter()
        self._paused_perf = 0.0
        self._accumulated_paused = 0.0
        self._is_paused = False

    def pause(self) -> None:
        """Pause the elapsed time accumulation."""
        if not self._is_paused:
            self._is_paused = True
            self._paused_perf = time.perf_counter()

    def resume(self) -> None:
        """Resume elapsed time accumulation."""
        if self._is_paused:
            self._is_paused = False
            self._accumulated_paused += time.perf_counter() - self._paused_perf
            self._paused_perf = 0.0

    def elapsed(self) -> float:
        """Current session elapsed seconds."""
        if self._is_paused:
            return max(0.0, self._paused_perf - self._start_perf - self._accumulated_paused)
        return max(0.0, time.perf_counter() - self._start_perf - self._accumulated_paused)

    def wall_iso(self) -> str:
        """Current ISO-8601 UTC timestamp."""
        return datetime.now(timezone.utc).isoformat()

    def wall_epoch(self) -> float:
        """Current UNIX epoch timestamp with fractional seconds."""
        return time.time()

    def row_timecodes(self) -> tuple[str, float, float]:
        """Returns canonical (wall_iso, wall_epoch, elapsed_s) tuple for CSV logging."""
        return (self.wall_iso(), self.wall_epoch(), round(self.elapsed(), 6))
