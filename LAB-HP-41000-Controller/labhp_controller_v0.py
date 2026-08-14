#!/usr/bin/env python3
"""
LAB-HP 41000 DC Source Controller — PyQt6 Professional Edition (FULLY ENHANCED)
================================================================================
Complete GUI for ETPS LAB-HP 41000 (4 kW, 1000 V, 7 A) via LAN.
Uses native ASCII protocol on Telnet port 10001 per official manual.

Enhancements over previous version:
- Editable IP combo with network scanner
- Background measurement thread (no UI blocking)
- Connection watchdog
- Enhanced logging (daily file splitting, pause/resume)
- Configuration persistence via QSettings
- Command terminal with history and auto-completion
- Status LED indicators
- Emergency stop button
- Plot channel toggles and save image
- Remote/local mode detection and warning
- Thread-safe disconnection
- Verified output state readback
- Correct STATUS bit decoding

Requirements:
    pip install PyQt6 matplotlib

Author: Laboratory Automation (improved)
Date: 2026-08-14
"""

import sys
import socket
import threading
import time
import csv
import datetime
import re
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QTabWidget, QGroupBox, QLabel, QLineEdit, QSpinBox,
    QDoubleSpinBox, QPushButton, QCheckBox, QTextEdit, QLCDNumber,
    QFileDialog, QMessageBox, QSplitter, QFrame, QProgressBar,
    QSizePolicy, QStatusBar, QComboBox, QCompleter, QToolButton,
    QStyle, QDialog, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QSettings, QEvent, QObject
from PyQt6.QtGui import QFont, QColor, QPalette, QPixmap, QIcon, QKeySequence, QShortcut

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


# =============================================================================
# DARK PALETTE (enhanced with additional styles)
# =============================================================================
DARK_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #1e1e1e;
    color: #d4d4d4;
    font-family: "Segoe UI", "Helvetica Neue", sans-serif;
    font-size: 10pt;
}
QGroupBox {
    border: 1px solid #3c3c3c;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
    color: #cccccc;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}
QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox {
    background-color: #252526;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    padding: 4px;
    color: #d4d4d4;
    selection-background-color: #264f78;
}
QPushButton {
    background-color: #0e639c;
    border: 1px solid #0e639c;
    border-radius: 4px;
    padding: 6px 14px;
    color: white;
    font-weight: bold;
}
QPushButton:hover { background-color: #1177bb; }
QPushButton:pressed { background-color: #094771; }
QPushButton:disabled {
    background-color: #3c3c3c;
    border-color: #3c3c3c;
    color: #808080;
}
QPushButton#danger {
    background-color: #c75450;
    border-color: #c75450;
}
QPushButton#danger:hover { background-color: #d9706c; }
QPushButton#success {
    background-color: #2ea043;
    border-color: #2ea043;
}
QPushButton#success:hover { background-color: #3fb950; }
QPushButton#emergency {
    background-color: #ff0000;
    border-color: #ff0000;
    font-size: 14pt;
    font-weight: bold;
    padding: 12px;
}
QPushButton#emergency:hover { background-color: #cc0000; }
QTextEdit {
    background-color: #252526;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    color: #d4d4d4;
    font-family: "Consolas", "Courier New", monospace;
}
QLCDNumber {
    background-color: #000000;
    color: #00ff41;
    border: 2px solid #3c3c3c;
    border-radius: 4px;
}
QStatusBar {
    background-color: #007acc;
    color: white;
}
QTabWidget::pane {
    border: 1px solid #3c3c3c;
    background-color: #1e1e1e;
}
QTabBar::tab {
    background-color: #2d2d2d;
    border: 1px solid #3c3c3c;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background-color: #1e1e1e;
    border-bottom: 2px solid #007acc;
}
QCheckBox { color: #d4d4d4; }
QProgressBar {
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    text-align: center;
    color: white;
}
QProgressBar::chunk { background-color: #007acc; }
QLabel#led {
    min-width: 16px;
    max-width: 16px;
    min-height: 16px;
    max-height: 16px;
    border-radius: 8px;
    border: 1px solid #3c3c3c;
}
"""


# =============================================================================
# CONTROLLER — Native ASCII protocol on port 10001 (FIXED & SAFE)
# =============================================================================
class LABHPController:
    """Native ASCII controller for LAB-HP 41000 via TCP port 10001."""

    MAX_VOLTAGE = 1000.0   # V
    MAX_CURRENT = 7.0      # A
    MAX_POWER   = 4000.0   # W

    def __init__(self):
        self.sock = None
        self._lock = threading.Lock()
        self.connected = False
        self.ip = ""
        self.port = 10001
        self.timeout = 5.0
        self._last_error = ""

    def connect(self, ip: str, port: int = 10001) -> bool:
        if self.connected:
            self.disconnect()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect((ip, port))
        self.ip = ip
        self.port = port
        self.connected = True
        # Flush any banner / startup noise
        time.sleep(0.2)
        try:
            self.sock.settimeout(0.5)
            self.sock.recv(4096)
        except socket.timeout:
            pass
        self.sock.settimeout(self.timeout)
        # Ensure remote mode
        self.set_remote()
        return True

    def disconnect(self):
        self.connected = False
        sock = self.sock
        self.sock = None
        if sock:
            try:
                sock.close()
            except Exception:
                pass

    def _send(self, cmd: str, expect_response: bool = False, retries: int = 1) -> str:
        """Send a command and optionally read the response."""
        with self._lock:
            if not self.sock:
                raise ConnectionError("Not connected")
            data = (cmd + "\r\n").encode("ascii")
            for attempt in range(retries + 1):
                try:
                    self.sock.sendall(data)
                    if expect_response:
                        resp = b""
                        deadline = time.time() + self.timeout
                        while time.time() < deadline:
                            try:
                                chunk = self.sock.recv(4096)
                                if not chunk:
                                    break
                                resp += chunk
                                if b"\n" in resp or b"\r" in resp:
                                    break
                            except socket.timeout:
                                break
                        return resp.decode("ascii", errors="ignore").strip()
                    return ""
                except (socket.timeout, OSError) as e:
                    if attempt < retries:
                        time.sleep(0.1)
                        continue
                    raise ConnectionError(f"Send failed after {retries} retries: {e}")
            return ""

    # --- Verified commands from manual ---
    def get_idn(self) -> str:
        return self._send("ID", expect_response=True, retries=2)

    def set_remote(self):
        self._send("GTR")

    def set_local(self):
        self._send("GTL")

    def reset(self):
        self._send("*RST")

    def set_voltage(self, v: float):
        self._send(f"UA,{v:.2f}")

    def get_voltage_setpoint(self) -> float:
        resp = self._send("UA", expect_response=True, retries=2)
        return self._parse_value(resp)

    def measure_voltage(self) -> float:
        resp = self._send("MU", expect_response=True, retries=2)
        return self._parse_value(resp)

    def set_current(self, i: float):
        self._send(f"IA,{i:.4f}")

    def get_current_setpoint(self) -> float:
        resp = self._send("IA", expect_response=True, retries=2)
        return self._parse_value(resp)

    def measure_current(self) -> float:
        resp = self._send("MI", expect_response=True, retries=2)
        return self._parse_value(resp)

    def set_power(self, p: float):
        self._send(f"PA,{p:.2f}")

    def get_power_setpoint(self) -> float:
        resp = self._send("PA", expect_response=True, retries=2)
        return self._parse_value(resp)

    def measure_power(self) -> float:
        u = self.measure_voltage()
        i = self.measure_current()
        return u * i

    def output_on(self):
        self._send("SB,R")

    def output_off(self):
        self._send("SB,S")

    def get_output_state(self) -> bool:
        resp = self._send("SB", expect_response=True, retries=2)
        if "," in resp:
            state = resp.split(",", 1)[1].strip().upper()
            return state == "R"
        return False

    def set_ovp(self, v: float):
        self._send(f"OVP,{v:.1f}")

    def get_ovp(self) -> float:
        resp = self._send("OVP", expect_response=True, retries=2)
        return self._parse_value(resp)

    def set_mode(self, mode: str):
        self._send(f"MODE,{mode}")

    def get_mode(self) -> str:
        resp = self._send("MODE", expect_response=True, retries=2)
        if "," in resp:
            return resp.split(",")[1].strip()
        return resp

    def get_status_raw(self) -> str:
        return self._send("STATUS", expect_response=True, retries=2)

    def get_limit_voltage(self) -> float:
        resp = self._send("LIMU", expect_response=True, retries=2)
        return self._parse_value(resp)

    def get_limit_current(self) -> float:
        resp = self._send("LIMI", expect_response=True, retries=2)
        return self._parse_value(resp)

    def get_limit_power(self) -> float:
        resp = self._send("LIMP", expect_response=True, retries=2)
        return self._parse_value(resp)

    def save_setup(self):
        self._send("SS")

    def measure_all(self) -> dict:
        u = self.measure_voltage()
        i = self.measure_current()
        return {
            "voltage": u,
            "current": i,
            "power": u * i,
        }

    @staticmethod
    def _parse_value(resp: str) -> float:
        """Parse a numeric value from a response like 'UA,123.4V' or '123.4'."""
        if not resp:
            return 0.0
        if "," in resp:
            _, val_part = resp.split(",", 1)
        else:
            val_part = resp
        match = re.search(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", val_part)
        if match:
            return float(match.group())
        return 0.0

    @staticmethod
    def decode_status(raw: str) -> dict:
        """Decode the STATUS binary word into human-readable flags (correct bit order)."""
        bits = raw.replace("STATUS,", "").strip()
        if not bits:
            return {}
        bits = bits.zfill(16)
        bits_rev = bits[::-1]  # LSB first
        bit_list = [int(b) for b in bits_rev]
        flags = {
            "OVP shutdown": bool(bit_list[0]),
            "Standby": bool(bit_list[1]),
            "Remote mode": bool(bit_list[4]),
            "Local mode": bool(bit_list[5]),
            "Local lockout": bool(bit_list[6]),
            "Current limit": bool(bit_list[7]),
            "Power limit": bool(bit_list[8]),
            "Raw": raw.strip()
        }
        return flags


# =============================================================================
# NETWORK SCANNER THREAD
# =============================================================================
class NetworkScanner(QThread):
    """Scans local subnets for devices responding on port 10001."""
    progress = pyqtSignal(int, int)          # (current, total)
    device_found = pyqtSignal(str, str)      # (ip, id_string)
    finished_scan = pyqtSignal(list)          # list of (ip, id_string)

    def __init__(self, port=10001, timeout=0.3):
        super().__init__()
        self.port = port
        self.timeout = timeout
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        # Get local IPs and subnets
        local_ips = self._get_local_ips()
        all_targets = set()
        for ip, netmask in local_ips:
            network = self._get_network(ip, netmask)
            if network:
                all_targets.update(network)

        if not all_targets:
            self.finished_scan.emit([])
            return

        targets = list(all_targets)
        total = len(targets)
        results = []
        with ThreadPoolExecutor(max_workers=50) as executor:
            future_to_ip = {
                executor.submit(self._test_ip, ip): ip for ip in targets
            }
            done = 0
            for future in as_completed(future_to_ip):
                if self._stop_event.is_set():
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                ip = future_to_ip[future]
                try:
                    id_str = future.result()
                    if id_str is not None:
                        results.append((ip, id_str))
                        self.device_found.emit(ip, id_str)
                except Exception:
                    pass
                done += 1
                self.progress.emit(done, total)

        if not self._stop_event.is_set():
            self.finished_scan.emit(results)

    def _get_local_ips(self):
        """Return list of (ip, netmask) for all IPv4 interfaces."""
        import psutil  # optional, but we can fallback
        try:
            import psutil
            ips = []
            for iface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET:
                        ips.append((addr.address, addr.netmask))
            return ips
        except ImportError:
            # Fallback: use socket to get a single IP
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
                # guess netmask as /24
                return [(ip, "255.255.255.0")]
            except Exception:
                return []

    def _get_network(self, ip, netmask):
        """Return list of IPs in the same /24 (or according to netmask)."""
        ip_parts = list(map(int, ip.split('.')))
        mask_parts = list(map(int, netmask.split('.')))
        if len(ip_parts) != 4 or len(mask_parts) != 4:
            return []
        # Simple case: assume /24 or /16 or /8
        if mask_parts[0] == 255 and mask_parts[1] == 255 and mask_parts[2] == 255:
            # /24
            base = ".".join(map(str, ip_parts[:3]))
            return [f"{base}.{i}" for i in range(1, 255)]
        elif mask_parts[0] == 255 and mask_parts[1] == 255:
            # /16
            base = ".".join(map(str, ip_parts[:2]))
            return [f"{base}.{i}.{j}" for i in range(1, 255) for j in range(1, 255)]
        elif mask_parts[0] == 255:
            # /8
            return [f"{ip_parts[0]}.{i}.{j}.{k}" for i in range(1, 255)
                    for j in range(1, 255) for k in range(1, 255)]
        else:
            # Fallback to /24
            base = ".".join(map(str, ip_parts[:3]))
            return [f"{base}.{i}" for i in range(1, 255)]

    def _test_ip(self, ip):
        """Try TCP connection and query ID. Return id string or None."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(self.timeout)
                s.connect((ip, self.port))
                s.settimeout(1.0)
                s.sendall(b"ID\r\n")
                resp = b""
                try:
                    while True:
                        chunk = s.recv(1024)
                        if not chunk:
                            break
                        resp += chunk
                        if b"\n" in resp or b"\r" in resp:
                            break
                except socket.timeout:
                    pass
                id_str = resp.decode("ascii", errors="ignore").strip()
                if id_str:
                    return id_str
                # If no ID, still treat as device (maybe just open port)
                return "Unknown device"
        except Exception:
            return None


# =============================================================================
# MEASUREMENT THREAD (Background polling)
# =============================================================================
class MeasurementThread(QThread):
    measurements_updated = pyqtSignal(dict)          # {'voltage', 'current', 'power'}
    output_state_updated = pyqtSignal(bool)
    status_updated = pyqtSignal(dict)
    error = pyqtSignal(str)
    connection_lost = pyqtSignal()
    local_mode_detected = pyqtSignal(bool)

    def __init__(self, controller: LABHPController, interval: float):
        super().__init__()
        self.controller = controller
        self.interval = max(0.1, interval)
        self._stop_event = threading.Event()
        self._trigger_event = threading.Event()

    def run(self):
        while not self._stop_event.is_set():
            try:
                if not self.controller.connected:
                    self.connection_lost.emit()
                    break

                meas = self.controller.measure_all()
                self.measurements_updated.emit(meas)

                out_state = self.controller.get_output_state()
                self.output_state_updated.emit(out_state)

                raw_status = self.controller.get_status_raw()
                status = self.controller.decode_status(raw_status)
                self.status_updated.emit(status)

                if status.get("Local mode", False):
                    self.local_mode_detected.emit(True)
                else:
                    self.local_mode_detected.emit(False)

            except Exception as e:
                if not self._stop_event.is_set():
                    self.error.emit(str(e))
                    # Check if connection lost
                    if not self.controller.connected:
                        self.connection_lost.emit()
                        break

            # Wait for interval or trigger
            self._stop_event.wait(self.interval)
            self._trigger_event.clear()

    def stop(self):
        self._stop_event.set()
        self.wait(5000)

    def trigger_measurement(self):
        self._trigger_event.set()


# =============================================================================
# LOGGING THREAD (Enhanced with pause/resume and daily splitting)
# =============================================================================
class LoggingThread(QThread):
    log_line = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, controller: LABHPController, interval: float, path: str,
                 log_volt=True, log_curr=True, log_pow=True, log_set=True):
        super().__init__()
        self.controller = controller
        self.interval = max(0.1, interval)
        self.base_path = path
        self.log_volt = log_volt
        self.log_curr = log_curr
        self.log_pow = log_pow
        self.log_set = log_set
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # start unpaused
        self._current_file = None

    def run(self):
        self._stop_event.clear()
        try:
            while not self._stop_event.is_set():
                # Wait if paused
                self._pause_event.wait()
                if self._stop_event.is_set():
                    break

                # Determine filename based on date (daily rotation)
                today = datetime.date.today().strftime("%Y%m%d")
                base, ext = os.path.splitext(self.base_path)
                filename = f"{base}_{today}{ext}"

                # Open file if different from current
                if self._current_file is None or self._current_file.name != filename:
                    if self._current_file:
                        self._current_file.close()
                    self._current_file = open(filename, "w", newline="", encoding="utf-8")
                    writer = csv.writer(self._current_file)
                    header = ["Timestamp", "UnixTime"]
                    if self.log_volt:
                        header.extend(["Voltage_Set_V", "Voltage_Meas_V"])
                    if self.log_curr:
                        header.extend(["Current_Set_A", "Current_Meas_A"])
                    if self.log_pow:
                        header.extend(["Power_Set_W", "Power_Meas_W"])
                    if self.log_set:
                        header.append("Output_State")
                    writer.writerow(header)
                    self._current_file.flush()
                    self.log_line.emit(f"New log file: {filename}")

                writer = csv.writer(self._current_file)
                ts = datetime.datetime.now().isoformat()
                ut = time.time()

                meas = self.controller.measure_all()
                v_set = self.controller.get_voltage_setpoint()
                i_set = self.controller.get_current_setpoint()
                p_set = self.controller.get_power_setpoint()
                out_on = self.controller.get_output_state()

                row = [ts, f"{ut:.3f}"]
                if self.log_volt:
                    row.extend([f"{v_set:.4f}", f"{meas['voltage']:.4f}"])
                if self.log_curr:
                    row.extend([f"{i_set:.4f}", f"{meas['current']:.4f}"])
                if self.log_pow:
                    row.extend([f"{p_set:.4f}", f"{meas['power']:.4f}"])
                if self.log_set:
                    row.append("ON" if out_on else "OFF")

                writer.writerow(row)
                self._current_file.flush()
                self.log_line.emit(",".join(row))

                # Interruptible sleep
                self._stop_event.wait(self.interval)

        except Exception as e:
            self.error.emit(str(e))
        finally:
            if self._current_file:
                self._current_file.close()
                self._current_file = None

    def stop(self):
        self._stop_event.set()
        self.wait(10000)

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()


# =============================================================================
# MAIN WINDOW (Enhanced)
# =============================================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LAB-HP 41000 — DC Source Control & Logger")
        self.setMinimumSize(1200, 850)
        self.controller = LABHPController()
        self.log_thread = None
        self.measure_thread = None
        self.scanner_thread = None
        self.settings = QSettings("MyCompany", "LABHPController")

        self._build_ui()
        self.setStyleSheet(DARK_STYLESHEET)

        # Restore settings
        self._load_settings()

        # Connection watchdog timer (checks connection every 5s)
        self.watchdog_timer = QTimer(self)
        self.watchdog_timer.timeout.connect(self._watchdog_check)
        self.watchdog_timer.start(5000)  # ms

        # Setup command history
        self.command_history = []
        self.history_index = -1
        self._setup_completer()

        # Set up emergency stop shortcut (Ctrl+E)
        self.emergency_shortcut = QShortcut(QKeySequence("Ctrl+E"), self)
        self.emergency_shortcut.activated.connect(self._emergency_stop)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # Title
        title = QLabel("LAB-HP 41000  DC High Power Source")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #569cd6;")
        main_layout.addWidget(title)

        subtitle = QLabel("4 kW  |  0-1000 V  |  0-7 A  |  LAN Control & Data Logger")
        subtitle.setFont(QFont("Segoe UI", 10))
        subtitle.setStyleSheet("color: #808080;")
        main_layout.addWidget(subtitle)

        # Connection bar
        conn_box = QGroupBox("LAN Connection")
        conn_layout = QHBoxLayout(conn_box)

        conn_layout.addWidget(QLabel("IP Address:"))
        self.ip_combo = QComboBox()
        self.ip_combo.setEditable(True)
        self.ip_combo.setMinimumWidth(160)
        self.ip_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        conn_layout.addWidget(self.ip_combo)

        self.btn_scan = QPushButton("Scan")
        self.btn_scan.setFixedWidth(70)
        self.btn_scan.clicked.connect(self._scan_network)
        conn_layout.addWidget(self.btn_scan)

        conn_layout.addWidget(QLabel("Port:"))
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(10001)
        self.port_spin.setFixedWidth(80)
        conn_layout.addWidget(self.port_spin)

        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setFixedWidth(100)
        self.btn_connect.clicked.connect(self._connect)
        conn_layout.addWidget(self.btn_connect)

        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_disconnect.setFixedWidth(100)
        self.btn_disconnect.setEnabled(False)
        self.btn_disconnect.clicked.connect(self._disconnect)
        conn_layout.addWidget(self.btn_disconnect)

        self.lbl_conn_status = QLabel("Disconnected")
        self.lbl_conn_status.setStyleSheet("color: #c75450; font-weight: bold;")
        conn_layout.addWidget(self.lbl_conn_status)

        self.lbl_idn = QLabel("Instrument: —")
        self.lbl_idn.setStyleSheet("color: #808080;")
        conn_layout.addWidget(self.lbl_idn)

        # Emergency stop button (always visible)
        self.btn_emergency = QPushButton("EMERGENCY STOP")
        self.btn_emergency.setObjectName("emergency")
        self.btn_emergency.setEnabled(False)
        self.btn_emergency.clicked.connect(self._emergency_stop)
        conn_layout.addWidget(self.btn_emergency, alignment=Qt.AlignmentFlag.AlignRight)

        main_layout.addWidget(conn_box)

        # Tabs
        tabs = QTabWidget()
        main_layout.addWidget(tabs, 1)

        # Control tab
        control_tab = QWidget()
        tabs.addTab(control_tab, "  Control  ")
        self._build_control_tab(control_tab)

        # Logger tab
        logger_tab = QWidget()
        tabs.addTab(logger_tab, "  Data Logger  ")
        self._build_logger_tab(logger_tab)

        # Advanced tab
        adv_tab = QWidget()
        tabs.addTab(adv_tab, "  Advanced  ")
        self._build_advanced_tab(adv_tab)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _build_control_tab(self, parent: QWidget):
        layout = QHBoxLayout(parent)
        layout.setSpacing(15)

        # Left: Setpoints
        left = QVBoxLayout()

        set_box = QGroupBox("Setpoints")
        set_grid = QGridLayout(set_box)

        set_grid.addWidget(QLabel("Voltage Setpoint:"), 0, 0)
        self.spin_volt = QDoubleSpinBox()
        self.spin_volt.setRange(0, self.controller.MAX_VOLTAGE)
        self.spin_volt.setDecimals(2)
        self.spin_volt.setSuffix(" V")
        self.spin_volt.setFixedWidth(120)
        set_grid.addWidget(self.spin_volt, 0, 1)
        self.btn_set_volt = QPushButton("Apply")
        self.btn_set_volt.setEnabled(False)
        self.btn_set_volt.clicked.connect(self._set_voltage)
        set_grid.addWidget(self.btn_set_volt, 0, 2)

        set_grid.addWidget(QLabel("Current Limit:"), 1, 0)
        self.spin_curr = QDoubleSpinBox()
        self.spin_curr.setRange(0, self.controller.MAX_CURRENT)
        self.spin_curr.setDecimals(4)
        self.spin_curr.setSuffix(" A")
        self.spin_curr.setFixedWidth(120)
        set_grid.addWidget(self.spin_curr, 1, 1)
        self.btn_set_curr = QPushButton("Apply")
        self.btn_set_curr.setEnabled(False)
        self.btn_set_curr.clicked.connect(self._set_current)
        set_grid.addWidget(self.btn_set_curr, 1, 2)

        set_grid.addWidget(QLabel("Power Limit:"), 2, 0)
        self.spin_pow = QDoubleSpinBox()
        self.spin_pow.setRange(0, self.controller.MAX_POWER)
        self.spin_pow.setDecimals(2)
        self.spin_pow.setSuffix(" W")
        self.spin_pow.setFixedWidth(120)
        set_grid.addWidget(self.spin_pow, 2, 1)
        self.btn_set_pow = QPushButton("Apply")
        self.btn_set_pow.setEnabled(False)
        self.btn_set_pow.clicked.connect(self._set_power)
        set_grid.addWidget(self.btn_set_pow, 2, 2)

        set_grid.addWidget(QLabel("OVP Setting:"), 3, 0)
        self.spin_ovp = QDoubleSpinBox()
        self.spin_ovp.setRange(0, self.controller.MAX_VOLTAGE * 1.2)
        self.spin_ovp.setDecimals(1)
        self.spin_ovp.setSuffix(" V")
        self.spin_ovp.setFixedWidth(120)
        set_grid.addWidget(self.spin_ovp, 3, 1)
        self.btn_set_ovp = QPushButton("Apply")
        self.btn_set_ovp.setEnabled(False)
        self.btn_set_ovp.clicked.connect(self._set_ovp)
        set_grid.addWidget(self.btn_set_ovp, 3, 2)

        set_grid.setColumnStretch(3, 1)
        left.addWidget(set_box)

        # Mode selector
        mode_box = QGroupBox("Operating Mode")
        mode_layout = QHBoxLayout(mode_box)
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["UI", "UIP", "UIR", "PVSIM", "USER"])
        self.combo_mode.setEnabled(False)
        mode_layout.addWidget(self.combo_mode)
        self.btn_set_mode = QPushButton("Set Mode")
        self.btn_set_mode.setEnabled(False)
        self.btn_set_mode.clicked.connect(self._set_mode)
        mode_layout.addWidget(self.btn_set_mode)
        mode_layout.addStretch()
        left.addWidget(mode_box)

        # Output control
        out_box = QGroupBox("Output Control")
        out_layout = QHBoxLayout(out_box)

        self.btn_out_on = QPushButton("OUTPUT ON")
        self.btn_out_on.setObjectName("success")
        self.btn_out_on.setEnabled(False)
        self.btn_out_on.clicked.connect(self._output_on)
        out_layout.addWidget(self.btn_out_on)

        self.btn_out_off = QPushButton("OUTPUT OFF")
        self.btn_out_off.setObjectName("danger")
        self.btn_out_off.setEnabled(False)
        self.btn_out_off.clicked.connect(self._output_off)
        out_layout.addWidget(self.btn_out_off)

        self.lbl_out_state = QLabel("Output: OFF")
        self.lbl_out_state.setStyleSheet("color: #c75450; font-weight: bold; font-size: 12pt;")
        out_layout.addWidget(self.lbl_out_state)
        out_layout.addStretch()

        left.addWidget(out_box)

        # Safety
        safe_box = QGroupBox("Safety")
        safe_layout = QVBoxLayout(safe_box)
        self.chk_safety = QCheckBox("Confirm before enabling output > 50 V")
        self.chk_safety.setChecked(True)
        safe_layout.addWidget(self.chk_safety)
        left.addWidget(safe_box)

        left.addStretch()
        layout.addLayout(left, 1)

        # Right: Live Measurements
        right = QVBoxLayout()

        meas_box = QGroupBox("Live Measurements")
        meas_layout = QGridLayout(meas_box)

        meas_layout.addWidget(QLabel("Voltage"), 0, 0, Qt.AlignmentFlag.AlignCenter)
        self.lcd_volt = QLCDNumber()
        self.lcd_volt.setDigitCount(8)
        self.lcd_volt.setSegmentStyle(QLCDNumber.SegmentStyle.Flat)
        self.lcd_volt.display("0.00")
        meas_layout.addWidget(self.lcd_volt, 1, 0)

        meas_layout.addWidget(QLabel("Current"), 0, 1, Qt.AlignmentFlag.AlignCenter)
        self.lcd_curr = QLCDNumber()
        self.lcd_curr.setDigitCount(8)
        self.lcd_curr.setSegmentStyle(QLCDNumber.SegmentStyle.Flat)
        self.lcd_curr.display("0.0000")
        meas_layout.addWidget(self.lcd_curr, 1, 1)

        meas_layout.addWidget(QLabel("Power"), 0, 2, Qt.AlignmentFlag.AlignCenter)
        self.lcd_pow = QLCDNumber()
        self.lcd_pow.setDigitCount(8)
        self.lcd_pow.setSegmentStyle(QLCDNumber.SegmentStyle.Flat)
        self.lcd_pow.display("0.0")
        meas_layout.addWidget(self.lcd_pow, 1, 2)

        self.btn_refresh = QPushButton("Refresh Now")
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.clicked.connect(self._force_measurement)
        meas_layout.addWidget(self.btn_refresh, 2, 0, 1, 3)

        right.addWidget(meas_box)

        # Poll config
        poll_box = QGroupBox("Auto-Polling")
        poll_layout = QHBoxLayout(poll_box)
        self.chk_poll = QCheckBox("Enable")
        self.chk_poll.stateChanged.connect(self._toggle_polling)
        poll_layout.addWidget(self.chk_poll)
        poll_layout.addWidget(QLabel("Interval (ms):"))
        self.spin_poll_ms = QSpinBox()
        self.spin_poll_ms.setRange(100, 30000)
        self.spin_poll_ms.setValue(1000)
        self.spin_poll_ms.setSingleStep(100)
        poll_layout.addWidget(self.spin_poll_ms)
        poll_layout.addStretch()
        right.addWidget(poll_box)

        right.addStretch()
        layout.addLayout(right, 1)

    def _build_logger_tab(self, parent: QWidget):
        layout = QVBoxLayout(parent)
        layout.setSpacing(10)

        default_log = f"lab_hp_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        cfg_layout = QHBoxLayout()
        cfg_layout.addWidget(QLabel("Log File:"))
        self.log_path_edit = QLineEdit(default_log)
        cfg_layout.addWidget(self.log_path_edit, 1)
        self.btn_browse = QPushButton("Browse...")
        self.btn_browse.clicked.connect(self._browse_log)
        cfg_layout.addWidget(self.btn_browse)
        cfg_layout.addWidget(QLabel("Interval (s):"))
        self.log_interval_spin = QDoubleSpinBox()
        self.log_interval_spin.setRange(0.1, 3600)
        self.log_interval_spin.setValue(1.0)
        self.log_interval_spin.setDecimals(1)
        cfg_layout.addWidget(self.log_interval_spin)
        layout.addLayout(cfg_layout)

        chk_layout = QHBoxLayout()
        self.chk_log_volt = QCheckBox("Voltage")
        self.chk_log_volt.setChecked(True)
        self.chk_log_curr = QCheckBox("Current")
        self.chk_log_curr.setChecked(True)
        self.chk_log_pow = QCheckBox("Power")
        self.chk_log_pow.setChecked(True)
        self.chk_log_set = QCheckBox("Setpoints + State")
        self.chk_log_set.setChecked(True)
        chk_layout.addWidget(self.chk_log_volt)
        chk_layout.addWidget(self.chk_log_curr)
        chk_layout.addWidget(self.chk_log_pow)
        chk_layout.addWidget(self.chk_log_set)
        chk_layout.addStretch()
        layout.addLayout(chk_layout)

        btn_layout = QHBoxLayout()
        self.btn_start_log = QPushButton("Start Logging")
        self.btn_start_log.setEnabled(False)
        self.btn_start_log.clicked.connect(self._start_logging)
        btn_layout.addWidget(self.btn_start_log)

        self.btn_stop_log = QPushButton("Stop Logging")
        self.btn_stop_log.setEnabled(False)
        self.btn_stop_log.clicked.connect(self._stop_logging)
        btn_layout.addWidget(self.btn_stop_log)

        self.btn_pause_log = QPushButton("Pause")
        self.btn_pause_log.setEnabled(False)
        self.btn_pause_log.clicked.connect(self._pause_logging)
        btn_layout.addWidget(self.btn_pause_log)

        self.lbl_log_status = QLabel("Logging: Stopped")
        self.lbl_log_status.setStyleSheet("color: #808080; font-weight: bold;")
        btn_layout.addWidget(self.lbl_log_status)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # Plot area
        plot_widget = QWidget()
        plot_layout = QVBoxLayout(plot_widget)
        plot_layout.setContentsMargins(0, 0, 0, 0)

        # Channel toggles
        toggle_layout = QHBoxLayout()
        self.chk_plot_volt = QCheckBox("Voltage")
        self.chk_plot_volt.setChecked(True)
        self.chk_plot_volt.stateChanged.connect(self._update_plot_visibility)
        self.chk_plot_curr = QCheckBox("Current")
        self.chk_plot_curr.setChecked(True)
        self.chk_plot_curr.stateChanged.connect(self._update_plot_visibility)
        self.chk_plot_pow = QCheckBox("Power")
        self.chk_plot_pow.setChecked(True)
        self.chk_plot_pow.stateChanged.connect(self._update_plot_visibility)
        self.btn_save_plot = QPushButton("Save Plot")
        self.btn_save_plot.clicked.connect(self._save_plot)
        toggle_layout.addWidget(self.chk_plot_volt)
        toggle_layout.addWidget(self.chk_plot_curr)
        toggle_layout.addWidget(self.chk_plot_pow)
        toggle_layout.addWidget(self.btn_save_plot)
        toggle_layout.addStretch()
        plot_layout.addLayout(toggle_layout)

        self.fig = Figure(figsize=(8, 3), facecolor="#1e1e1e")
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("#1e1e1e")
        self.ax.tick_params(colors="#d4d4d4")
        self.ax.set_xlabel("Time (s)", color="#d4d4d4")
        self.ax.set_ylabel("Value", color="#d4d4d4")
        for spine in self.ax.spines.values():
            spine.set_color("#3c3c3c")
        self.line_volt, = self.ax.plot([], [], "#569cd6", label="Voltage (V)", linewidth=1.2)
        self.line_curr, = self.ax.plot([], [], "#b5cea8", label="Current (A)", linewidth=1.2)
        self.line_pow,  = self.ax.plot([], [], "#ce9178", label="Power (W)", linewidth=1.2)
        self.ax.legend(facecolor="#1e1e1e", edgecolor="#3c3c3c", labelcolor="#d4d4d4")
        self.canvas = FigureCanvas(self.fig)
        plot_layout.addWidget(self.canvas)
        splitter.addWidget(plot_widget)

        # Log text
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.document().setMaximumBlockCount(1000)
        splitter.addWidget(self.log_text)
        splitter.setSizes([350, 250])

        layout.addWidget(splitter, 1)

        self.plot_t: list[float] = []
        self.plot_v: list[float] = []
        self.plot_i: list[float] = []
        self.plot_p: list[float] = []
        self.plot_start_time: float | None = None

    def _build_advanced_tab(self, parent: QWidget):
        layout = QVBoxLayout(parent)

        # Command terminal
        term_box = QGroupBox("Command Terminal")
        term_layout = QGridLayout(term_box)

        term_layout.addWidget(QLabel("Command:"), 0, 0)
        self.cmd_edit = QLineEdit()
        self.cmd_edit.setPlaceholderText("e.g. ID  or  UA,50  or  MU")
        self.cmd_edit.returnPressed.connect(self._send_command)
        self.cmd_edit.installEventFilter(self)  # For up/down history
        term_layout.addWidget(self.cmd_edit, 0, 1)

        self.btn_send = QPushButton("Send")
        self.btn_send.setEnabled(False)
        self.btn_send.clicked.connect(self._send_command)
        term_layout.addWidget(self.btn_send, 0, 2)

        term_layout.addWidget(QLabel("Response:"), 1, 0)
        self.lbl_resp = QLabel("—")
        self.lbl_resp.setStyleSheet("color: #b5cea8; font-family: Consolas;")
        self.lbl_resp.setWordWrap(True)
        term_layout.addWidget(self.lbl_resp, 1, 1, 1, 2)

        layout.addWidget(term_box)

        # Quick Commands
        quick_box = QGroupBox("Quick Commands")
        quick_layout = QGridLayout(quick_box)
        quick_cmds = [
            ("ID", "ID"), ("MU", "MU"), ("MI", "MI"),
            ("UA", "UA"), ("IA", "IA"), ("PA", "PA"),
            ("SB,R", "SB,R"), ("SB,S", "SB,S"), ("OVP", "OVP"),
            ("STATUS", "STATUS"), ("MODE", "MODE"), ("LIMU", "LIMU"),
            ("LIMI", "LIMI"), ("LIMP", "LIMP"), ("GTR", "GTR"),
            ("GTL", "GTL"), ("*RST", "*RST"), ("SS", "SS"),
        ]
        for i, (label, cmd) in enumerate(quick_cmds):
            btn = QPushButton(label)
            btn.clicked.connect(lambda checked, c=cmd: self._quick_cmd(c))
            quick_layout.addWidget(btn, i // 6, i % 6)
        layout.addWidget(quick_box)

        # Device Information
        info_box = QGroupBox("Device Information")
        info_layout = QVBoxLayout(info_box)
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(150)
        info_layout.addWidget(self.info_text)
        self.btn_read_info = QPushButton("Read Device Info")
        self.btn_read_info.setEnabled(False)
        self.btn_read_info.clicked.connect(self._read_info)
        info_layout.addWidget(self.btn_read_info)
        layout.addWidget(info_box)

        # Status LED indicators
        status_box = QGroupBox("Status Indicators")
        status_layout = QGridLayout(status_box)
        self.status_leds = {}
        led_labels = [
            ("Remote", "Remote mode"),
            ("Local", "Local mode"),
            ("Standby", "Standby"),
            ("OVP", "OVP shutdown"),
            ("CurrLim", "Current limit"),
            ("PowLim", "Power limit"),
            ("Lockout", "Local lockout"),
        ]
        for i, (key, desc) in enumerate(led_labels):
            led = QLabel()
            led.setObjectName("led")
            led.setStyleSheet("background-color: #555; border-radius: 8px;")
            led.setFixedSize(16, 16)
            label = QLabel(desc)
            self.status_leds[key] = led
            status_layout.addWidget(led, i // 2, (i % 2) * 2)
            status_layout.addWidget(label, i // 2, (i % 2) * 2 + 1)
        self.btn_update_status = QPushButton("Update Status")
        self.btn_update_status.setEnabled(False)
        self.btn_update_status.clicked.connect(self._manual_status_update)
        status_layout.addWidget(self.btn_update_status, 4, 0, 1, 4)
        layout.addWidget(status_box)

        layout.addStretch()

    # -------------------------------------------------------------------------
    # SETTINGS PERSISTENCE
    # -------------------------------------------------------------------------
    def _load_settings(self):
        # Restore IP combo items
        ips = self.settings.value("ip_history", [])
        if ips:
            self.ip_combo.addItems(ips)
        last_ip = self.settings.value("last_ip", "")
        if last_ip:
            self.ip_combo.setCurrentText(last_ip)
        # Port
        port = self.settings.value("port", 10001, type=int)
        self.port_spin.setValue(port)
        # Log settings
        log_path = self.settings.value("log_path", "")
        if log_path:
            self.log_path_edit.setText(log_path)
        log_interval = self.settings.value("log_interval", 1.0, type=float)
        self.log_interval_spin.setValue(log_interval)
        self.chk_log_volt.setChecked(self.settings.value("log_volt", True, type=bool))
        self.chk_log_curr.setChecked(self.settings.value("log_curr", True, type=bool))
        self.chk_log_pow.setChecked(self.settings.value("log_pow", True, type=bool))
        self.chk_log_set.setChecked(self.settings.value("log_set", True, type=bool))
        # Poll settings
        self.chk_poll.setChecked(self.settings.value("poll_enabled", False, type=bool))
        poll_ms = self.settings.value("poll_ms", 1000, type=int)
        self.spin_poll_ms.setValue(poll_ms)
        # Safety
        self.chk_safety.setChecked(self.settings.value("safety_confirm", True, type=bool))

    def _save_settings(self):
        # Save current IP in combo as last used and update history
        current_ip = self.ip_combo.currentText().strip()
        if current_ip:
            self.settings.setValue("last_ip", current_ip)
            # Update history list
            history = []
            for i in range(self.ip_combo.count()):
                text = self.ip_combo.itemText(i)
                if text and text not in history:
                    history.append(text)
            if current_ip not in history:
                history.insert(0, current_ip)
            self.settings.setValue("ip_history", history[:10])  # keep last 10
        self.settings.setValue("port", self.port_spin.value())
        self.settings.setValue("log_path", self.log_path_edit.text())
        self.settings.setValue("log_interval", self.log_interval_spin.value())
        self.settings.setValue("log_volt", self.chk_log_volt.isChecked())
        self.settings.setValue("log_curr", self.chk_log_curr.isChecked())
        self.settings.setValue("log_pow", self.chk_log_pow.isChecked())
        self.settings.setValue("log_set", self.chk_log_set.isChecked())
        self.settings.setValue("poll_enabled", self.chk_poll.isChecked())
        self.settings.setValue("poll_ms", self.spin_poll_ms.value())
        self.settings.setValue("safety_confirm", self.chk_safety.isChecked())

    # -------------------------------------------------------------------------
    # COMMAND HISTORY & COMPLETER
    # -------------------------------------------------------------------------
    def _setup_completer(self):
        commands = ["ID", "IDN?", "UA", "IA", "PA", "OVP", "SB,R", "SB,S",
                    "MU", "MI", "STATUS", "MODE", "LIMU", "LIMI", "LIMP",
                    "GTR", "GTL", "*RST", "SS"]
        completer = QCompleter(commands, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.cmd_edit.setCompleter(completer)

    def eventFilter(self, obj, event):
        if obj is self.cmd_edit and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Up:
                self._history_prev()
                return True
            elif event.key() == Qt.Key.Key_Down:
                self._history_next()
                return True
        return super().eventFilter(obj, event)

    def _history_prev(self):
        if self.command_history and self.history_index > 0:
            self.history_index -= 1
            self.cmd_edit.setText(self.command_history[self.history_index])

    def _history_next(self):
        if self.command_history and self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            self.cmd_edit.setText(self.command_history[self.history_index])
        else:
            self.history_index = len(self.command_history)
            self.cmd_edit.clear()

    def _add_to_history(self, cmd):
        if cmd and (not self.command_history or self.command_history[-1] != cmd):
            self.command_history.append(cmd)
        self.history_index = len(self.command_history)

    # -------------------------------------------------------------------------
    # NETWORK SCANNING
    # -------------------------------------------------------------------------
    def _scan_network(self):
        if self.scanner_thread and self.scanner_thread.isRunning():
            return
        self.btn_scan.setEnabled(False)
        self.status_bar.showMessage("Scanning network for devices on port 10001...")
        self.scanner_thread = NetworkScanner(port=self.port_spin.value(), timeout=0.5)
        self.scanner_thread.device_found.connect(self._on_device_found)
        self.scanner_thread.finished_scan.connect(self._on_scan_finished)
        self.scanner_thread.start()

    def _on_device_found(self, ip, id_str):
        # Add IP to combo if not present
        existing = [self.ip_combo.itemText(i) for i in range(self.ip_combo.count())]
        if ip not in existing:
            self.ip_combo.addItem(ip)
        # Optionally set the combo's current text to the found IP if user hasn't typed
        if self.ip_combo.currentText().strip() == "":
            self.ip_combo.setCurrentText(ip)
        self.status_bar.showMessage(f"Found device at {ip} ({id_str})")

    def _on_scan_finished(self, results):
        self.btn_scan.setEnabled(True)
        if results:
            self.status_bar.showMessage(f"Scan complete: {len(results)} device(s) found.")
        else:
            self.status_bar.showMessage("Scan complete: no devices found.")

    # -------------------------------------------------------------------------
    # CONNECTION / DISCONNECTION
    # -------------------------------------------------------------------------
    def _connect(self):
        ip = self.ip_combo.currentText().strip()
        try:
            port = int(self.port_spin.value())
        except ValueError:
            QMessageBox.critical(self, "Error", "Invalid port number")
            return
        if not ip:
            QMessageBox.critical(self, "Error", "Please enter an IP address")
            return
        try:
            self.controller.connect(ip, port)
            idn = self.controller.get_idn()
            self.lbl_idn.setText(f"Instrument: {idn}")
            self.lbl_conn_status.setText("Connected")
            self.lbl_conn_status.setStyleSheet("color: #2ea043; font-weight: bold;")
            self._set_controls_enabled(True)
            self.btn_emergency.setEnabled(True)
            self.status_bar.showMessage(f"Connected to {ip}:{port} – Remote mode set")
            self._read_info()
            # Start measurement thread if polling enabled
            if self.chk_poll.isChecked():
                self._start_measurement_thread()
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", str(e))
            self.status_bar.showMessage(f"Connection failed: {e}")

    def _disconnect(self):
        self._stop_logging()
        self._stop_measurement_thread()
        self.controller.disconnect()
        self.lbl_conn_status.setText("Disconnected")
        self.lbl_conn_status.setStyleSheet("color: #c75450; font-weight: bold;")
        self.lbl_idn.setText("Instrument: —")
        self._set_controls_enabled(False)
        self.btn_emergency.setEnabled(False)
        self.lbl_out_state.setText("Output: OFF")
        self.lbl_out_state.setStyleSheet("color: #c75450; font-weight: bold; font-size: 12pt;")
        self.status_bar.showMessage("Disconnected")

    def _set_controls_enabled(self, enabled: bool):
        widgets = [
            self.btn_disconnect, self.btn_set_volt, self.btn_set_curr,
            self.btn_set_pow, self.btn_set_ovp, self.btn_set_mode,
            self.btn_out_on, self.btn_out_off, self.btn_refresh,
            self.btn_start_log, self.btn_send, self.btn_read_info,
            self.btn_update_status,
            self.cmd_edit, self.combo_mode,
        ]
        for w in widgets:
            w.setEnabled(enabled)
        self.btn_connect.setEnabled(not enabled)
        if enabled:
            self.btn_emergency.setEnabled(True)
        else:
            self.btn_emergency.setEnabled(False)
            self.btn_pause_log.setEnabled(False)

    # -------------------------------------------------------------------------
    # MEASUREMENT THREAD MANAGEMENT
    # -------------------------------------------------------------------------
    def _start_measurement_thread(self):
        if self.measure_thread and self.measure_thread.isRunning():
            return
        interval_s = self.spin_poll_ms.value() / 1000.0
        self.measure_thread = MeasurementThread(self.controller, interval_s)
        self.measure_thread.measurements_updated.connect(self._on_measurements_updated)
        self.measure_thread.output_state_updated.connect(self._on_output_state_updated)
        self.measure_thread.status_updated.connect(self._on_status_updated)
        self.measure_thread.error.connect(self._on_measurement_error)
        self.measure_thread.connection_lost.connect(self._on_connection_lost)
        self.measure_thread.local_mode_detected.connect(self._on_local_mode_detected)
        self.measure_thread.start()

    def _stop_measurement_thread(self):
        if self.measure_thread:
            self.measure_thread.stop()
            self.measure_thread = None

    def _toggle_polling(self, state):
        if state == Qt.CheckState.Checked.value:
            if self.controller.connected:
                self._start_measurement_thread()
        else:
            self._stop_measurement_thread()

    def _force_measurement(self):
        if self.measure_thread and self.measure_thread.isRunning():
            self.measure_thread.trigger_measurement()
        else:
            # Fallback: do a single measurement
            self._poll_measurements_once()

    def _poll_measurements_once(self):
        try:
            meas = self.controller.measure_all()
            self._on_measurements_updated(meas)
            out_state = self.controller.get_output_state()
            self._on_output_state_updated(out_state)
            raw_status = self.controller.get_status_raw()
            status = self.controller.decode_status(raw_status)
            self._on_status_updated(status)
        except Exception as e:
            self.status_bar.showMessage(f"Measurement error: {e}")

    def _on_measurements_updated(self, meas):
        self.lcd_volt.display(f"{meas['voltage']:.2f}")
        self.lcd_curr.display(f"{meas['current']:.4f}")
        self.lcd_pow.display(f"{meas['power']:.2f}")
        # Update plot
        now = time.time()
        if self.plot_start_time is None:
            self.plot_start_time = now
        t = now - self.plot_start_time
        self.plot_t.append(t)
        self.plot_v.append(meas["voltage"])
        self.plot_i.append(meas["current"])
        self.plot_p.append(meas["power"])
        if len(self.plot_t) > 300:
            self.plot_t = self.plot_t[-300:]
            self.plot_v = self.plot_v[-300:]
            self.plot_i = self.plot_i[-300:]
            self.plot_p = self.plot_p[-300:]
        self.line_volt.set_data(self.plot_t, self.plot_v)
        self.line_curr.set_data(self.plot_t, self.plot_i)
        self.line_pow.set_data(self.plot_t, self.plot_p)
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw_idle()

    def _on_output_state_updated(self, out_state):
        self.lbl_out_state.setText("Output: ON" if out_state else "Output: OFF")
        self.lbl_out_state.setStyleSheet(
            "color: #2ea043; font-weight: bold; font-size: 12pt;" if out_state
            else "color: #c75450; font-weight: bold; font-size: 12pt;"
        )

    def _on_status_updated(self, status):
        # Update LEDs
        led_map = {
            "Remote": "Remote mode",
            "Local": "Local mode",
            "Standby": "Standby",
            "OVP": "OVP shutdown",
            "CurrLim": "Current limit",
            "PowLim": "Power limit",
            "Lockout": "Local lockout",
        }
        for led_key, status_key in led_map.items():
            led = self.status_leds.get(led_key)
            if led:
                active = status.get(status_key, False)
                color = "#00ff00" if active else "#555555"
                led.setStyleSheet(f"background-color: {color}; border-radius: 8px;")

    def _on_measurement_error(self, error_msg):
        self.status_bar.showMessage(f"Measurement error: {error_msg}")

    def _on_connection_lost(self):
        if self.controller.connected:
            # Actually lost connection, handle gracefully
            self._disconnect()
            QMessageBox.warning(self, "Connection Lost", "The connection to the device was lost.")

    def _on_local_mode_detected(self, is_local):
        if is_local:
            self.status_bar.showMessage("Warning: Device is in Local mode. Remote commands may be ignored.")
            # Optionally auto-send GTR? We'll just warn.

    # -------------------------------------------------------------------------
    # CONNECTION WATCHDOG
    # -------------------------------------------------------------------------
    def _watchdog_check(self):
        if not self.controller.connected:
            return
        try:
            # Send a lightweight query
            self.controller.get_idn()
        except Exception:
            # Connection lost
            self._on_connection_lost()

    # -------------------------------------------------------------------------
    # SETPOINT SLOTS (with error handling)
    # -------------------------------------------------------------------------
    def _safe_command(self, func, success_msg):
        try:
            func()
            self.status_bar.showMessage(success_msg)
        except Exception as e:
            QMessageBox.critical(self, "Command Error", str(e))
            self.status_bar.showMessage(f"Command failed: {e}")

    def _set_voltage(self):
        v = self.spin_volt.value()
        self._safe_command(lambda: self.controller.set_voltage(v), f"Voltage set to {v:.2f} V")

    def _set_current(self):
        i = self.spin_curr.value()
        self._safe_command(lambda: self.controller.set_current(i), f"Current limit set to {i:.4f} A")

    def _set_power(self):
        p = self.spin_pow.value()
        self._safe_command(lambda: self.controller.set_power(p), f"Power limit set to {p:.2f} W")

    def _set_ovp(self):
        v = self.spin_ovp.value()
        self._safe_command(lambda: self.controller.set_ovp(v), f"OVP set to {v:.1f} V")

    def _set_mode(self):
        mode = self.combo_mode.currentText()
        self._safe_command(lambda: self.controller.set_mode(mode), f"Mode set to {mode}")

    def _output_on(self):
        if self.chk_safety.isChecked() and self.spin_volt.value() > 50:
            reply = QMessageBox.question(
                self, "Safety Warning",
                f"Output voltage is set to {self.spin_volt.value():.1f} V.\n\nEnable output?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        try:
            self.controller.output_on()
            # Verify actual state
            actual = self.controller.get_output_state()
            self._on_output_state_updated(actual)
            if actual:
                self.status_bar.showMessage("Output ENABLED")
            else:
                self.status_bar.showMessage("Output command sent but state is OFF")
        except Exception as e:
            QMessageBox.critical(self, "Output Error", str(e))

    def _output_off(self):
        try:
            self.controller.output_off()
            actual = self.controller.get_output_state()
            self._on_output_state_updated(actual)
            self.status_bar.showMessage("Output DISABLED")
        except Exception as e:
            QMessageBox.critical(self, "Output Error", str(e))

    def _emergency_stop(self):
        if not self.controller.connected:
            return
        try:
            self.controller.output_off()
            self.controller.set_local()  # also go to local to prevent remote re-enable
            self._on_output_state_updated(False)
            self.status_bar.showMessage("EMERGENCY STOP ACTIVATED: Output OFF and Local mode set.")
        except Exception as e:
            QMessageBox.critical(self, "Emergency Stop Failed", str(e))

    # -------------------------------------------------------------------------
    # LOGGING SLOTS
    # -------------------------------------------------------------------------
    def _browse_log(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Log", self.log_path_edit.text(), "CSV (*.csv)")
        if path:
            self.log_path_edit.setText(path)

    def _start_logging(self):
        path = self.log_path_edit.text()
        if not path:
            QMessageBox.warning(self, "Log Error", "Please specify a log file path.")
            return
        self.plot_t.clear()
        self.plot_v.clear()
        self.plot_i.clear()
        self.plot_p.clear()
        self.plot_start_time = None

        self.log_thread = LoggingThread(
            self.controller,
            self.log_interval_spin.value(),
            path,
            self.chk_log_volt.isChecked(),
            self.chk_log_curr.isChecked(),
            self.chk_log_pow.isChecked(),
            self.chk_log_set.isChecked(),
        )
        self.log_thread.log_line.connect(self._on_log_line)
        self.log_thread.error.connect(self._on_log_error)
        self.log_thread.start()

        self.btn_start_log.setEnabled(False)
        self.btn_stop_log.setEnabled(True)
        self.btn_pause_log.setEnabled(True)
        self.lbl_log_status.setText("Logging: RUNNING")
        self.lbl_log_status.setStyleSheet("color: #2ea043; font-weight: bold;")
        self.status_bar.showMessage(f"Logging to {path}")

    def _stop_logging(self):
        if self.log_thread and self.log_thread.isRunning():
            self.log_thread.stop()
        self.log_thread = None
        self.btn_start_log.setEnabled(True)
        self.btn_stop_log.setEnabled(False)
        self.btn_pause_log.setEnabled(False)
        self.btn_pause_log.setText("Pause")
        self.lbl_log_status.setText("Logging: Stopped")
        self.lbl_log_status.setStyleSheet("color: #808080; font-weight: bold;")
        self.status_bar.showMessage("Logging stopped")

    def _pause_logging(self):
        if self.log_thread and self.log_thread.isRunning():
            if self.btn_pause_log.text() == "Pause":
                self.log_thread.pause()
                self.btn_pause_log.setText("Resume")
                self.lbl_log_status.setText("Logging: PAUSED")
                self.lbl_log_status.setStyleSheet("color: #c8c800; font-weight: bold;")
            else:
                self.log_thread.resume()
                self.btn_pause_log.setText("Pause")
                self.lbl_log_status.setText("Logging: RUNNING")
                self.lbl_log_status.setStyleSheet("color: #2ea043; font-weight: bold;")

    def _on_log_line(self, line: str):
        self.log_text.append(line)

    def _on_log_error(self, error_msg):
        QMessageBox.critical(self, "Log Error", error_msg)
        self._stop_logging()

    # -------------------------------------------------------------------------
    # PLOT CONTROLS
    # -------------------------------------------------------------------------
    def _update_plot_visibility(self):
        self.line_volt.set_visible(self.chk_plot_volt.isChecked())
        self.line_curr.set_visible(self.chk_plot_curr.isChecked())
        self.line_pow.set_visible(self.chk_plot_pow.isChecked())
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw_idle()

    def _save_plot(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Plot", "", "PNG (*.png);;PDF (*.pdf)")
        if path:
            try:
                self.fig.savefig(path, facecolor=self.fig.get_facecolor())
                self.status_bar.showMessage(f"Plot saved to {path}")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", str(e))

    # -------------------------------------------------------------------------
    # ADVANCED TAB: COMMAND SENDING
    # -------------------------------------------------------------------------
    def _send_command(self):
        cmd = self.cmd_edit.text().strip()
        if not cmd:
            return
        try:
            query_cmds = {"ID", "IDN?", "MU", "MI", "UA", "IA", "PA", "OVP",
                          "STATUS", "MODE", "LIMU", "LIMI", "LIMP", "SB"}
            is_query = ("," not in cmd) and (cmd.upper() in query_cmds)
            if is_query:
                resp = self.controller._send(cmd, expect_response=True, retries=2)
                self.lbl_resp.setText(resp)
                self.status_bar.showMessage(f"Response: {resp}")
            else:
                self.controller._send(cmd)
                self.lbl_resp.setText("(command sent)")
                self.status_bar.showMessage(f"Sent: {cmd}")
            self._add_to_history(cmd)
        except Exception as e:
            self.lbl_resp.setText(f"ERROR: {e}")
            self.status_bar.showMessage(f"Command error: {e}")

    def _quick_cmd(self, cmd: str):
        self.cmd_edit.setText(cmd)
        self._send_command()

    def _read_info(self):
        try:
            lines = [
                f"IDN:      {self.controller.get_idn()}",
                f"Mode:     {self.controller.get_mode()}",
                f"Voltage:  {self.controller.measure_voltage():.3f} V",
                f"Current:  {self.controller.measure_current():.4f} A",
                f"Power:    {self.controller.measure_power():.2f} W",
                f"U Set:    {self.controller.get_voltage_setpoint():.3f} V",
                f"I Set:    {self.controller.get_current_setpoint():.4f} A",
                f"P Set:    {self.controller.get_power_setpoint():.2f} W",
                f"OVP:      {self.controller.get_ovp():.1f} V",
                f"U Limit:  {self.controller.get_limit_voltage():.1f} V",
                f"I Limit:  {self.controller.get_limit_current():.4f} A",
                f"P Limit:  {self.controller.get_limit_power():.1f} W",
                f"Output:   {'ON' if self.controller.get_output_state() else 'OFF'}",
            ]
            self.info_text.setPlainText("\n".join(lines))
            self.status_bar.showMessage("Device info updated")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _manual_status_update(self):
        try:
            raw = self.controller.get_status_raw()
            status = self.controller.decode_status(raw)
            self._on_status_updated(status)
            self.status_bar.showMessage("Status updated")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # -------------------------------------------------------------------------
    # CLOSE EVENT
    # -------------------------------------------------------------------------
    def closeEvent(self, event):
        self._save_settings()
        self._stop_logging()
        self._stop_measurement_thread()
        if self.scanner_thread and self.scanner_thread.isRunning():
            self.scanner_thread.stop()
            self.scanner_thread.wait(2000)
        self.controller.disconnect()
        event.accept()


# =============================================================================
# ENTRY POINT
# =============================================================================
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()