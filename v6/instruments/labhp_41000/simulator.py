"""LABHPSimulatorServer — Lightweight standalone TCP simulator for ETPS LAB-HP 41000."""
import socket
import threading
import time
import math
from typing import Optional


class LABHPSimulatorServer:
    """Lightweight background TCP server simulating the ETPS LAB-HP 41000 command protocol."""

    def __init__(self, host: str = "127.0.0.1", port: int = 10001):
        self.host = host
        self.port = port
        self.running = False
        self._server_sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None

        # Simulated Device State
        self.lock = threading.Lock()
        self.voltage_setpoint = 48.0
        self.current_setpoint = 5.0
        self.ovp_setpoint = 120.0
        self.output_enabled = False
        self.remote_mode = True
        self.simulated_load_r = 10.0  # 10 ohm default simulated load

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
                while "\n" in buffer or "\r" in buffer:
                    line, _, buffer = buffer.partition("\n")
                    line = line.strip("\r\n").strip()
                    if line:
                        resp = self._handle_command(line)
                        if resp is not None:
                            client.sendall((resp + "\n").encode("latin1"))
            except socket.timeout:
                continue
            except Exception:
                break
        try:
            client.close()
        except Exception:
            pass

    def _handle_command(self, cmd: str) -> Optional[str]:
        with self.lock:
            cmd = cmd.strip()
            if cmd == "ID":
                return "ETPS,LAB-HP 41000,SN-SIM-6001,V6.2.0"
            if cmd == "GTR":
                self.remote_mode = True
                return None
            if cmd == "GTL":
                self.remote_mode = False
                return None
            if cmd == "SB,R":
                self.output_enabled = True
                return None
            if cmd == "SB,S":
                self.output_enabled = False
                return None
            if cmd == "SB":
                return f"SB,{'R' if self.output_enabled else 'S'}"
            if cmd == "STATUS":
                # Returns 16-bit status word. bit 4 is Remote mode (0x10)
                # bit 5 is Local mode
                status_val = 0x0010 if self.remote_mode else 0x0020
                bits_str = f"{status_val:016b}"
                return f"STATUS,{bits_str}"
            if cmd == "MODE":
                return "MODE,UI"
            if cmd.startswith("UA,") or cmd.startswith("PV,"):
                try:
                    self.voltage_setpoint = float(cmd.split(",")[1])
                except Exception:
                    pass
                return None
            if cmd in ("UA", "PV"):
                return f"UA,{self.voltage_setpoint:.2f}"
            if cmd.startswith("IA,") or cmd.startswith("PC,"):
                try:
                    self.current_setpoint = float(cmd.split(",")[1])
                except Exception:
                    pass
                return None
            if cmd in ("IA", "PC"):
                return f"IA,{self.current_setpoint:.4f}"
            if cmd.startswith("PA,"):
                try:
                    self.power_setpoint = float(cmd.split(",")[1])
                except Exception:
                    pass
                return None
            if cmd == "PA":
                return f"PA,{self.voltage_setpoint * self.current_setpoint:.2f}"
            if cmd.startswith("OVP,"):
                try:
                    self.ovp_setpoint = float(cmd.split(",")[1])
                except Exception:
                    pass
                return None
            if cmd == "OVP":
                return f"OVP,{self.ovp_setpoint:.1f}"
            if cmd in ("MU", "MV?"):
                if self.output_enabled:
                    v = min(self.voltage_setpoint, self.current_setpoint * self.simulated_load_r)
                    return f"MU,{v:.2f}"
                return "MU,0.00"
            if cmd in ("MI", "MC?"):
                if self.output_enabled:
                    v = min(self.voltage_setpoint, self.current_setpoint * self.simulated_load_r)
                    c = v / self.simulated_load_r
                    return f"MI,{c:.3f}"
                return "MI,0.000"
            if cmd in ("MP", "MP?"):
                if self.output_enabled:
                    v = min(self.voltage_setpoint, self.current_setpoint * self.simulated_load_r)
                    c = v / self.simulated_load_r
                    p = v * c
                    return f"MP,{p:.1f}"
                return "MP,0.0"
            if cmd in ("MR", "MR?"):
                if self.output_enabled:
                    return f"MR,{self.simulated_load_r:.2f}"
                return "MR,0.00"
            return "OK"


LABHPSimulator = LABHPSimulatorServer
