"""RTB2000SimulatorServer — Standalone TCP SCPI Simulator for Rohde & Schwarz RTB2000 (Port 5025)."""
import socket
import threading
import time
import math
import struct
from typing import Optional


class RTB2000SimulatorServer:
    """Lightweight background TCP server simulating the Rohde & Schwarz RTB2000 SCPI protocol."""

    def __init__(self, host: str = "127.0.0.1", port: int = 5025):
        self.host = host
        self.port = port
        self.running = False
        self._server_sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None

        # Oscilloscope State
        self.lock = threading.Lock()
        self.ch1_scale = 1.0
        self.ch1_position = 0.0
        self.ch1_coupling = "DCLimit"
        self.ch1_state = 1

        self.ch2_scale = 2.0
        self.ch2_position = 0.0
        self.ch2_coupling = "DCLimit"
        self.ch2_state = 1

        self.timebase_scale = 0.001
        self.timebase_position = 0.0
        self.run_state = "RUN"
        self.trigger_source = "CH1"
        self.trigger_level = 0.0
        self.trigger_slope = "POS"
        self.trigger_mode = "AUTO"

    def start(self):
        self.running = True
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((self.host, self.port))
        self._server_sock.listen(5)
        self._server_sock.settimeout(0.5)

        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self._server_sock:
            try:
                self._server_sock.close()
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=1.0)

    def _listen_loop(self):
        while self.running:
            try:
                client, addr = self._server_sock.accept()
                t = threading.Thread(target=self._client_handler, args=(client,), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except Exception:
                break

    def _client_handler(self, client: socket.socket):
        client.settimeout(1.0)
        buffer = ""
        while self.running:
            try:
                data = client.recv(1024)
                if not data:
                    break
                buffer += data.decode("latin1", errors="ignore")
                while "\n" in buffer:
                    line, _, buffer = buffer.partition("\n")
                    line = line.strip("\r\n").strip()
                    if line:
                        resp = self._handle_command(line)
                        if isinstance(resp, bytes):
                            client.sendall(resp)
                        elif resp is not None:
                            client.sendall((resp + "\n").encode("latin1"))
            except socket.timeout:
                continue
            except Exception:
                break
        try:
            client.close()
        except Exception:
            pass

    def _handle_command(self, cmd: str):
        with self.lock:
            cmd = cmd.strip()
            up = cmd.upper()
            if up in ("*IDN?", "IDN?"):
                return "Rohde&Schwarz,RTB2004,1333.1005k04/100001,05.100"
            if up == "*OPC?":
                return "1"
            if up.startswith(":RUN") or up.startswith("RUN"):
                self.run_state = "RUN"
                return None
            if up.startswith(":STOP") or up.startswith("STOP"):
                self.run_state = "STOP"
                return None
            if up.startswith(":SING") or up.startswith("SING"):
                self.run_state = "STOP"
                return None
            if up.startswith(":AUT") or up.startswith("AUT"):
                return None

            # Channel 1 Scale
            if up.startswith(":CHAN1:SCAL ") or up.startswith(":CHANNEL1:SCALE "):
                try:
                    self.ch1_scale = float(cmd.split()[1])
                except Exception:
                    pass
                return None
            if up in (":CHAN1:SCAL?", ":CHANNEL1:SCALE?", ":CHAN1:SCALE?", ":CHANNEL1:SCAL?"):
                return f"{self.ch1_scale:.4E}"

            # Channel 2 Scale
            if up.startswith(":CHAN2:SCAL ") or up.startswith(":CHANNEL2:SCALE "):
                try:
                    self.ch2_scale = float(cmd.split()[1])
                except Exception:
                    pass
                return None
            if up in (":CHAN2:SCAL?", ":CHANNEL2:SCALE?", ":CHAN2:SCALE?", ":CHANNEL2:SCAL?"):
                return f"{self.ch2_scale:.4E}"

            # Timebase Scale
            if up.startswith(":TIM:SCAL ") or up.startswith(":TIMEBASE:SCALE "):
                try:
                    self.timebase_scale = float(cmd.split()[1])
                except Exception:
                    pass
                return None
            if up in (":TIM:SCAL?", ":TIMEBASE:SCALE?", ":TIMEBASE:SCAL?", ":TIM:SCALE?"):
                return f"{self.timebase_scale:.4E}"

            # Channel States
            if up.startswith(":CHAN1:STAT") or up.startswith(":CHANNEL1:STAT"):
                if "?" in up:
                    return "1" if self.ch1_state else "0"
                self.ch1_state = 1 if ("ON" in up or "1" in up) else 0
                return None
            if up.startswith(":CHAN2:STAT") or up.startswith(":CHANNEL2:STAT"):
                if "?" in up:
                    return "1" if self.ch2_state else "0"
                self.ch2_state = 1 if ("ON" in up or "1" in up) else 0
                return None

            # Positions
            if "POS" in up and "TRIG" not in up and "SLOP" not in up:
                if "?" in up:
                    return "0.00"
                return None

            # Couplings
            if "COUP" in up:
                if "?" in up:
                    return "DC"
                return None

            # Trigger Controls
            if "TRIG" in up:
                if "SOUR" in up:
                    if "?" in up:
                        return self.trigger_source
                    val = cmd.split()[-1].strip().upper()
                    self.trigger_source = val
                    return None
                if "LEV" in up:
                    if "?" in up:
                        return f"{self.trigger_level:.4f}"
                    try:
                        self.trigger_level = float(cmd.split()[-1])
                    except Exception:
                        pass
                    return None
                if "SLOP" in up:
                    if "?" in up:
                        return self.trigger_slope
                    self.trigger_slope = "POS" if "POS" in up else "NEG"
                    return None
                if "MODE" in up:
                    if "?" in up:
                        return self.trigger_mode
                    self.trigger_mode = "AUTO" if "AUTO" in up else "NORM"
                    return None

            # Measurements
            if "MEAS" in up:
                if "RES?" in up or "RESULT?" in up:
                    return "50.000"
                return None

            # Data Header / Data
            if "DATA:HEAD?" in up:
                num_pts = 1000
                x_start = -5 * self.timebase_scale
                x_stop = 5 * self.timebase_scale
                return f"{x_start:.6E},{x_stop:.6E},{num_pts},1"
            if ":DATA?" in up or "DATA?" in up:
                num_pts = 1000
                ch = 1 if ("CHAN1" in up or "CHANNEL1" in up) else 2
                freq = 50.0 if ch == 1 else 100.0
                t_total = 10 * self.timebase_scale
                dt = t_total / num_pts
                vals = []
                for i in range(num_pts):
                    t = -5 * self.timebase_scale + i * dt
                    if ch == 1:
                        val = self.ch1_scale * 2.0 * math.sin(2 * math.pi * freq * t)
                    else:
                        val = self.ch2_scale * (1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0)
                    vals.append(val)
                raw_bytes = struct.pack(f"<{num_pts}f", *vals)
                len_str = str(len(raw_bytes))
                header = f"#{len(len_str)}{len_str}".encode("latin1")
                return header + raw_bytes + b"\n"
            return "0"


RTB2000Simulator = RTB2000SimulatorServer
