"""ScannerWorker — Multithreaded LAN discovery for LAB-HP power supplies and SCPI instruments."""
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

try:
    from PyQt6.QtCore import QThread, pyqtSignal
except ImportError:
    class QThread:
        def __init__(self, parent=None): pass
        def start(self): pass
        def wait(self, timeout=None): pass
        def isRunning(self): return False
    def pyqtSignal(*args, **kwargs):
        class SignalMock:
            def __init__(self): self._slots = []
            def emit(self, *a, **kw):
                for s in self._slots:
                    try: s(*a, **kw)
                    except Exception: pass
            def connect(self, s): self._slots.append(s)
            def disconnect(self, s=None): pass
        return SignalMock()


import ipaddress

class ScannerWorker(QThread):
    """
    Scans IP targets concurrently on ports:
      - 10001: ETPS LAB-HP 41000 (Sends 'ID\\r\\n')
      - 5025: Rohde & Schwarz RTB2000 (Sends '*IDN?\\n')
    Emits device_found(ip, port, idn, type) and device_discovered(ip, port, idn) on positive response.
    """

    device_found = pyqtSignal(str, int, str, str)  # ip, port, idn, type_str
    device_discovered = pyqtSignal(str, int, str)  # ip, port, idn
    scan_progress = pyqtSignal(int)                # percent completed (0-100)
    scan_finished = pyqtSignal()
    scan_completed = pyqtSignal(list)

    def __init__(
        self,
        targets=None,
        ports: Optional[List[int]] = None,
        timeout: float = 0.5,
        timeout_s: Optional[float] = None,
        parent=None
    ):
        super().__init__(parent)
        self.ports = ports or [10001, 5025]
        self.timeout_s = timeout_s if timeout_s is not None else timeout
        self._stop_event = threading.Event()
        self.discovered_list = []

        # Parse targets (can be list of ips, single IP, or subnet CIDR)
        if targets is None:
            self.ip_targets = ["127.0.0.1"]
        elif isinstance(targets, list):
            self.ip_targets = targets
        elif isinstance(targets, str):
            if "/" in targets:
                try:
                    net = ipaddress.ip_network(targets, strict=False)
                    hosts = [str(h) for h in net.hosts()]
                    self.ip_targets = hosts if hosts else [str(net.network_address)]
                except Exception:
                    self.ip_targets = [targets.split("/")[0]]
            else:
                self.ip_targets = [targets]
        else:
            self.ip_targets = ["127.0.0.1"]

    def stop(self):
        self._stop_event.set()
        self.wait(1000)

    def _probe_labhp(self, ip: str) -> Optional[dict]:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(self.timeout_s)
                s.connect((ip, 10001))
                s.sendall(b"ID\r\n")
                resp = s.recv(1024).decode("ascii", errors="ignore").strip()
                if resp:
                    return {"ip": ip, "port": 10001, "idn": resp, "type": "LAB-HP 41000"}
        except Exception:
            pass
        return None

    def _probe_rtb2000(self, ip: str) -> Optional[dict]:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(self.timeout_s)
                s.connect((ip, 5025))
                s.sendall(b"*IDN?\n")
                resp = s.recv(1024).decode("ascii", errors="ignore").strip()
                if resp:
                    dev_type = "RTB2000 Scope" if "RTB" in resp or "Rohde" in resp else "SCPI Instrument"
                    return {"ip": ip, "port": 5025, "idn": resp, "type": dev_type}
        except Exception:
            pass
        return None

    def run(self):
        total_probes = len(self.ip_targets) * 2
        completed = 0

        def check_target(ip: str):
            nonlocal completed
            if self._stop_event.is_set():
                return

            res_lab = self._probe_labhp(ip)
            if res_lab:
                self.discovered_list.append(res_lab)
                self.device_found.emit(res_lab["ip"], res_lab["port"], res_lab["idn"], res_lab["type"])
                self.device_discovered.emit(res_lab["ip"], res_lab["port"], res_lab["idn"])

            res_rtb = self._probe_rtb2000(ip)
            if res_rtb:
                self.discovered_list.append(res_rtb)
                self.device_found.emit(res_rtb["ip"], res_rtb["port"], res_rtb["idn"], res_rtb["type"])
                self.device_discovered.emit(res_rtb["ip"], res_rtb["port"], res_rtb["idn"])

            completed += 2
            prog = int((completed / max(1, total_probes)) * 100)
            self.scan_progress.emit(min(100, prog))

        with ThreadPoolExecutor(max_workers=min(32, max(2, len(self.ip_targets)))) as executor:
            futures = [executor.submit(check_target, ip) for ip in self.ip_targets]
            for f in futures:
                if self._stop_event.is_set():
                    break
                try:
                    f.result(timeout=self.timeout_s * 3)
                except Exception:
                    pass

        self.scan_progress.emit(100)
        self.scan_finished.emit()
        self.scan_completed.emit(self.discovered_list)
