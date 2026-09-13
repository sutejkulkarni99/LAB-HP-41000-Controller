import os
import json
import csv
import time
from typing import Dict, Any, List, Optional
import numpy as np

from PySide6.QtCore import QObject, Signal, Slot, Property, QTimer

from .contracts import Instrument
from .clock import SessionClock
from .session import LoggingSession
from .waveform import WaveformStore
from .workers import TelemetryWorker

class InstrumentsBridge(QObject):
    """Bridge coordinating instrument connections, live telemetry, and control."""

    instrumentConnected = Signal(str)
    instrumentDisconnected = Signal(str)
    telemetryUpdated = Signal(str, 'QVariantMap')
    statusUpdated = Signal(str, 'QVariantMap')
    waveformUpdated = Signal(str, 'QVariantMap')

    def __init__(self, instruments: dict[str, Instrument], parent=None):
        super().__init__(parent)
        self.instruments = instruments
        self._workers: dict[str, TelemetryWorker] = {}

    @Slot(str, str)
    def connectInstrument(self, short_id: str, resource: str) -> None:
        inst = self.instruments.get(short_id)
        if not inst:
            return
        try:
            inst.connect(resource)
            self.instrumentConnected.emit(short_id)
            # Start telemetry worker querying real hardware
            worker = TelemetryWorker(inst, interval_s=0.2)
            worker.measurements.connect(lambda s_id, m: self.telemetryUpdated.emit(s_id, m))
            worker.status.connect(lambda s_id, s: self.statusUpdated.emit(s_id, s))
            worker.connection_lost.connect(lambda s_id, _: self.disconnectInstrument(s_id))
            self._workers[short_id] = worker
            worker.start()
        except Exception as e:
            self.statusUpdated.emit(short_id, {"error": str(e), "connected": False})

    @Slot(str)
    def disconnectInstrument(self, short_id: str) -> None:
        if short_id in self._workers:
            self._workers[short_id].stop()
            del self._workers[short_id]
        inst = self.instruments.get(short_id)
        if inst:
            inst.disconnect()
            self.instrumentDisconnected.emit(short_id)

    @Slot(str, 'QStringList')
    def captureWaveform(self, short_id: str, channels: list) -> None:
        inst = self.instruments.get(short_id)
        if not inst or not inst.connected or not inst.supports_waveform:
            return
        try:
            wf = inst.capture_waveform(list(channels))
            ch_data = {}
            for k, v in wf.get("channels", {}).items():
                ch_data[k] = v.tolist() if isinstance(v, np.ndarray) else list(v)
            t_data = wf.get("time", [])
            t_list = t_data.tolist() if isinstance(t_data, np.ndarray) else list(t_data)
            self.waveformUpdated.emit(short_id, {
                "time": t_list,
                "channels": ch_data,
                "metadata": wf.get("metadata", {})
            })
        except Exception:
            pass

    @Slot(str, float)
    def setPsuSetpoint(self, kind: str, value: float) -> None:
        psu = self.instruments.get("labhp_41000")
        if not psu or not psu.connected:
            return
        kind_clean = kind.lower()
        if "volt" in kind_clean:
            psu.command(f"UA,{value:.2f}")
        elif "curr" in kind_clean:
            psu.command(f"IA,{value:.4f}")
        elif "pow" in kind_clean:
            psu.command(f"PA,{value:.2f}")
        elif "ovp" in kind_clean:
            psu.command(f"OVP,{value:.1f}")

    @Slot(str, str, 'QVariant')
    def setScopeControl(self, short_id: str, key: str, value: Any) -> None:
        inst = self.instruments.get(short_id)
        if not inst or not inst.connected:
            return
        key_u = key.upper()
        if "TIMEBASE" in key_u or "SCALE" in key_u:
            inst.command(f":TIMebase:SCALe {float(value):.6e}")
        elif "CH1_SCALE" in key_u:
            inst.command(f":CHANnel1:SCALe {float(value):.4e}")
        elif "CH2_SCALE" in key_u:
            inst.command(f":CHANnel2:SCALe {float(value):.4e}")
        elif "RUN" in key_u:
            inst.command(":RUN" if value else ":STOP")

    @Slot(str, str, result=str)
    def sendRawCommand(self, short_id: str, cmd: str) -> str:
        inst = self.instruments.get(short_id)
        if not inst or not inst.connected:
            return "[DISCONNECTED]"
        try:
            return inst.command(cmd)
        except Exception as e:
            return f"[ERROR: {e}]"


class SessionBridge(QObject):
    """Bridge for session lifecycle management, shared clock, and manifest tracking."""

    sessionStarted = Signal(str)
    sessionStopped = Signal(str, 'QVariantMap')
    rowLogged = Signal(str, int, str)
    clockUpdated = Signal()

    def __init__(self, session: LoggingSession, clock: SessionClock, instruments: dict[str, Instrument], parent=None):
        super().__init__(parent)
        self.session = session
        self.clock = clock
        self.instruments = instruments

        self._running = False
        self._paused = False
        self._row_counts: dict[str, int] = {}

        self.session.started.connect(self._on_started)
        self.session.stopped.connect(self._on_stopped)
        self.session.row.connect(self._on_row)

        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self.clockUpdated.emit)
        self._timer.start()

    def _on_started(self, d: str):
        self._running = True
        self._paused = False
        self.sessionStarted.emit(d)

    def _on_stopped(self, d: str, m: dict):
        self._running = False
        self._paused = False
        self.sessionStopped.emit(d, m)

    def _on_row(self, short_id: str, count: int, ts: str):
        self._row_counts[short_id] = count
        self.rowLogged.emit(short_id, count, ts)

    @Property(bool, notify=clockUpdated)
    def running(self) -> bool:
        return self._running

    @Property(bool, notify=clockUpdated)
    def paused(self) -> bool:
        return self._paused

    @Property(float, notify=clockUpdated)
    def elapsed(self) -> float:
        return round(self.clock.elapsed(), 2)

    @Property(str, notify=clockUpdated)
    def clockLabel(self) -> str:
        if not self._running:
            return "00:00:00.000"
        secs = int(self.clock.elapsed())
        m, s = divmod(secs, 60)
        h, m = divmod(m, 60)
        ms = int((self.clock.elapsed() - secs) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

    @Property('QVariantMap', notify=clockUpdated)
    def rowCounts(self) -> dict:
        return self._row_counts

    @Slot(str, 'QVariantList')
    def startSession(self, directory: str, instrument_configs: list) -> None:
        inst_tuples = []
        for item in instrument_configs:
            s_id = item.get("short_id")
            interval = float(item.get("interval_s", 0.1))
            inst = self.instruments.get(s_id)
            if inst and inst.connected:
                inst_tuples.append((inst, interval))

        if not directory:
            ts = time.strftime("%Y%m%d_%H%M%S")
            directory = os.path.join("sessions", f"session_{ts}")
        self.session.start(directory, inst_tuples)

    @Slot()
    def pauseSession(self) -> None:
        self.session.pause()
        self._paused = True

    @Slot()
    def resumeSession(self) -> None:
        self.session.resume()
        self._paused = False

    @Slot()
    def stopSession(self) -> None:
        self.session.stop()


class ArchiveBridge(QObject):
    """Bridge loading past sessions, plotting synchronized signals, and reviewing waveforms."""

    sessionLoaded = Signal(str)
    plotUpdated = Signal()
    cursorMoved = Signal(float, 'QVariantMap')

    def __init__(self, parent=None):
        super().__init__(parent)
        self._session_dir = ""
        self._tree_model: list[dict] = []
        self._cursor_values: dict[str, float] = {}
        self._step_boundaries: list[dict] = []
        self._waveform_markers: list[dict] = []
        self._loaded_series: dict[str, tuple[np.ndarray, np.ndarray]] = {}

    @Property('QVariantList', notify=sessionLoaded)
    def treeModel(self) -> list:
        return self._tree_model

    @Property('QVariantMap', notify=cursorMoved)
    def cursorValues(self) -> dict:
        return self._cursor_values

    @Property('QVariantList', notify=plotUpdated)
    def stepBoundaries(self) -> list:
        return self._step_boundaries

    @Property('QVariantList', notify=plotUpdated)
    def waveformMarkers(self) -> list:
        return self._waveform_markers

    @Slot(str)
    def openSession(self, directory: str) -> None:
        self._session_dir = os.path.abspath(directory)
        self._tree_model.clear()
        self._loaded_series.clear()
        self._step_boundaries.clear()
        self._waveform_markers.clear()

        # Parse CSVs in the session directory
        if os.path.exists(self._session_dir):
            for fname in os.listdir(self._session_dir):
                if fname.endswith(".csv") and fname not in ("events.csv", "waveforms.csv"):
                    short_id = fname[:-4]
                    csv_path = os.path.join(self._session_dir, fname)
                    channels = []
                    try:
                        with open(csv_path, "r", encoding="utf-8") as f:
                            reader = csv.reader(f)
                            headers = next(reader)
                            # headers: iso_timestamp, epoch_s, elapsed_s, <cols...>
                            cols = headers[3:]
                            for col in cols:
                                channels.append({"key": f"{short_id}.{col}", "label": col, "enabled": True})
                    except Exception:
                        pass
                    self._tree_model.append({"instrument": short_id, "channels": channels})

            # Check for waveform markers
            wf_csv = os.path.join(self._session_dir, "waveforms.csv")
            if os.path.exists(wf_csv):
                try:
                    with open(wf_csv, "r", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for r in reader:
                            self._waveform_markers.append({
                                "elapsed_s": float(r.get("elapsed_s", 0.0)),
                                "instrument": r.get("instrument", ""),
                                "path": r.get("npz_path", "")
                            })
                except Exception:
                    pass

        self.sessionLoaded.emit(self._session_dir)
        self.plotUpdated.emit()

    @Slot(str, 'QStringList')
    def setChannelEnabled(self, short_id: str, channels: list[str]) -> None:
        self.plotUpdated.emit()

    @Slot(float, float)
    def zoomTo(self, t0: float, t1: float) -> None:
        self.plotUpdated.emit()

    @Slot(str, str)
    def exportPlot(self, kind: str, path: str) -> None:
        pass

    @Slot(str, result='QVariantMap')
    def loadWaveform(self, npz_path: str) -> dict:
        try:
            data = WaveformStore.load_npz(npz_path)
            # return summary
            return {
                "sample_count": len(data.get("time", [])),
                "channel_keys": list(data.get("channels", {}).keys()),
                "metadata": data.get("metadata", {})
            }
        except Exception as e:
            return {"error": str(e)}


class ThemeBridge(QObject):
    """Bridge for runtime Dark (Polaris) / Light theme switching."""

    themeChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_dark = True

    @Property(bool, notify=themeChanged)
    def isDark(self) -> bool:
        return self._is_dark

    @Slot()
    def toggleTheme(self) -> None:
        self._is_dark = not self._is_dark
        self.themeChanged.emit()
