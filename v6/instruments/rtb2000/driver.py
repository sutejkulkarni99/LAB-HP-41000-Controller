"""Rohde & Schwarz RTB2000 Raw SCPI TCP Driver (Port 5025)."""
import socket
import threading
import time
import re
from typing import Optional, List, Tuple, Dict, Any

try:
    import numpy as np
    HAVE_NUMPY = True
except ImportError:
    HAVE_NUMPY = False

RTB_PARAM_MAP = {
    "VPP": "UPEakvalue",
    "PKPK": "UPEakvalue",
    "RMS": "RMS",
    "MEAN": "MEAN",
    "FREQ": "FREQuency",
    "FREQUENCY": "FREQuency",
    "PER": "PERiod",
    "PERIOD": "PERiod",
    "RTIM": "RTIMe",
    "RTIME": "RTIMe",
    "FTIM": "FTIMe",
    "FTIME": "FTIMe",
    "DUTY": "PDCYcle",
    "PDCYCLE": "PDCYcle",
    "PEAK": "PEAK",
}


class RTB2000Driver:
    """
    SCPI communication driver for Rohde & Schwarz RTB2000 digital storage oscilloscopes.
    Connects via raw TCP socket on default port 5025.
    """

    def __init__(self):
        self.sock: Optional[socket.socket] = None
        self._lock = threading.RLock()
        self.connected = False
        self.ip = ""
        self.port = 5025
        self.timeout = 5.0
        self.last_roundtrip_ms = 0.0
        self._meas_slots: Dict[Tuple[int, str], int] = {}

    def connect(self, ip: str, port: int = 5025) -> bool:
        if self.connected:
            self.disconnect()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect((ip, port))
        self.ip = ip
        self.port = port
        self.connected = True
        self._meas_slots.clear()
        time.sleep(0.1)

        # Clear status and set standard format
        try:
            self.send("*CLS")
            self.send(":FORMat:DATA ASCii")
        except Exception:
            pass
        return True

    def disconnect(self):
        self.connected = False
        self._meas_slots.clear()
        with self._lock:
            sock = self.sock
            self.sock = None
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass

    def send(self, cmd: str):
        """Sends SCPI command without expecting response."""
        with self._lock:
            if not self.sock or not self.connected:
                raise ConnectionError("RTB2000 not connected")
            data = (cmd.strip() + "\n").encode("ascii")
            self.sock.sendall(data)

    def _flush_input(self):
        if not self.sock:
            return
        try:
            self.sock.setblocking(False)
            while True:
                data = self.sock.recv(4096)
                if not data:
                    break
        except Exception:
            pass
        finally:
            if self.sock:
                self.sock.setblocking(True)
                self.sock.settimeout(self.timeout)

    def query(self, cmd: str, timeout: Optional[float] = None) -> str:
        """Sends SCPI query command and reads newline-terminated response."""
        with self._lock:
            if not self.sock or not self.connected:
                raise ConnectionError("RTB2000 not connected")

            self._flush_input()
            t_start = time.perf_counter()
            data = (cmd.strip() + "\n").encode("ascii")
            self.sock.sendall(data)

            old_timeout = self.sock.gettimeout()
            if timeout:
                self.sock.settimeout(timeout)

            try:
                resp = b""
                deadline = time.time() + (timeout or self.timeout)
                while time.time() < deadline:
                    chunk = self.sock.recv(8192)
                    if not chunk:
                        break
                    resp += chunk
                    if b"\n" in resp:
                        break
                decoded = resp.decode("ascii", errors="ignore").strip()
                self.last_roundtrip_ms = (time.perf_counter() - t_start) * 1000.0
                lines = [l.strip() for l in decoded.split("\n") if l.strip()]
                return lines[-1] if lines else ""
            finally:
                if timeout:
                    self.sock.settimeout(old_timeout)

    # Core SCPI queries
    def get_idn(self) -> str:
        return self.query("*IDN?")

    def reset(self):
        self.send("*RST")

    def opc(self) -> str:
        return self.query("*OPC?", timeout=10.0)

    # Acquisition Control
    def run(self):
        self.send(":RUN")

    def stop(self):
        self.send(":STOP")

    def single(self):
        self.send(":SINGle")

    # Timebase Control
    def set_timebase_scale(self, scale_s_div: float):
        self.send(f":TIMebase:SCALe {scale_s_div:.6e}")

    def get_timebase_scale(self) -> float:
        resp = self.query(":TIMebase:SCALe?")
        try:
            return float(resp)
        except ValueError:
            return 1e-3

    def set_timebase_position(self, pos_s: float):
        self.send(f":TIMebase:POSition {pos_s:.6e}")

    def get_timebase_position(self) -> float:
        resp = self.query(":TIMebase:POSition?")
        try:
            return float(resp)
        except ValueError:
            return 0.0

    # Channel Control
    def set_channel_state(self, ch: int, state: bool):
        self.send(f":CHANnel{ch}:STATe {'1' if state else '0'}")

    def get_channel_state(self, ch: int) -> bool:
        resp = self.query(f":CHANnel{ch}:STATe?")
        return ("1" in resp or "ON" in resp.upper())

    def set_channel_scale(self, ch: int, scale_v_div: float):
        self.send(f":CHANnel{ch}:SCALe {scale_v_div:.6e}")

    def get_channel_scale(self, ch: int) -> float:
        resp = self.query(f":CHANnel{ch}:SCALe?")
        try:
            return float(resp)
        except ValueError:
            return 1.0

    def set_channel_position(self, ch: int, pos_div: float):
        self.send(f":CHANnel{ch}:POSition {pos_div:.2f}")

    def get_channel_position(self, ch: int) -> float:
        resp = self.query(f":CHANnel{ch}:POSition?")
        try:
            return float(resp)
        except ValueError:
            return 0.0

    def set_channel_coupling(self, ch: int, coupling: str):
        c = coupling.upper()
        if c in ("DC", "AC", "GND"):
            self.send(f":CHANnel{ch}:COUPling {c}")

    def get_channel_coupling(self, ch: int) -> str:
        return self.query(f":CHANnel{ch}:COUPling?")

    def set_channel_probe(self, ch: int, ratio: float):
        self.send(f":CHANnel{ch}:PROBe {ratio:.1f}")

    def get_channel_probe(self, ch: int) -> float:
        resp = self.query(f":CHANnel{ch}:PROBe?")
        try:
            return float(resp)
        except ValueError:
            return 1.0

    # Trigger Control
    def set_trigger_source(self, source: str):
        self.send(f":TRIGger:A:SOURce {source}")

    def get_trigger_source(self) -> str:
        return self.query(":TRIGger:A:SOURce?")

    def set_trigger_level(self, level_v: float, ch: int = 1):
        # ch kept for API compatibility; RTB2000 single-trigger uses unsuffixed form
        self.send(f":TRIGger:A:LEVel {level_v:.4f}")

    def get_trigger_level(self, ch: int = 1) -> float:
        resp = self.query(":TRIGger:A:LEVel?")
        try:
            return float(resp)
        except ValueError:
            return 0.0

    def set_trigger_slope(self, slope: str):
        s = "POS" if "POS" in slope.upper() else "NEG"
        self.send(f":TRIGger:A:EDGE:SLOPe {s}")

    def get_trigger_slope(self) -> str:
        return self.query(":TRIGger:A:EDGE:SLOPe?")

    def set_trigger_mode(self, mode: str):
        m = mode.upper()
        if m in ("AUTO", "NORM", "NORMAL", "SING", "SINGLE"):
            self.send(f":TRIGger:A:MODE {m[:4]}")

    def get_trigger_mode(self) -> str:
        return self.query(":TRIGger:A:MODE?")

    # Automated Measurements
    def measure_parameter(self, ch: int, param: str) -> float:
        """
        Queries instant scalar measurement with dedicated slot allocation (1..4).
        Applies RTB2000 parameter translation map and avoids compound SCPI strings.
        """
        p_clean = param.strip().upper()
        if p_clean in RTB_PARAM_MAP:
            rtb_param = RTB_PARAM_MAP[p_clean]
        elif p_clean in RTB_PARAM_MAP.values():
            rtb_param = p_clean
        else:
            raise ValueError(f"Unknown measurement parameter: {param}")

        pair = (ch, rtb_param)
        with self._lock:
            if pair not in self._meas_slots:
                used_slots = set(self._meas_slots.values())
                avail_slots = [s for s in (1, 2, 3, 4) if s not in used_slots]
                if avail_slots:
                    slot = avail_slots[0]
                else:
                    slot = 1
                    for k, s in list(self._meas_slots.items()):
                        if s == slot:
                            del self._meas_slots[k]

                self._meas_slots[pair] = slot
                self.send(f":MEASurement{slot}:SOURce CH{ch}")
                self.send(f":MEASurement{slot}:MAIN {rtb_param}")
                self.send(f":MEASurement{slot}:ENABle ON")
            else:
                slot = self._meas_slots[pair]

            resp = self.query(f":MEASurement{slot}:RESult?")

        try:
            val_str = resp.split(",")[-1].strip()
            return float(val_str)
        except Exception:
            return 0.0

    # Waveform Transfer
    def fetch_channel_waveform(self, ch: int) -> Tuple[Any, Any]:
        """
        Reads channel waveform data and returns (time_array, volt_array).
        Configures ASCII export, synchronizes with *OPC?, and queries :CHANnel<n>:DATA:HEADer? and :CHANnel<n>:DATA?
        Applies vertical Y-axis scaling: v = (raw - yorigin) * yincrement.
        """
        with self._lock:
            # Re-send :FORMat:DATA ASCii before header query
            self.send(":FORMat:DATA ASCii")

            # Parse :CHANnel<n>:DATA:HEADer?
            data_hdr = ""
            try:
                data_hdr = self.query(f":CHANnel{ch}:DATA:HEADer?")
            except Exception:
                data_hdr = ""

            x_start = -0.005
            x_stop = 0.005
            num_pts = 1000
            yincrement: Optional[float] = None
            yorigin: Optional[float] = None

            header_parsed = False
            if data_hdr:
                parts = [p.strip() for p in data_hdr.split(",")]
                try:
                    # Field order: xstart, xstop, count, xincrement, xorigin, yincrement, yorigin
                    if len(parts) >= 7:
                        x_start = float(parts[0])
                        x_stop = float(parts[1])
                        num_pts = int(float(parts[2]))
                        yincrement = float(parts[5])
                        yorigin = float(parts[6])
                        header_parsed = True
                    elif len(parts) >= 3:
                        x_start = float(parts[0])
                        x_stop = float(parts[1])
                        num_pts = int(float(parts[2]))
                except (IndexError, ValueError):
                    pass

            # Fall back to querying :CHANnel<n>:DATA:YINCrement? and :YORigin? separately
            if not header_parsed or yincrement is None or yorigin is None:
                try:
                    resp_inc = self.query(f":CHANnel{ch}:DATA:YINCrement?")
                    yincrement = float(resp_inc) if resp_inc else 1.0
                except Exception:
                    yincrement = 1.0

                try:
                    resp_orig = self.query(f":CHANnel{ch}:DATA:YORigin?")
                    yorigin = float(resp_orig) if resp_orig else 0.0
                except Exception:
                    yorigin = 0.0

            # Synchronize before read
            self.query("*OPC?", timeout=15.0)

            # Query data
            self.send(f":CHANnel{ch}:DATA?")

            raw_resp = b""
            deadline = time.time() + self.timeout
            while time.time() < deadline:
                chunk = self.sock.recv(16384)
                if not chunk:
                    break
                raw_resp += chunk
                if b"\n" in raw_resp:
                    break

            text_data = raw_resp.decode("ascii", errors="ignore").strip()
            lines = [l.strip() for l in text_data.split("\n") if l.strip()]
            data_line = lines[-1] if lines else ""

            volt_list = []
            for token in data_line.split(","):
                token = token.strip()
                if token:
                    try:
                        volt_list.append(float(token))
                    except ValueError:
                        pass

            if not volt_list:
                raise RuntimeError("no waveform data available")

            actual_n = len(volt_list)
            # Transform each value: v = (raw - yorigin) * yincrement
            if HAVE_NUMPY:
                t_arr = np.linspace(x_start, x_stop, actual_n)
                raw_arr = np.array(volt_list, dtype=float)
                v_arr = (raw_arr - yorigin) * yincrement
            else:
                dt = (x_stop - x_start) / max(1, actual_n - 1)
                t_arr = [x_start + k * dt for k in range(actual_n)]
                v_arr = [(raw - yorigin) * yincrement for raw in volt_list]

            return t_arr, v_arr
