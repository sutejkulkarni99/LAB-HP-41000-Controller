"""ETPS LAB-HP 41000 ASCII Protocol Driver over TCP/IP (Port 10001)."""
import socket
import threading
import time
import re
from typing import Dict, Any


class LABHPController:
    """ASCII Protocol Driver for ETPS LAB-HP 41000 over TCP/IP."""

    MAX_VOLTAGE = 1000.0
    MAX_CURRENT = 7.0
    MAX_POWER   = 4000.0

    def __init__(self):
        self.sock: socket.socket | None = None
        self._lock = threading.Lock()
        self.connected = False
        self.ip = ""
        self.port = 10001
        self.timeout = 4.0
        self.last_roundtrip_ms = 0.0

    def connect(self, ip: str, port: int = 10001) -> bool:
        if self.connected:
            self.disconnect()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect((ip, port))
        self.ip = ip
        self.port = port
        self.connected = True
        time.sleep(0.15)

        # Flush any welcome or boot banners
        try:
            self.sock.settimeout(0.3)
            self.sock.recv(4096)
        except (socket.timeout, OSError):
            pass
        self.sock.settimeout(self.timeout)
        return True

    def disconnect(self):
        self.connected = False
        with self._lock:
            sock = self.sock
            self.sock = None
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass

    def _send(self, cmd: str, expect_response: bool = False, retries: int = 1) -> str:
        with self._lock:
            if not self.sock or not self.connected:
                raise ConnectionError("Device not connected")

            data = (cmd.strip() + "\r\n").encode("ascii")
            t_start = time.perf_counter()

            for attempt in range(retries + 1):
                try:
                    self.sock.sendall(data)
                    if expect_response:
                        resp = b""
                        deadline = time.time() + self.timeout
                        while time.time() < deadline:
                            chunk = self.sock.recv(4096)
                            if not chunk:
                                break
                            resp += chunk
                            if b"\n" in resp or b"\r" in resp:
                                break
                        decoded = resp.decode("ascii", errors="ignore").strip()
                        self.last_roundtrip_ms = (time.perf_counter() - t_start) * 1000.0
                        return decoded
                    self.last_roundtrip_ms = (time.perf_counter() - t_start) * 1000.0
                    return ""
                except (socket.timeout, OSError) as e:
                    if attempt < retries:
                        time.sleep(0.08)
                        continue
                    self.connected = False
                    raise ConnectionError(f"I/O error ({cmd}): {e}")
            return ""

    @staticmethod
    def _parse_value(resp: str) -> float:
        if not resp:
            return 0.0
        val_part = resp.split(",", 1)[1] if "," in resp else resp
        match = re.search(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", val_part)
        return float(match.group()) if match else 0.0

    # Device Command Interface
    def get_idn(self) -> str: return self._send("ID", expect_response=True, retries=2)
    def set_remote(self): self._send("GTR", retries=2)
    def set_local(self): self._send("GTL", retries=2)
    def reset(self): self._send("*RST")
    def save_setup(self): self._send("SS")

    # Setpoints
    def set_voltage(self, v: float): self._send(f"UA,{v:.2f}")
    def get_voltage_setpoint(self) -> float: return self._parse_value(self._send("UA", expect_response=True))
    def set_current(self, i: float): self._send(f"IA,{i:.4f}")
    def get_current_setpoint(self) -> float: return self._parse_value(self._send("IA", expect_response=True))
    def set_power(self, p: float): self._send(f"PA,{p:.2f}")
    def get_power_setpoint(self) -> float: return self._parse_value(self._send("PA", expect_response=True))
    def set_ovp(self, v: float): self._send(f"OVP,{v:.1f}")
    def get_ovp(self) -> float: return self._parse_value(self._send("OVP", expect_response=True))

    # Output Control
    def output_on(self): self._send("SB,R", retries=2)
    def output_off(self): self._send("SB,S", retries=2)
    def set_output(self, state: bool):
        if state:
            self.output_on()
        else:
            self.output_off()

    @property
    def output_state(self) -> bool:
        return self.get_output_state()

    def get_output_state(self) -> bool:
        resp = self._send("SB", expect_response=True)
        return ("R" in resp.split(",", 1)[1].upper()) if "," in resp else False

    # Measurements & Status
    def measure_voltage(self) -> float: return self._parse_value(self._send("MU", expect_response=True))
    def measure_current(self) -> float: return self._parse_value(self._send("MI", expect_response=True))
    def get_status_raw(self) -> str: return self._send("STATUS", expect_response=True)

    def get_mode(self) -> str:
        resp = self._send("MODE", expect_response=True)
        return resp.split(",")[1].strip() if "," in resp else resp

    def set_mode(self, mode: str): self._send(f"MODE,{mode}")
    def set_operating_mode(self, mode: str): self.set_mode(mode)
    def send_cmd(self, cmd: str) -> str: return self._send(cmd, expect_response=True)

    def measure_fast_telemetry(self) -> dict:
        """Pipelined measurement for high polling efficiency."""
        u = self.measure_voltage()
        i = self.measure_current()
        p = u * i
        r = (u / i) if i > 0.0005 else float('inf')
        return {"voltage": u, "current": i, "power": p, "resistance": r}

    @staticmethod
    def decode_status(raw: str) -> Dict[str, Any]:
        """Decode 16-bit status word."""
        bits = raw.replace("STATUS,", "").strip()
        if not bits:
            return {}
        bits = bits.zfill(16)
        bits_rev = bits[::-1]
        bit_list = [int(b) for b in bits_rev]
        return {
            "OVP shutdown": bool(bit_list[0]),
            "Standby": bool(bit_list[1]),
            "Remote mode": bool(bit_list[4]),
            "Local mode": bool(bit_list[5]),
            "Local lockout": bool(bit_list[6]),
            "Current limit": bool(bit_list[7]),
            "Power limit": bool(bit_list[8]),
            "Raw": raw.strip()
        }
