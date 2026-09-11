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
            val = float(val_str)
            # RTB2000 returns 9.91e37 when measurement is unavailable or overrange
            if val > 1e30 or math.isnan(val) or math.isinf(val):
                return 0.0
            return val
        except Exception:
            return 0.0

    def send_scpi(self, cmd: str) -> str:
        """Execute arbitrary SCPI command, returning response if query, or '[OK]'."""
        cmd = cmd.strip()
        if "?" in cmd:
            return self.query(cmd)
        else:
            self.send(cmd)
            return "[OK]"

    # Waveform Transfer
    def fetch_channel_waveform(self, ch: int) -> Tuple[Any, Any]:
        """
        Reads channel waveform data and returns (time_array, volt_array).
        Supports IEEE-488.2 binary block format (#<d><len><bytes>) and ASCII comma-separated format.
        Applies vertical Y-axis scaling: v = raw * yincrement + yorigin.
        """
        with self._lock:
            # Synchronize before read
            try:
                self.query("*OPC?", timeout=5.0)
            except Exception:
                pass

            # Query physical scaling parameters
            yincrement = 1.0
            yorigin = 0.0
            xincrement = 1e-4
            xorigin = -0.005

            try:
                resp_yinc = self.query(f":CHANnel{ch}:DATA:YINC?")
                if resp_yinc:
                    yincrement = float(resp_yinc.split(",")[-1].strip())
            except Exception:
                try:
                    resp_yinc = self.query(f":CHANnel{ch}:DATA:YINCrement?")
                    if resp_yinc:
                        yincrement = float(resp_yinc.split(",")[-1].strip())
                except Exception:
                    pass

            try:
                resp_yorg = self.query(f":CHANnel{ch}:DATA:YOR?")
                if resp_yorg:
                    yorigin = float(resp_yorg.split(",")[-1].strip())
            except Exception:
                try:
                    resp_yorg = self.query(f":CHANnel{ch}:DATA:YORigin?")
                    if resp_yorg:
                        yorigin = float(resp_yorg.split(",")[-1].strip())
                except Exception:
                    pass

            try:
                resp_xinc = self.query(f":CHANnel{ch}:DATA:XINC?")
                if resp_xinc:
                    xincrement = float(resp_xinc.split(",")[-1].strip())
            except Exception:
                try:
                    resp_xinc = self.query(f":CHANnel{ch}:DATA:XINCrement?")
                    if resp_xinc:
                        xincrement = float(resp_xinc.split(",")[-1].strip())
                except Exception:
                    pass

            try:
                resp_xorg = self.query(f":CHANnel{ch}:DATA:XOR?")
                if resp_xorg:
                    xorigin = float(resp_xorg.split(",")[-1].strip())
            except Exception:
                try:
                    resp_xorg = self.query(f":CHANnel{ch}:DATA:XORigin?")
                    if resp_xorg:
                        xorigin = float(resp_xorg.split(",")[-1].strip())
                except Exception:
                    pass

            # Query waveform data
            self.send(f":CHANnel{ch}:DATA?")

            raw_resp = b""
            deadline = time.time() + self.timeout
            expected_total = None

            while time.time() < deadline:
                chunk = self.sock.recv(16384)
                if not chunk:
                    break
                raw_resp += chunk

                # Check if IEEE-488.2 binary block header received
                if expected_total is None and raw_resp.startswith(b"#") and len(raw_resp) >= 3:
                    try:
                        num_digits = int(chr(raw_resp[1]))
                        if len(raw_resp) >= 2 + num_digits:
                            payload_len = int(raw_resp[2:2 + num_digits].decode("ascii"))
                            expected_total = 2 + num_digits + payload_len
                    except Exception:
                        pass

                if expected_total is not None:
                    if len(raw_resp) >= expected_total:
                        break
                elif b"\n" in raw_resp:
                    break

            if not raw_resp:
                raise RuntimeError("no waveform data received")

            # 1. Parse IEEE-488.2 Binary Block Format (#<d><len><bytes>)
            if raw_resp.startswith(b"#"):
                try:
                    num_digits = int(chr(raw_resp[1]))
                    payload_len = int(raw_resp[2:2 + num_digits].decode("ascii"))
                    payload_start = 2 + num_digits
                    payload_bytes = raw_resp[payload_start:payload_start + payload_len]

                    if HAVE_NUMPY:
                        raw_data = np.frombuffer(payload_bytes, dtype=np.int8)
                        num_pts = len(raw_data)
                        v_arr = raw_data.astype(float) * yincrement + yorigin
                        t_arr = xorigin + np.arange(num_pts) * xincrement
                    else:
                        raw_data = [b - 256 if b > 127 else b for b in payload_bytes]
                        num_pts = len(raw_data)
                        v_arr = [r * yincrement + yorigin for r in raw_data]
                        t_arr = [xorigin + k * xincrement for k in range(num_pts)]

                    return t_arr, v_arr
                except Exception:
                    pass

            # 2. Parse ASCII comma-separated format
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
            if HAVE_NUMPY:
                t_arr = xorigin + np.arange(actual_n) * xincrement
                v_arr = np.array(volt_list, dtype=float)
            else:
                t_arr = [xorigin + k * xincrement for k in range(actual_n)]
                v_arr = volt_list

            return t_arr, v_arr
