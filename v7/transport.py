import socket
import time
from typing import Optional
from .contracts import Transport

class SocketTransport(Transport):
    """TCP socket transport implementing raw stream byte operations."""

    def __init__(self, ip: str, port: int, timeout_s: float = 5.0):
        self.ip = ip
        self.port = port
        self.timeout_s = timeout_s
        self._sock: Optional[socket.socket] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._sock.settimeout(self.timeout_s)
        self._sock.connect((self.ip, self.port))

    def write(self, data: bytes) -> None:
        if not self._sock:
            raise ConnectionError("Socket is closed")
        self._sock.sendall(data)

    def read_until(self, terminator: bytes, timeout_s: float) -> bytes:
        if not self._sock:
            raise ConnectionError("Socket is closed")
        self._sock.settimeout(timeout_s)
        buffer = bytearray()
        end_time = time.monotonic() + timeout_s
        while True:
            idx = buffer.find(terminator)
            if idx != -1:
                return bytes(buffer[:idx + len(terminator)])
            remaining = end_time - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"Timed out waiting for terminator {terminator!r}")
            self._sock.settimeout(max(0.01, remaining))
            try:
                chunk = self._sock.recv(4096)
                if not chunk:
                    raise ConnectionResetError("Socket closed by remote host")
                buffer.extend(chunk)
            except socket.timeout:
                raise TimeoutError(f"Socket timed out waiting for terminator {terminator!r}")

    def read_bytes(self, n: int, timeout_s: float) -> bytes:
        if not self._sock:
            raise ConnectionError("Socket is closed")
        self._sock.settimeout(timeout_s)
        buffer = bytearray()
        end_time = time.monotonic() + timeout_s
        while len(buffer) < n:
            remaining = end_time - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"Timed out reading {n} bytes (read {len(buffer)})")
            self._sock.settimeout(max(0.01, remaining))
            try:
                chunk = self._sock.recv(min(4096, n - len(buffer)))
                if not chunk:
                    raise ConnectionResetError("Socket closed by remote host")
                buffer.extend(chunk)
            except socket.timeout:
                raise TimeoutError(f"Socket timed out reading {n} bytes")
        return bytes(buffer)

    def close(self) -> None:
        if self._sock:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None


class VisaTransport(Transport):
    """VISA transport using pyvisa."""

    def __init__(self, resource_string: str, timeout_s: float = 5.0):
        try:
            import pyvisa
        except ImportError:
            raise RuntimeError("pyvisa is required for VisaTransport but not installed.")

        self.resource_string = resource_string
        self.timeout_s = timeout_s
        rm = pyvisa.ResourceManager()
        self._inst = rm.open_resource(resource_string)
        self._inst.timeout = int(timeout_s * 1000)

    def write(self, data: bytes) -> None:
        if not self._inst:
            raise ConnectionError("VISA instrument is closed")
        self._inst.write_raw(data)

    def read_until(self, terminator: bytes, timeout_s: float) -> bytes:
        if not self._inst:
            raise ConnectionError("VISA instrument is closed")
        old_to = self._inst.timeout
        self._inst.timeout = int(timeout_s * 1000)
        try:
            data = bytearray()
            while True:
                chunk = self._inst.read_bytes(1)
                data.extend(chunk)
                if data.endswith(terminator):
                    return bytes(data)
        finally:
            self._inst.timeout = old_to

    def read_bytes(self, n: int, timeout_s: float) -> bytes:
        if not self._inst:
            raise ConnectionError("VISA instrument is closed")
        old_to = self._inst.timeout
        self._inst.timeout = int(timeout_s * 1000)
        try:
            return self._inst.read_bytes(n)
        finally:
            self._inst.timeout = old_to

    def close(self) -> None:
        if self._inst:
            try:
                self._inst.close()
            except Exception:
                pass
            self._inst = None


def parse_resource(resource: str) -> Transport:
    """Instantiate a Transport based on the resource string specification."""
    resource = resource.strip()
    if "::" in resource:
        return VisaTransport(resource)
    if ":" in resource:
        host, port_str = resource.split(":", 1)
        return SocketTransport(host.strip(), int(port_str.strip()))
    raise ValueError(f"Invalid resource string format: '{resource}'. Expected 'host:port' or VISA descriptor.")
