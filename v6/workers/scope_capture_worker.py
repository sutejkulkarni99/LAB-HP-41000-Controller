"""ScopeCaptureWorker — Background acquisition worker for oscilloscope single-shot captures."""
import time
import datetime
from typing import Optional, List

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
from ..core.waveform_store import WaveformStore


class ScopeCaptureWorker(QThread):
    """
    Arms oscilloscope single-shot acquisition, waits for trigger acquisition completion (*OPC?),
    transfers raw binary waveform arrays, saves a compressed .npz archive into the session folder,
    and returns file path and waveform payload via Qt signal.
    """

    waveform_captured = pyqtSignal(str, str, dict)  # short_id, npz_path, data_dict
    capture_failed = pyqtSignal(str, str)           # short_id, error_message

    def __init__(
        self,
        instrument: InstrumentBase,
        session_dir: str,
        channels: Optional[List[int]] = None,
        parent=None
    ):
        super().__init__(parent)
        self.instrument = instrument
        self.session_dir = session_dir
        self.channels = channels or [1, 2, 3, 4]

    def run(self):
        try:
            if not self.instrument.connected:
                raise ConnectionError("Oscilloscope is not connected")

            # Arm single-shot trigger
            self.instrument.command("SINGle")
            # Wait for acquisition completion (*OPC? query)
            opc_resp = self.instrument.command("*OPC?")
            if "1" not in opc_resp:
                time.sleep(0.1)

            # Fetch waveform traces
            wave_dict = self.instrument.capture_waveform(self.channels)
            if not wave_dict:
                raise RuntimeError("No waveform data returned from instrument")

            # Save to session waveforms store
            wall_ts = datetime.datetime.now().isoformat()
            npz_path = WaveformStore.save(
                session_dir=self.session_dir,
                short_id=self.instrument.short_id,
                wall_ts=wall_ts,
                channels_dict=wave_dict
            )

            self.waveform_captured.emit(self.instrument.short_id, npz_path, wave_dict)

        except Exception as e:
            self.capture_failed.emit(self.instrument.short_id, str(e))
