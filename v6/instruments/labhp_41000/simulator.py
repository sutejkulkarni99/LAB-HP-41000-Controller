"""LABHPSimulatorServer — Lightweight standalone TCP simulator for ETPS LAB-HP 41000."""
import socket
import threading
import time
import re
from typing import Optional


class LABHPSimulatorServer:
    """
    TCP server emulating ETPS LAB-HP 41000 on port 10001 (or custom port).
    Supports all native commands and provides realistic voltage/current/load calculations.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 10001):
        self.host = host
        self.port = port
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._server_sock: Optional[socket.socket] = None

        # State
        self.voltage_setpoint = 24.0
        self.current_limit = 5.0
        self.power_limit = 2000.0
        self.ovp_setting = 80.0
        self.output_on = False
        self.remote_mode = True
        self.mode = "UI"
        self.load_resistance = 10.0  # Ohms
        self.ovp_tripped = False
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
            try:
                self._server_sock.close()
            except Exception:
                pass
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
                    data = sock.recv(2048)
                    if not data:
                        break
                    buf += data
                    while b"\n" in buf or b"\r" in buf:
                        # Split by first newline/carriage return
                        match = re.search(b"[\r\n]+", buf)
                        if not match:
                            break
                        line = buf[:match.start()].decode("ascii", errors="ignore").strip()
                        buf = buf[match.end():]
                        if line:
                            resp = self._process_command(line)
                            if resp:
                                sock.sendall((resp + "\r\n").encode("ascii"))
                except (socket.timeout, OSError):
                    continue

    def _process_command(self, cmd: str) -> Optional[str]:
        with self._lock:
            parts = cmd.split(",", 1)
            opcode = parts[0].strip().upper()
            arg = parts[1].strip() if len(parts) > 1 else None

            if opcode in ("ID", "*IDN?"):
                return "ETPS,LAB-HP 41000,SN-SIM-6001,V6.2.0"
            elif opcode == "GTR":
                self.remote_mode = True
                return None
            elif opcode == "GTL":
                self.remote_mode = False
                return None
            elif opcode == "*RST":
                self.voltage_setpoint = 0.0
                self.output_on = False
                return None
            elif opcode == "SS":
                return None
            elif opcode == "UA":
                if arg is not None:
                    try:
                        self.voltage_setpoint = max(0.0, min(1000.0, float(arg)))
                        if self.voltage_setpoint > self.ovp_setting:
                            self.ovp_tripped = True
                            self.output_on = False
                    except ValueError:
                        pass
                    return None
                return f"UA,{self.voltage_setpoint:.2f}"
            elif opcode == "IA":
                if arg is not None:
                    try: self.current_limit = max(0.0, min(7.0, float(arg)))
                    except ValueError: pass
                    return None
                return f"IA,{self.current_limit:.4f}"
            elif opcode == "PA":
                if arg is not None:
                    try: self.power_limit = max(0.0, min(4000.0, float(arg)))
                    except ValueError: pass
                    return None
                return f"PA,{self.power_limit:.2f}"
            elif opcode == "OVP":
                if arg is not None:
                    try: self.ovp_setting = max(0.0, min(1200.0, float(arg)))
                    except ValueError: pass
                    return None
                return f"OVP,{self.ovp_setting:.1f}"
            elif opcode == "SB":
                if arg is not None:
                    if arg.upper() == "R":
                        if not self.ovp_tripped:
                            self.output_on = True
                    elif arg.upper() == "S":
                        self.output_on = False
                        self.ovp_tripped = False
                    return None
                return f"SB,{'R' if self.output_on else 'S'}"
            elif opcode == "MU":
                if not self.output_on or self.ovp_tripped:
                    return "MU,0.00"
                # Calculate based on load
                ideal_i = self.voltage_setpoint / max(0.01, self.load_resistance)
                actual_i = min(ideal_i, self.current_limit)
                actual_v = actual_i * self.load_resistance
                return f"MU,{actual_v:.2f}"
            elif opcode == "MI":
                if not self.output_on or self.ovp_tripped:
                    return "MI,0.0000"
                ideal_i = self.voltage_setpoint / max(0.01, self.load_resistance)
                actual_i = min(ideal_i, self.current_limit)
                return f"MI,{actual_i:.4f}"
            elif opcode == "STATUS":
                # Bit 0: OVP tripped, Bit 1: Standby (output off), Bit 4: Remote, Bit 5: Local, Bit 7: Current Limit
                b0 = 1 if self.ovp_tripped else 0
                b1 = 1 if not self.output_on else 0
                b4 = 1 if self.remote_mode else 0
                b5 = 1 if not self.remote_mode else 0
                ideal_i = self.voltage_setpoint / max(0.01, self.load_resistance)
                b7 = 1 if (self.output_on and ideal_i >= self.current_limit) else 0
                bits = [0]*16
                bits[0], bits[1], bits[4], bits[5], bits[7] = b0, b1, b4, b5, b7
                rev = bits[::-1]
                return f"STATUS,{''.join(str(b) for b in rev)}"
            elif opcode == "MODE":
                if arg is not None:
                    self.mode = arg
                    return None
                return f"MODE,{self.mode}"
            return ""


# Alias
LABHPSimulator = LABHPSimulatorServer
