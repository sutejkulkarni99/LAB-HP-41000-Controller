import os
import json
import csv
import time
from typing import Dict, Any, List, Optional
import numpy as np

from PySide6.QtCore import QObject, Signal, Slot, Property, QTimer

try:
    from v7.contracts import Instrument
    from v7.clock import SessionClock
    from v7.session import LoggingSession
    from v7.waveform import WaveformStore
    from v7.workers import TelemetryWorker
    from v7.transport import parse_resource
    from v7.instruments import (
        LabhpDriver,
        Rtb2000Driver,
        KeysightEdu33212ADriver,
        TektronixMso2004BDriver
    )
except ImportError:
    from contracts import Instrument
    from clock import SessionClock
    from session import LoggingSession
    from waveform import WaveformStore
    from workers import TelemetryWorker
    from transport import parse_resource
    from instruments import (
        LabhpDriver,
        Rtb2000Driver,
        KeysightEdu33212ADriver,
        TektronixMso2004BDriver
    )

class InstrumentsBridge(QObject):
    """Bridge coordinating instrument connections, live telemetry, and control."""

    instrumentConnected = Signal(str)
    instrumentDisconnected = Signal(str)
    connectionFailed = Signal(str, str)
    telemetryUpdated = Signal(str, 'QVariantMap')
    statusUpdated = Signal(str, 'QVariantMap')
    waveformUpdated = Signal(str, 'QVariantMap')

    def __init__(self, instruments: dict[str, Instrument] = None, parent=None):
        super().__init__(parent)
        self._instruments: dict[str, Instrument] = instruments if instruments is not None else {}
        self.instruments = self._instruments
        self._workers: dict[str, TelemetryWorker] = {}
        self._waveform_timers: dict[str, QTimer] = {}

    def _capture_and_emit(self, short_id: str) -> None:
        inst = self._instruments.get(short_id)
        if not inst or not getattr(inst, "connected", False):
            return
        try:
            channels = ["ch1", "ch2", "ch3", "ch4"]
            wf = inst.capture_waveform(channels)
            wave_dict: Dict[str, Any] = {}

            t_data = wf.get("time", [])
            if isinstance(t_data, np.ndarray):
                t_list = t_data.tolist()
            elif isinstance(t_data, (list, tuple)):
                t_list = list(t_data)
            else:
                t_list = []
            wave_dict["time"] = t_list

            raw_channels = wf.get("channels", {}) if isinstance(wf.get("channels"), dict) else {}
            for ch in ["ch1", "ch2", "ch3", "ch4"]:
                val = None
                if ch in wf:
                    val = wf[ch]
                elif ch.upper() in wf:
                    val = wf[ch.upper()]
                elif ch in raw_channels:
                    val = raw_channels[ch]
                elif ch.upper() in raw_channels:
                    val = raw_channels[ch.upper()]

                if val is not None:
                    if isinstance(val, np.ndarray):
                        v_list = val.tolist()
                    elif isinstance(val, (list, tuple)):
                        v_list = list(val)
                    else:
                        v_list = []
                    wave_dict[ch] = v_list
                    wave_dict[ch.upper()] = v_list

            wave_dict["channels"] = {k: v for k, v in wave_dict.items() if k.startswith("ch") or k.startswith("CH")}
            if "metadata" in wf:
                wave_dict["metadata"] = wf["metadata"]

            self.waveformUpdated.emit(short_id, wave_dict)
        except Exception:
            pass

    @Slot(str, str)
    def requestConnect(self, short_id: str, hint: str) -> None:
        inst = self._instruments.get(short_id)
        if inst and inst.connected:
            return
        try:
            if not inst:
                if short_id == "labhp_41000":
                    inst = LabhpDriver()
                elif short_id == "rtb2000":
                    inst = Rtb2000Driver()
                elif short_id == "mso2004b":
                    inst = TektronixMso2004BDriver()
                elif short_id == "fg_edu33212a":
                    inst = KeysightEdu33212ADriver()
                else:
                    inst = LabhpDriver()
                self._instruments[short_id] = inst
                self.instruments[short_id] = inst

            try:
                transport = parse_resource(hint)
                inst.connect(hint)
            except Exception:
                inst.connect(hint)

            worker = TelemetryWorker(inst, interval_s=0.2)
            worker.measurements.connect(self._on_measurements)
            worker.connection_lost.connect(self._on_connection_lost)
            self._workers[short_id] = worker
            worker.start()

            # Start waveform capture loop for scope instruments
            if getattr(inst, "supports_waveform", False) or short_id in {"rtb2000", "mso2004b"}:
                if short_id in self._waveform_timers:
                    self._waveform_timers[short_id].stop()
                    del self._waveform_timers[short_id]
                timer = QTimer(self)
                timer.setInterval(1000)
                timer.timeout.connect(lambda s=short_id: self._capture_and_emit(s))
                self._waveform_timers[short_id] = timer
                timer.start()
                # Immediate initial capture
                QTimer.singleShot(50, lambda s=short_id: self._capture_and_emit(s))

            self.instrumentConnected.emit(short_id)
        except Exception as e:
            self.connectionFailed.emit(short_id, str(e))

    @Slot(str)
    def requestDisconnect(self, short_id: str) -> None:
        if short_id in self._waveform_timers:
            self._waveform_timers[short_id].stop()
            del self._waveform_timers[short_id]
        if short_id in self._workers:
            self._workers[short_id].stop()
            del self._workers[short_id]
        inst = self._instruments.get(short_id)
        if inst:
            inst.disconnect()
        self.instrumentDisconnected.emit(short_id)

    @Slot(str, dict)
    def _on_measurements(self, short_id: str, values: dict) -> None:
        self.telemetryUpdated.emit(short_id, values)

    @Slot(str, str)
    def _on_connection_lost(self, short_id: str, err: str) -> None:
        self.connectionFailed.emit(short_id, err)
        self.requestDisconnect(short_id)

    @Slot(str, str)
    def connectInstrument(self, short_id: str, resource: str) -> None:
        self.requestConnect(short_id, resource)

    @Slot(str)
    def disconnectInstrument(self, short_id: str) -> None:
        self.requestDisconnect(short_id)

    @Slot(str, str, 'QVariant')
    @Slot(str, str)
    def setScopeControl(self, short_id: str, key: str, value: Any = 0) -> None:
        inst = self._instruments.get(short_id)
        if not inst:
            return
        k = str(key).lower()
        try:
            if k == "run":
                if hasattr(inst, "run"):
                    inst.run()
            elif k == "stop":
                if hasattr(inst, "stop"):
                    inst.stop()
            elif k == "single":
                if hasattr(inst, "single"):
                    inst.single()
            elif k == "autoset":
                if hasattr(inst, "autoset"):
                    inst.autoset()
        except Exception:
            pass

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
    clockChanged = Signal()
    rowCountsChanged = Signal()
    runningChanged = Signal()
    pausedChanged = Signal()

    def __init__(self, session: Optional[LoggingSession] = None, clock: Optional[SessionClock] = None, instruments: Optional[dict[str, Instrument]] = None, parent=None):
        super().__init__(parent)
        self._clock = clock if clock is not None else SessionClock()
        self.clock = self._clock
        self._session = session
        self.session = self._session
        self.instruments: dict[str, Instrument] = instruments if instruments is not None else {}

        self._running = False
        self._paused = False
        self._row_counts: dict[str, int] = {}
        self._session_dir = ""

        if self._session:
            self._wire_session(self._session)

        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._on_timer_tick)
        self._timer.start()

    def _wire_session(self, session: LoggingSession) -> None:
        try:
            session.started.connect(self._on_started)
        except Exception:
            pass
        try:
            session.stopped.connect(self._on_stopped)
        except Exception:
            pass
        try:
            session.row.connect(self._on_row)
        except Exception:
            pass

    def _on_timer_tick(self) -> None:
        self.clockUpdated.emit()
        self.clockChanged.emit()

    def _on_started(self, d: str) -> None:
        self._running = True
        self._paused = False
        self.runningChanged.emit()
        self.pausedChanged.emit()
        self.sessionStarted.emit(d)

    def _on_stopped(self, d: str, m: dict) -> None:
        self._running = False
        self._paused = False
        self.runningChanged.emit()
        self.pausedChanged.emit()
        self.sessionStopped.emit(d, m)

    def _on_row(self, short_id: str, count: int, preview: str = "") -> None:
        self._row_counts[short_id] = count
        self.rowLogged.emit(short_id, count, str(preview))
        self.rowCountsChanged.emit()
        self.clockUpdated.emit()

    @Property(bool, notify=runningChanged)
    def running(self) -> bool:
        return self._running

    @Property(bool, notify=pausedChanged)
    def paused(self) -> bool:
        return self._paused

    @Property(float, notify=clockUpdated)
    def elapsed(self) -> float:
        return round(self._clock.elapsed(), 2) if hasattr(self._clock, "elapsed") else 0.0

    @Property(str, notify=clockUpdated)
    def clockLabel(self) -> str:
        if hasattr(self._clock, "formatted_time"):
            try:
                return self._clock.formatted_time()
            except Exception:
                pass
        secs = self._clock.elapsed() if hasattr(self._clock, "elapsed") else 0.0
        total_s = int(secs)
        m, s = divmod(total_s, 60)
        h, m = divmod(m, 60)
        ms = int((secs - total_s) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

    @Property('QVariantMap', notify=rowCountsChanged)
    def rowCounts(self) -> dict:
        return self._row_counts

    @Slot(str, 'QVariantList')
    @Slot('QVariantList')
    @Slot()
    def startSession(self, session_dir: str = "", specs: list = None) -> None:
        if specs is None:
            if isinstance(session_dir, list):
                specs = session_dir
                session_dir = ""
            else:
                specs = []

        inst_list = []
        for item in specs:
            if isinstance(item, dict):
                s_id = item.get("short_id")
                interval = float(item.get("interval_s", 0.1))
                inst = self.instruments.get(s_id)
                if inst and getattr(inst, "connected", False):
                    inst_list.append((inst, interval))

        timestamped_name = "session_" + time.strftime("%Y%m%d_%H%M%S")
        if not session_dir:
            resolved_dir = os.path.abspath(os.path.join("..", "sessions", timestamped_name))
        elif not os.path.isabs(session_dir):
            resolved_dir = os.path.abspath(os.path.join("..", "sessions", session_dir))
        else:
            resolved_dir = session_dir

        self._session_dir = resolved_dir
        self._row_counts.clear()
        self.rowCountsChanged.emit()

        self._session = LoggingSession(self._clock)
        self.session = self._session
        self._wire_session(self._session)

        if hasattr(self._session, "set_metadata"):
            try:
                self._session.set_metadata({})
            except Exception:
                pass

        os.makedirs(self._session_dir, exist_ok=True)
        self._session.start(self._session_dir, inst_list)
        self._running = True
        self._paused = False
        self.runningChanged.emit()
        self.pausedChanged.emit()
        self.sessionStarted.emit(self._session_dir)

    @Slot()
    def pauseSession(self) -> None:
        if self._session:
            self._session.pause()
        self._paused = True
        self.pausedChanged.emit()

    @Slot()
    def resumeSession(self) -> None:
        if self._session:
            self._session.resume()
        self._paused = False
        self.pausedChanged.emit()

    @Slot()
    def stopSession(self) -> None:
        if self._session:
            self._session.stop()
        self._running = False
        self._paused = False
        self.runningChanged.emit()
        self.pausedChanged.emit()
        self.sessionStopped.emit(self._session_dir, {})


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
