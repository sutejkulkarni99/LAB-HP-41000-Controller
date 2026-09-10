"""RTB2000SimulatorServer — Standalone TCP SCPI Simulator for Rohde & Schwarz RTB2000 (Port 5025)."""
import socket
import threading
import time
import math
import re
from typing import Optional


class RTB2000SimulatorServer:
    """
    Simulates Rohde & Schwarz RTB2000 oscilloscope SCPI server on TCP port 5025.
    Generates realistic synthetic multi-channel waveforms (CH1: Sine 50Hz, CH2: Square pulse 100Hz)
    and supports full timebase/channel/trigger configuration queries.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 5025):
        self.host = host
        self.port = port
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._server_sock: Optional[socket.socket] = None

        # State
        self.running_state = True
        self.timebase_scale = 1e-3  # 1ms / div
        self.timebase_pos = 0.0
        self.ch_state = {1: True, 2: True, 3: False, 4: False}
        self.ch_scale = {1: 1.0, 2: 2.0, 3: 1.0, 4: 1.0}
        self.ch_pos = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
        self.ch_coupling = {1: "DC", 2: "DC", 3: "DC", 4: "DC"}
        self.ch_probe = {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0}
        self.trig_source = "CH1"
        self.trig_level = 0.5
        self.trig_slope = "POS"
        self.trig_mode = "AUTO"
        self.meas_source = 1
        self.meas_param = "RMS"
        self._lock = threading.Lock()

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        time.sleep(0.1)

    def stop(self):
        self.running = False
        if self._server_sock:
            try: self._server_sock.close()
            except Exception: pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def _run(self):
        try:
            self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_sock.bind((self.host, self.port))
            self._server_sock.listen(2)
            self._server_sock.settimeout(0.5)

            while self.running:
                try:
                    client_sock, _ = self._server_sock.accept()
                    client_sock.settimeout(1.0)
                    threading.Thread(target=self._handle_client, args=(client_sock,), daemon=True).start()
                except socket.timeout:
                    continue
                except OSError:
                    break
        except Exception:
            pass
        finally:
            self.running = False

    def _handle_client(self, sock: socket.socket):
        buf = b""
        with sock:
            while self.running:
                try:
                    data = sock.recv(4096)
                    if not data:
                        break
                    buf += data
                    while b"\n" in buf or b"\r" in buf:
                        match = re.search(b"[\r\n]+", buf)
                        if not match:
                            break
                        line = buf[:match.start()].decode("ascii", errors="ignore").strip()
                        buf = buf[match.end():]
                        if line:
                            # Handle multiple commands separated by semicolon
                            for sub_cmd in line.split(";"):
                                sub_cmd = sub_cmd.strip()
                                if sub_cmd:
                                    resp = self._process_scpi(sub_cmd)
                                    if resp is not None:
                                        sock.sendall((resp + "\n").encode("ascii"))
                except (socket.timeout, OSError):
                    continue

    def _process_scpi(self, cmd: str) -> Optional[str]:
        with self._lock:
            cmd_upper = cmd.upper().strip()

            if cmd_upper in ("*IDN?", "IDN?"):
                return "Rohde&Schwarz,RTB2004,1333.1005K04/101234,02.300"
            elif cmd_upper == "*OPC?":
                return "1"
            elif cmd_upper in ("*CLS", "*RST"):
                return None
            elif cmd_upper in (":RUN", "RUN"):
                self.running_state = True
                return None
            elif cmd_upper in (":STOP", "STOP"):
                self.running_state = False
                return None
            elif cmd_upper in (":SINGLE", "SINGLE", ":SING", "SING"):
                self.running_state = False
                return None

            # Timebase
            if cmd_upper.startswith(":TIM:SCAL") or cmd_upper.startswith(":TIMEBASE:SCAL"):
                if "?" in cmd_upper:
                    return f"{self.timebase_scale:.6e}"
                val = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", cmd)
                if val: self.timebase_scale = max(1e-9, float(val[0]))
                return None
            elif cmd_upper.startswith(":TIM:POS") or cmd_upper.startswith(":TIMEBASE:POS"):
                if "?" in cmd_upper:
                    return f"{self.timebase_pos:.6e}"
                val = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", cmd)
                if val: self.timebase_pos = float(val[0])
                return None

            # Channel Data Header query
            if "DATA:HEAD" in cmd_upper or "DATA:HEADER" in cmd_upper:
                total_time = self.timebase_scale * 10.0
                return f"{-total_time/2.0:.6e},{total_time/2.0:.6e},1000,1"

            # Channels
            ch_match = re.match(r":?CHAN(?:NEL)?([1-4]):(\w+)(\?)?(.*)", cmd_upper)
            if ch_match:
                ch = int(ch_match.group(1))
                prop = ch_match.group(2)
                is_query = bool(ch_match.group(3))
                args = ch_match.group(4).strip()

                if prop == "STAT" or prop == "STATE":
                    if is_query: return "1" if self.ch_state.get(ch, False) else "0"
                    self.ch_state[ch] = ("1" in args or "ON" in args)
                    return None
                elif prop == "SCAL" or prop == "SCALE":
                    if is_query: return f"{self.ch_scale.get(ch, 1.0):.6e}"
                    val = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", args)
                    if val: self.ch_scale[ch] = max(1e-4, float(val[0]))
                    return None
                elif prop == "POS" or prop == "POSITION":
                    if is_query: return f"{self.ch_pos.get(ch, 0.0):.2f}"
                    val = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", args)
                    if val: self.ch_pos[ch] = float(val[0])
                    return None
                elif prop == "COUP" or prop == "COUPLING":
                    if is_query: return self.ch_coupling.get(ch, "DC")
                    if args in ("DC", "AC", "GND"): self.ch_coupling[ch] = args
                    return None
                elif prop == "PROB" or prop == "PROBE":
                    if is_query: return f"{self.ch_probe.get(ch, 1.0):.1f}"
                    val = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", args)
                    if val: self.ch_probe[ch] = float(val[0])
                    return None
                elif prop.startswith("DATA:HEAD"):
                    # x_start, x_stop, sample_count, values_per_interval
                    total_time = self.timebase_scale * 10.0
                    return f"{-total_time/2.0:.6e},{total_time/2.0:.6e},1000,1"
                elif prop == "DATA":
                    # Generate 1000 sample points
                    total_time = self.timebase_scale * 10.0
                    dt = total_time / 1000.0
                    t_start = -total_time / 2.0
                    points = []
                    freq = 50.0 if ch == 1 else 120.0
                    amp = 3.3 if ch == 1 else 5.0
                    for k in range(1000):
                        t_sec = t_start + k * dt
                        if ch == 1:
                            val = amp * math.sin(2.0 * math.pi * freq * t_sec) + 0.05 * math.sin(2.0 * math.pi * 1000.0 * t_sec)
                        elif ch == 2:
                            # Pulse square wave
                            phase = (t_sec * freq) % 1.0
                            val = amp if phase < 0.5 else 0.0
                        else:
                            val = 0.5 * math.cos(2.0 * math.pi * 20.0 * t_sec)
                        points.append(f"{val:.4f}")
                    return ",".join(points)

            # Trigger
            if cmd_upper.startswith(":TRIG") or cmd_upper.startswith("TRIG"):
                if "SOUR" in cmd_upper:
                    if "?" in cmd_upper: return self.trig_source
                    for s in ["CH1", "CH2", "CH3", "CH4", "EXT"]:
                        if s in cmd_upper: self.trig_source = s
                    return None
                elif "LEV" in cmd_upper:
                    if "?" in cmd_upper: return f"{self.trig_level:.4f}"
                    val = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", cmd)
                    if val: self.trig_level = float(val[0])
                    return None
                elif "SLOP" in cmd_upper:
                    if "?" in cmd_upper: return self.trig_slope
                    self.trig_slope = "NEG" if "NEG" in cmd_upper else "POS"
                    return None
                elif "MODE" in cmd_upper:
                    if "?" in cmd_upper: return self.trig_mode
                    for m in ["AUTO", "NORM", "SING"]:
                        if m in cmd_upper: self.trig_mode = m
                    return None

            # Measurement
            if cmd_upper.startswith(":MEAS") or cmd_upper.startswith("MEAS"):
                if "SOUR" in cmd_upper:
                    for ch in [1, 2, 3, 4]:
                        if f"CH{ch}" in cmd_upper: self.meas_source = ch
                    return None
                elif "MAIN" in cmd_upper:
                    for p in ["RMS", "PEAK", "MAX", "MIN", "FREQ", "PER"]:
                        if p in cmd_upper: self.meas_param = p
                    return None
                elif "RES" in cmd_upper or "?" in cmd_upper:
                    if "RMS" in self.meas_param:
                        return "2.3335" if self.meas_source == 1 else "3.5355"
                    elif "PEAK" in self.meas_param:
                        return "6.6000" if self.meas_source == 1 else "5.0000"
                    elif "FREQ" in self.meas_param:
                        return "50.00" if self.meas_source == 1 else "120.00"
                    return "1.0000"

            return ""


# Alias
RTB2000Simulator = RTB2000SimulatorServer
