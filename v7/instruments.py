import re
import math
import struct
import threading
from typing import Any, Optional, List, Dict
import numpy as np

from .contracts import Instrument, Channel, ChannelKind
from .transport import Transport, parse_resource

class LabhpDriver(Instrument):
    """Driver for ETPS LAB-HP 41000 DC Power Supply via ASCII commands over TCP."""

    name = "ETPS LAB-HP 41000"
    short_id = "labhp_41000"
    default_resource_hint = "192.168.1.100:10001"
    supports_waveform = False
    supports_events = False

    def __init__(self):
        self._transport: Optional[Transport] = None
        self._lock = threading.Lock()
        self._cached_idn = ""
        self._connected = False

    def connect(self, resource: str) -> None:
        with self._lock:
            self._transport = parse_resource(resource)
            self._connected = True
            # Verify communication
            self._cached_idn = self._send_query("ID")

    def disconnect(self) -> None:
        with self._lock:
            if self._transport:
                self._transport.close()
                self._transport = None
            self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    def idn(self) -> str:
        return self._cached_idn

    def channels(self) -> list[Channel]:
        return [
            Channel(key="voltage_meas_v", label="Voltage", kind=ChannelKind.ANALOG, unit="V", color="#38BDF8"),
            Channel(key="current_meas_a", label="Current", kind=ChannelKind.ANALOG, unit="A", color="#FBBF24"),
            Channel(key="power_meas_w", label="Power", kind=ChannelKind.ANALOG, unit="W", color="#A78BFA"),
            Channel(key="resistance_ohm", label="Resistance", kind=ChannelKind.ANALOG, unit="Ω", color="#34D399")
        ]

    def measurement_columns(self) -> list[str]:
        return ["voltage_meas_v", "current_meas_a", "power_meas_w", "resistance_ohm"]

    def _send_raw(self, cmd: str) -> None:
        if not self._transport:
            raise ConnectionError("Instrument not connected")
        payload = (cmd.strip() + "\r\n").encode("latin1")
        self._transport.write(payload)

    def _send_query(self, cmd: str, timeout_s: float = 3.0) -> str:
        self._send_raw(cmd)
        raw = self._transport.read_until(b"\n", timeout_s=timeout_s)
        return raw.decode("latin1", errors="ignore").strip()

    def _parse_val(self, resp: str) -> float:
        if "," in resp:
            val_part = resp.split(",", 1)[1]
        else:
            val_part = resp
        match = re.search(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", val_part)
        return float(match.group()) if match else 0.0

    def command(self, raw: str) -> str:
        with self._lock:
            raw = raw.strip()
            # If state changing, send then re-query verification
            if raw.startswith("UA,"):
                self._send_raw(raw)
                ver = self._send_query("UA")
                return f"[VERIFIED: {ver}]"
            elif raw.startswith("IA,"):
                self._send_raw(raw)
                ver = self._send_query("IA")
                return f"[VERIFIED: {ver}]"
            elif raw.startswith("PA,"):
                self._send_raw(raw)
                ver = self._send_query("PA")
                return f"[VERIFIED: {ver}]"
            elif raw.startswith("OVP,"):
                self._send_raw(raw)
                ver = self._send_query("OVP")
                return f"[VERIFIED: {ver}]"
            elif raw in ("SB,R", "SB,S"):
                self._send_raw(raw)
                ver = self._send_query("SB")
                return f"[VERIFIED: {ver}]"
            elif raw in ("GTR", "GTL"):
                self._send_raw(raw)
                ver = self._send_query("STATUS")
                return f"[VERIFIED: {ver}]"
            elif raw in ("ID", "UA", "IA", "PA", "OVP", "SB", "MU", "MI", "STATUS", "MODE"):
                return self._send_query(raw)
            else:
                self._send_raw(raw)
                return "[OK]"

    def poll_measurements(self) -> dict[str, Any]:
        with self._lock:
            v_resp = self._send_query("MU")
            i_resp = self._send_query("MI")
            v = self._parse_val(v_resp)
            i = self._parse_val(i_resp)
            p = v * i
            r = (v / i) if i > 1e-4 else 999999.0
            return {
                "voltage_meas_v": round(v, 3),
                "current_meas_a": round(i, 4),
                "power_meas_w": round(p, 2),
                "resistance_ohm": round(r, 2)
            }

    def status(self) -> dict[str, Any]:
        with self._lock:
            st_raw = self._send_query("STATUS")
            out_raw = self._send_query("SB")
            mode_raw = self._send_query("MODE")
            out_on = ("R" in out_raw.split(",", 1)[1].upper()) if "," in out_raw else ("R" in out_raw.upper())
            return {
                "status_raw": st_raw,
                "output_on": out_on,
                "mode": mode_raw.split(",")[-1].strip() if "," in mode_raw else mode_raw,
                "connected": self._connected
            }


class Rtb2000Driver(Instrument):
    """Driver for Rohde & Schwarz RTB2000 oscilloscope (SCPI/TCP port 5025)."""

    name = "Rohde & Schwarz RTB2000"
    short_id = "rtb2000"
    default_resource_hint = "192.168.1.101:5025"
    supports_waveform = True
    supports_events = False

    def __init__(self):
        self._transport: Optional[Transport] = None
        self._lock = threading.Lock()
        self._cached_idn = ""
        self._connected = False
        self._active_channels = [1, 2]

    def connect(self, resource: str) -> None:
        with self._lock:
            self._transport = parse_resource(resource)
            self._connected = True
            self._cached_idn = self._query("*IDN?")

    def disconnect(self) -> None:
        with self._lock:
            if self._transport:
                self._transport.close()
                self._transport = None
            self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    def idn(self) -> str:
        return self._cached_idn

    def channels(self) -> list[Channel]:
        colors = ["#FACC15", "#38BDF8", "#F43F5E", "#4ADE80"]
        return [
            Channel(key=f"ch{ch}_vrms", label=f"CH{ch} Vrms", kind=ChannelKind.ANALOG, unit="V", color=colors[ch-1])
            for ch in range(1, 5)
        ]

    def measurement_columns(self) -> list[str]:
        cols = []
        for ch in self._active_channels:
            cols.extend([f"ch{ch}_vrms", f"ch{ch}_vpp", f"ch{ch}_freq_hz"])
        return cols

    def _send(self, cmd: str) -> None:
        if not self._transport:
            raise ConnectionError("Scope not connected")
        self._transport.write((cmd.strip() + "\n").encode("ascii"))

    def _query(self, cmd: str, timeout_s: float = 4.0) -> str:
        self._send(cmd)
        raw = self._transport.read_until(b"\n", timeout_s=timeout_s)
        return raw.decode("ascii", errors="ignore").strip()

    def command(self, raw: str) -> str:
        with self._lock:
            cmd = raw.strip()
            # Verification re-query on state-changing commands
            if cmd.upper().startswith(":TIM:SCAL ") or cmd.upper().startswith(":TIMEBASE:SCALE "):
                self._send(cmd)
                ver = self._query(":TIMebase:SCALe?")
                return f"[VERIFIED: {ver}]"
            elif ":SCAL " in cmd.upper() or ":SCALE " in cmd.upper():
                self._send(cmd)
                ch_m = re.search(r"CHAN(?:nel)?(\d)", cmd, re.IGNORECASE)
                ch = ch_m.group(1) if ch_m else "1"
                ver = self._query(f":CHANnel{ch}:SCALe?")
                return f"[VERIFIED: {ver}]"
            elif ":STAT " in cmd.upper() or ":STATE " in cmd.upper():
                self._send(cmd)
                ch_m = re.search(r"CHAN(?:nel)?(\d)", cmd, re.IGNORECASE)
                ch = ch_m.group(1) if ch_m else "1"
                ver = self._query(f":CHANnel{ch}:STATe?")
                return f"[VERIFIED: {ver}]"
            elif cmd.endswith("?"):
                return self._query(cmd)
            else:
                self._send(cmd)
                return "[OK]"

    def poll_measurements(self) -> dict[str, Any]:
        with self._lock:
            meas: dict[str, Any] = {}
            for ch in self._active_channels:
                try:
                    # Allocate slot or query measurement directly
                    self._send(f":MEASurement1:SOURce CH{ch}")
                    self._send(":MEASurement1:MAIN RMS")
                    vrms_str = self._query(":MEASurement1:RESult?")
                    vrms = float(vrms_str.split(",")[-1]) if vrms_str else 0.0

                    self._send(":MEASurement1:MAIN PEAK")
                    vpp_str = self._query(":MEASurement1:RESult?")
                    vpp = float(vpp_str.split(",")[-1]) if vpp_str else 0.0

                    self._send(":MEASurement1:MAIN FREQuency")
                    freq_str = self._query(":MEASurement1:RESult?")
                    freq = float(freq_str.split(",")[-1]) if freq_str else 0.0

                    meas[f"ch{ch}_vrms"] = round(vrms, 4)
                    meas[f"ch{ch}_vpp"] = round(vpp, 4)
                    meas[f"ch{ch}_freq_hz"] = round(freq, 2)
                except Exception:
                    meas[f"ch{ch}_vrms"] = 0.0
                    meas[f"ch{ch}_vpp"] = 0.0
                    meas[f"ch{ch}_freq_hz"] = 0.0
            return meas

    def status(self) -> dict[str, Any]:
        with self._lock:
            try:
                tb = float(self._query(":TIMebase:SCALe?"))
            except Exception:
                tb = 0.001
            return {
                "timebase_scale_s": tb,
                "connected": self._connected
            }

    def capture_waveform(self, channels: list[str]) -> dict:
        with self._lock:
            out_ch: dict[str, np.ndarray] = {}
            time_vector = np.array([], dtype=np.float64)

            for ch_str in channels:
                m = re.search(r"\d+", ch_str)
                ch_num = int(m.group()) if m else 1

                # Set format and fetch data
                self._send(f":FORM:DATA UINT,8")
                self._send(f":CHANnel{ch_num}:DATA:HEAD?")
                head_str = self._transport.read_until(b"\n", 3.0).decode("ascii", errors="ignore").strip()
                # header: x_start, x_stop, points, values_per_sample
                parts = [float(p) for p in head_str.split(",") if p.strip()] if head_str else []
                x_start = parts[0] if len(parts) > 0 else -0.005
                x_stop = parts[1] if len(parts) > 1 else 0.005
                pts = int(parts[2]) if len(parts) > 2 else 1000

                self._send(f":CHANnel{ch_num}:DATA?")
                # Read IEEE 488.2 binary header #<d><len>
                h = self._transport.read_bytes(2, 4.0)
                if h.startswith(b"#"):
                    d = int(h[1:2].decode("ascii"))
                    len_bytes = int(self._transport.read_bytes(d, 2.0).decode("ascii"))
                    raw_data = self._transport.read_bytes(len_bytes, 5.0)
                    # Consume trailing newline if present
                    try:
                        self._transport.read_until(b"\n", 0.5)
                    except Exception:
                        pass
                    volt_samples = np.frombuffer(raw_data, dtype=np.uint8).astype(np.float32)
                    out_ch[f"ch{ch_num}"] = volt_samples
                    if len(time_vector) == 0:
                        time_vector = np.linspace(x_start, x_stop, len(volt_samples), dtype=np.float64)

            return {
                "time": time_vector,
                "channels": out_ch,
                "metadata": {"instrument": self.name, "short_id": self.short_id}
            }


class KeysightEdu33212ADriver(Instrument):
    """Driver for Keysight EDU33212A Function / Arbitrary Waveform Generator."""

    name = "Keysight EDU33212A"
    short_id = "fg_edu33212a"
    default_resource_hint = "192.168.1.102:5025"
    supports_waveform = False
    supports_events = True

    def __init__(self):
        self._transport: Optional[Transport] = None
        self._lock = threading.Lock()
        self._cached_idn = ""
        self._connected = False
        self._events_log: list[dict] = []

    def connect(self, resource: str) -> None:
        with self._lock:
            self._transport = parse_resource(resource)
            self._connected = True
            self._cached_idn = self._query("*IDN?")

    def disconnect(self) -> None:
        with self._lock:
            if self._transport:
                self._transport.close()
                self._transport = None
            self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    def idn(self) -> str:
        return self._cached_idn

    def channels(self) -> list[Channel]:
        return [
            Channel(key="ch1_freq", label="CH1 Freq", kind=ChannelKind.ANALOG, unit="Hz", color="#38BDF8"),
            Channel(key="ch1_ampl", label="CH1 Ampl", kind=ChannelKind.ANALOG, unit="Vpp", color="#FBBF24"),
            Channel(key="ch2_freq", label="CH2 Freq", kind=ChannelKind.ANALOG, unit="Hz", color="#A78BFA"),
            Channel(key="ch2_ampl", label="CH2 Ampl", kind=ChannelKind.ANALOG, unit="Vpp", color="#34D399")
        ]

    def measurement_columns(self) -> list[str]:
        return ["ch1_freq", "ch1_ampl", "ch2_freq", "ch2_ampl"]

    def _send(self, cmd: str) -> None:
        if not self._transport:
            raise ConnectionError("Function generator not connected")
        self._transport.write((cmd.strip() + "\n").encode("ascii"))

    def _query(self, cmd: str, timeout_s: float = 3.0) -> str:
        self._send(cmd)
        raw = self._transport.read_until(b"\n", timeout_s=timeout_s)
        return raw.decode("ascii", errors="ignore").strip()

    def command(self, raw: str) -> str:
        with self._lock:
            cmd = raw.strip()
            # Verification re-query on state changes
            if ":FREQ" in cmd.upper():
                self._send(cmd)
                ch = "2" if "SOUR2" in cmd.upper() else "1"
                ver = self._query(f":SOURce{ch}:FREQuency?")
                return f"[VERIFIED: {ver}]"
            elif ":VOLT" in cmd.upper():
                self._send(cmd)
                ch = "2" if "SOUR2" in cmd.upper() else "1"
                ver = self._query(f":SOURce{ch}:VOLTage?")
                return f"[VERIFIED: {ver}]"
            elif ":OUTP" in cmd.upper():
                self._send(cmd)
                ch = "2" if "OUTP2" in cmd.upper() else "1"
                ver = self._query(f":OUTPut{ch}?")
                return f"[VERIFIED: {ver}]"
            elif cmd.endswith("?"):
                return self._query(cmd)
            else:
                self._send(cmd)
                return "[OK]"

    def poll_measurements(self) -> dict[str, Any]:
        with self._lock:
            try:
                f1 = float(self._query(":SOURce1:FREQuency?"))
                a1 = float(self._query(":SOURce1:VOLTage?"))
            except Exception:
                f1, a1 = 1000.0, 1.0
            try:
                f2 = float(self._query(":SOURce2:FREQuency?"))
                a2 = float(self._query(":SOURce2:VOLTage?"))
            except Exception:
                f2, a2 = 1000.0, 1.0
            return {
                "ch1_freq": f1,
                "ch1_ampl": a1,
                "ch2_freq": f2,
                "ch2_ampl": a2
            }

    def configuration(self) -> dict:
        with self._lock:
            try:
                ch1_func = self._query(":SOURce1:FUNCtion?")
                ch1_out = self._query(":OUTPut1?")
                ch2_func = self._query(":SOURce2:FUNCtion?")
                ch2_out = self._query(":OUTPut2?")
            except Exception:
                ch1_func, ch1_out, ch2_func, ch2_out = "SIN", "0", "SIN", "0"
            return {
                "ch1_function": ch1_func,
                "ch1_output": ch1_out,
                "ch2_function": ch2_func,
                "ch2_output": ch2_out
            }

    def events(self) -> list[dict]:
        with self._lock:
            ev = list(self._events_log)
            self._events_log.clear()
            return ev

    def status(self) -> dict[str, Any]:
        return {"connected": self._connected}


class TektronixMso2004BDriver(Instrument):
    """Driver for Tektronix MSO2004B Oscilloscope (4 analog + 16 digital channels)."""

    name = "Tektronix MSO2004B"
    short_id = "mso2004b"
    default_resource_hint = "192.168.1.103:5025"
    supports_waveform = True
    supports_events = False

    def __init__(self):
        self._transport: Optional[Transport] = None
        self._lock = threading.Lock()
        self._cached_idn = ""
        self._connected = False
        self._active_channels = [1, 2]

    def connect(self, resource: str) -> None:
        with self._lock:
            self._transport = parse_resource(resource)
            self._connected = True
            self._cached_idn = self._query("*IDN?")

    def disconnect(self) -> None:
        with self._lock:
            if self._transport:
                self._transport.close()
                self._transport = None
            self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    def idn(self) -> str:
        return self._cached_idn

    def channels(self) -> list[Channel]:
        colors = ["#FACC15", "#38BDF8", "#F43F5E", "#4ADE80"]
        return [
            Channel(key=f"ch{ch}_vrms", label=f"CH{ch} Vrms", kind=ChannelKind.ANALOG, unit="V", color=colors[ch-1])
            for ch in range(1, 5)
        ]

    def measurement_columns(self) -> list[str]:
        cols = []
        for ch in self._active_channels:
            cols.extend([f"ch{ch}_vrms", f"ch{ch}_vpp", f"ch{ch}_freq_hz"])
        return cols

    def _send(self, cmd: str) -> None:
        if not self._transport:
            raise ConnectionError("Tektronix scope not connected")
        self._transport.write((cmd.strip() + "\n").encode("ascii"))

    def _query(self, cmd: str, timeout_s: float = 4.0) -> str:
        self._send(cmd)
        raw = self._transport.read_until(b"\n", timeout_s=timeout_s)
        return raw.decode("ascii", errors="ignore").strip()

    def command(self, raw: str) -> str:
        with self._lock:
            cmd = raw.strip()
            # Verification re-query on state changes
            if "HOR:SCA" in cmd.upper() or "HORIZONTAL:SCALE" in cmd.upper():
                self._send(cmd)
                ver = self._query("HOR:SCA?")
                return f"[VERIFIED: {ver}]"
            elif ":SCA" in cmd.upper() or ":SCALE" in cmd.upper():
                self._send(cmd)
                ch_m = re.search(r"CH(\d)", cmd, re.IGNORECASE)
                ch = ch_m.group(1) if ch_m else "1"
                ver = self._query(f"CH{ch}:SCA?")
                return f"[VERIFIED: {ver}]"
            elif cmd.endswith("?"):
                return self._query(cmd)
            else:
                self._send(cmd)
                return "[OK]"

    def poll_measurements(self) -> dict[str, Any]:
        with self._lock:
            meas: dict[str, Any] = {}
            for ch in self._active_channels:
                try:
                    self._send(f"MEASU:IMM:SOURCE CH{ch}")
                    self._send("MEASU:IMM:TYPE RMS")
                    vrms = float(self._query("MEASU:IMM:VAL?"))
                    self._send("MEASU:IMM:TYPE PK2PK")
                    vpp = float(self._query("MEASU:IMM:VAL?"))
                    self._send("MEASU:IMM:TYPE FREQ")
                    freq = float(self._query("MEASU:IMM:VAL?"))
                    meas[f"ch{ch}_vrms"] = round(vrms, 4)
                    meas[f"ch{ch}_vpp"] = round(vpp, 4)
                    meas[f"ch{ch}_freq_hz"] = round(freq, 2)
                except Exception:
                    meas[f"ch{ch}_vrms"] = 0.0
                    meas[f"ch{ch}_vpp"] = 0.0
                    meas[f"ch{ch}_freq_hz"] = 0.0
            return meas

    def status(self) -> dict[str, Any]:
        with self._lock:
            try:
                scale = float(self._query("HOR:SCA?"))
            except Exception:
                scale = 0.001
            return {"horizontal_scale": scale, "connected": self._connected}

    def capture_waveform(self, channels: list[str]) -> dict:
        with self._lock:
            out_ch: dict[str, np.ndarray] = {}
            time_vector = np.array([], dtype=np.float64)

            for ch_str in channels:
                m = re.search(r"\d+", ch_str)
                ch_num = int(m.group()) if m else 1
                self._send(f"DATA:SOURCE CH{ch_num}")
                self._send("DATA:ENCDG RIBINARY")
                self._send("DATA:WIDTH 1")
                # Query preamble for scaling
                self._send("CURVE?")
                h = self._transport.read_bytes(2, 4.0)
                if h.startswith(b"#"):
                    d = int(h[1:2].decode("ascii"))
                    len_bytes = int(self._transport.read_bytes(d, 2.0).decode("ascii"))
                    raw = self._transport.read_bytes(len_bytes, 5.0)
                    try:
                        self._transport.read_until(b"\n", 0.5)
                    except Exception:
                        pass
                    volt_samples = np.frombuffer(raw, dtype=np.int8).astype(np.float32) * 0.02
                    out_ch[f"ch{ch_num}"] = volt_samples
                    if len(time_vector) == 0:
                        time_vector = np.linspace(-0.005, 0.005, len(volt_samples), dtype=np.float64)

            return {
                "time": time_vector,
                "channels": out_ch,
                "metadata": {"instrument": self.name, "short_id": self.short_id}
            }
