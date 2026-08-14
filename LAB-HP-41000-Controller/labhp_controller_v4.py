#!/usr/bin/env python3
"""
LAB-HP 41000 DC Source Controller — PyQt6 Professional Edition (FINAL CLEAN)
================================================================================
Complete GUI for ETPS LAB-HP 41000 (4 kW, 1000 V, 7 A) via LAN.
Uses native ASCII protocol on Telnet port 10001 per official manual.

Features:
- Icon-based decluttered interface
- Industrial circular emergency stop (latching)
- Plot appearance settings in a gear icon dialog
- Editable IP combo with network scanner
- Background measurement thread
- Connection watchdog
- Enhanced logging (pause/resume, stop timestamp filename, temp cleanup)
- Configuration persistence
- Command terminal with history & auto-completion
- Status LED indicators
- Plot saving (current screen / full data)
- Per-setpoint reset buttons, global reset
- Limit-active indicators

Requirements:
    pip install PyQt6 matplotlib

Author: Laboratory Automation
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
    QStyle, QDialog, QDialogButtonBox, QFormLayout
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QSettings, QEvent, QObject
from PyQt6.QtGui import QFont, QColor, QPalette, QPixmap, QIcon, QKeySequence, QShortcut

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


# =============================================================================
# DARK PALETTE (enhanced)
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
QPushButton, QToolButton {
    background-color: #0e639c;
    border: 1px solid #0e639c;
    border-radius: 4px;
    padding: 6px;
    color: white;
    font-weight: bold;
}
QPushButton:hover, QToolButton:hover { background-color: #1177bb; }
QPushButton:pressed, QToolButton:pressed { background-color: #094771; }
QPushButton:disabled, QToolButton:disabled {
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
    background-color: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
                                      stop:0 #ff4d4d, stop:0.8 #cc0000, stop:1 #990000);
    border: 4px solid #ffcc00;
    border-radius: 45px;
    font-size: 12pt;
    font-weight: bold;
    color: white;
    padding: 0;
}
QPushButton#emergency:disabled {
    background-color: #555555;
    border-color: #888888;
    color: #aaaaaa;
}
QPushButton#emergency:latched {
    background-color: #660000;
    border-color: #ff6600;
    color: #ffcccc;
}
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
QLabel#led {
    min-width: 16px;
    max-width: 16px;
    min-height: 16px;
    max-height: 16px;
    border-radius: 8px;
    border: 1px solid #3c3c3c;
}
QLabel#limit_warning {
    color: #ffcc00;
    font-weight: bold;
    font-size: 10pt;
    background-color: transparent;
}
"""


# =============================================================================
# CONTROLLER
# =============================================================================
class LABHPController:
    """Native ASCII controller for LAB-HP 41000 via TCP port 10001."""

    MAX_VOLTAGE = 1000.0
    MAX_CURRENT = 7.0
    MAX_POWER   = 4000.0

    def __init__(self):
        self.sock = None
        self._lock = threading.Lock()
        self.connected = False
        self.ip = ""
        self.port = 10001
        self.timeout = 5.0

    def connect(self, ip, port=10001):
        if self.connected:
            self.disconnect()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect((ip, port))
        self.ip = ip
        self.port = port
        self.connected = True
        time.sleep(0.2)
        try:
            self.sock.settimeout(0.5)
            self.sock.recv(4096)
        except socket.timeout:
            pass
        self.sock.settimeout(self.timeout)
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

    def _send(self, cmd, expect_response=False, retries=1):
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

    def get_idn(self): return self._send("ID", expect_response=True, retries=2)
    def set_remote(self): self._send("GTR")
    def set_local(self): self._send("GTL")
    def reset(self): self._send("*RST")
    def set_voltage(self, v): self._send(f"UA,{v:.2f}")
    def get_voltage_setpoint(self): return self._parse_value(self._send("UA", expect_response=True, retries=2))
    def measure_voltage(self): return self._parse_value(self._send("MU", expect_response=True, retries=2))
    def set_current(self, i): self._send(f"IA,{i:.4f}")
    def get_current_setpoint(self): return self._parse_value(self._send("IA", expect_response=True, retries=2))
    def measure_current(self): return self._parse_value(self._send("MI", expect_response=True, retries=2))
    def set_power(self, p): self._send(f"PA,{p:.2f}")
    def get_power_setpoint(self): return self._parse_value(self._send("PA", expect_response=True, retries=2))
    def measure_power(self):
        u = self.measure_voltage()
        i = self.measure_current()
        return u * i
    def output_on(self): self._send("SB,R")
    def output_off(self): self._send("SB,S")
    def get_output_state(self):
        resp = self._send("SB", expect_response=True, retries=2)
        if "," in resp:
            state = resp.split(",", 1)[1].strip().upper()
            return state == "R"
        return False
    def set_ovp(self, v): self._send(f"OVP,{v:.1f}")
    def get_ovp(self): return self._parse_value(self._send("OVP", expect_response=True, retries=2))
    def set_mode(self, mode): self._send(f"MODE,{mode}")
    def get_mode(self):
        resp = self._send("MODE", expect_response=True, retries=2)
        if "," in resp:
            return resp.split(",")[1].strip()
        return resp
    def get_status_raw(self): return self._send("STATUS", expect_response=True, retries=2)
    def get_limit_voltage(self): return self._parse_value(self._send("LIMU", expect_response=True, retries=2))
    def get_limit_current(self): return self._parse_value(self._send("LIMI", expect_response=True, retries=2))
    def get_limit_power(self): return self._parse_value(self._send("LIMP", expect_response=True, retries=2))
    def save_setup(self): self._send("SS")
    def measure_all(self):
        u = self.measure_voltage()
        i = self.measure_current()
        return {"voltage": u, "current": i, "power": u * i}

    @staticmethod
    def _parse_value(resp):
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
    def decode_status(raw):
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


# =============================================================================
# NETWORK SCANNER THREAD
# =============================================================================
class NetworkScanner(QThread):
    progress = pyqtSignal(int, int)
    device_found = pyqtSignal(str, str)
    finished_scan = pyqtSignal(list)

    def __init__(self, port=10001, timeout=0.3):
        super().__init__()
        self.port = port
        self.timeout = timeout
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
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
            future_to_ip = {executor.submit(self._test_ip, ip): ip for ip in targets}
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
        try:
            import psutil
            ips = []
            for iface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET:
                        ips.append((addr.address, addr.netmask))
            return ips
        except ImportError:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
                return [(ip, "255.255.255.0")]
            except Exception:
                return []

    def _get_network(self, ip, netmask):
        ip_parts = list(map(int, ip.split('.')))
        mask_parts = list(map(int, netmask.split('.')))
        if len(ip_parts) != 4 or len(mask_parts) != 4:
            return []
        if mask_parts[0] == 255 and mask_parts[1] == 255 and mask_parts[2] == 255:
            base = ".".join(map(str, ip_parts[:3]))
            return [f"{base}.{i}" for i in range(1, 255)]
        elif mask_parts[0] == 255 and mask_parts[1] == 255:
            base = ".".join(map(str, ip_parts[:2]))
            return [f"{base}.{i}.{j}" for i in range(1, 255) for j in range(1, 255)]
        elif mask_parts[0] == 255:
            return [f"{ip_parts[0]}.{i}.{j}.{k}" for i in range(1, 255)
                    for j in range(1, 255) for k in range(1, 255)]
        else:
            base = ".".join(map(str, ip_parts[:3]))
            return [f"{base}.{i}" for i in range(1, 255)]

    def _test_ip(self, ip):
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
                return "Unknown device"
        except Exception:
            return None


# =============================================================================
# MEASUREMENT THREAD
# =============================================================================
class MeasurementThread(QThread):
    measurements_updated = pyqtSignal(dict)
    output_state_updated = pyqtSignal(bool)
    status_updated = pyqtSignal(dict)
    error = pyqtSignal(str)
    connection_lost = pyqtSignal()
    local_mode_detected = pyqtSignal(bool)

    def __init__(self, controller, interval):
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
                    if not self.controller.connected:
                        self.connection_lost.emit()
                        break
            self._stop_event.wait(self.interval)
            self._trigger_event.clear()

    def stop(self):
        self._stop_event.set()
        self.wait(5000)

    def trigger_measurement(self):
        self._trigger_event.set()


# =============================================================================
# LOGGING THREAD (temp file, rename on stop)
# =============================================================================
class LoggingThread(QThread):
    log_line = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, controller, interval, temp_path, log_volt, log_curr, log_pow, log_set):
        super().__init__()
        self.controller = controller
        self.interval = max(0.1, interval)
        self.temp_path = temp_path
        self.log_volt = log_volt
        self.log_curr = log_curr
        self.log_pow = log_pow
        self.log_set = log_set
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._current_file = None

    def run(self):
        self._stop_event.clear()
        try:
            self._current_file = open(self.temp_path, "w", newline="", encoding="utf-8")
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
            self.log_line.emit(f"Logging to temporary file: {self.temp_path}")

            while not self._stop_event.is_set():
                self._pause_event.wait()
                if self._stop_event.is_set():
                    break
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
# MAIN WINDOW
# =============================================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LAB-HP 41000 — DC Source Control & Logger")
        self.setMinimumSize(1200, 900)
        self.controller = LABHPController()
        self.log_thread = None
        self.measure_thread = None
        self.scanner_thread = None
        self.settings = QSettings("MyCompany", "LABHPController")
        self.temp_log_path = None
        self.final_log_path = None
        self.emergency_latched = False

        # Plot appearance attributes (loaded from settings later)
        self.plot_bg_color = "Dark"
        self.plot_grid = False
        self.plot_legend = True
        self.plot_xlabel = "Time (s)"
        self.plot_ylabel = "Value"
        self.plot_title = ""

        self._build_ui()
        self.setStyleSheet(DARK_STYLESHEET)

        # Clean leftover temp files
        self._cleanup_temp_files()

        # Load settings (including plot appearance)
        self._load_settings()

        # Watchdog
        self.watchdog_timer = QTimer(self)
        self.watchdog_timer.timeout.connect(self._watchdog_check)
        self.watchdog_timer.start(5000)

        self.command_history = []
        self.history_index = -1
        self._setup_completer()

        self.emergency_shortcut = QShortcut(QKeySequence("Ctrl+E"), self)
        self.emergency_shortcut.activated.connect(self._emergency_stop)

    # -------------------------------------------------------------------------
    # CLEANUP
    # -------------------------------------------------------------------------
    def _cleanup_temp_files(self):
        for f in Path.cwd().glob("lab_hp_log_temp_*.csv"):
            try:
                f.unlink()
                print(f"Deleted stale temp file: {f}")
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # UI BUILDING
    # -------------------------------------------------------------------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(12, 12, 12, 12)

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

        conn_layout.addWidget(QLabel("IP:"))
        self.ip_combo = QComboBox()
        self.ip_combo.setEditable(True)
        self.ip_combo.setMinimumWidth(140)
        self.ip_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        conn_layout.addWidget(self.ip_combo)

        self.btn_scan = QToolButton()
        self.btn_scan.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.btn_scan.setToolTip("Scan network")
        self.btn_scan.clicked.connect(self._scan_network)
        conn_layout.addWidget(self.btn_scan)

        conn_layout.addWidget(QLabel("Port:"))
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(10001)
        self.port_spin.setFixedWidth(70)
        conn_layout.addWidget(self.port_spin)

        self.btn_connect = QToolButton()
        self.btn_connect.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOkButton))
        self.btn_connect.setToolTip("Connect")
        self.btn_connect.clicked.connect(self._connect)
        conn_layout.addWidget(self.btn_connect)

        self.btn_disconnect = QToolButton()
        self.btn_disconnect.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton))
        self.btn_disconnect.setToolTip("Disconnect")
        self.btn_disconnect.setEnabled(False)
        self.btn_disconnect.clicked.connect(self._disconnect)
        conn_layout.addWidget(self.btn_disconnect)

        self.lbl_conn_status = QLabel("Disconnected")
        self.lbl_conn_status.setStyleSheet("color: #c75450; font-weight: bold;")
        conn_layout.addWidget(self.lbl_conn_status)

        self.lbl_idn = QLabel("Instrument: —")
        self.lbl_idn.setStyleSheet("color: #808080;")
        conn_layout.addWidget(self.lbl_idn)

        conn_layout.addStretch()

        # Industrial Emergency Stop (Option A)
        self.btn_emergency = QPushButton("EMERGENCY\nSTOP")
        self.btn_emergency.setObjectName("emergency")
        self.btn_emergency.setFixedSize(90, 90)
        self.btn_emergency.setEnabled(False)
        self.btn_emergency.setProperty("latched", False)
        self.btn_emergency.clicked.connect(self._emergency_stop)
        conn_layout.addWidget(self.btn_emergency, alignment=Qt.AlignmentFlag.AlignRight)

        main_layout.addWidget(conn_box)

        # Tabs
        tabs = QTabWidget()
        main_layout.addWidget(tabs, 1)

        control_tab = QWidget()
        tabs.addTab(control_tab, "  Control  ")
        self._build_control_tab(control_tab)

        logger_tab = QWidget()
        tabs.addTab(logger_tab, "  Data Logger  ")
        self._build_logger_tab(logger_tab)

        adv_tab = QWidget()
        tabs.addTab(adv_tab, "  Advanced  ")
        self._build_advanced_tab(adv_tab)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _build_control_tab(self, parent):
        layout = QHBoxLayout(parent)
        layout.setSpacing(15)

        left = QVBoxLayout()

        set_box = QGroupBox("Setpoints")
        set_grid = QGridLayout(set_box)

        # Voltage
        set_grid.addWidget(QLabel("Voltage Setpoint:"), 0, 0)
        self.spin_volt = QDoubleSpinBox()
        self.spin_volt.setRange(0, self.controller.MAX_VOLTAGE)
        self.spin_volt.setDecimals(2)
        self.spin_volt.setSuffix(" V")
        self.spin_volt.setFixedWidth(120)
        set_grid.addWidget(self.spin_volt, 0, 1)
        self.btn_set_volt = QToolButton()
        self.btn_set_volt.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.btn_set_volt.setToolTip("Apply voltage")
        self.btn_set_volt.setEnabled(False)
        self.btn_set_volt.clicked.connect(self._set_voltage)
        set_grid.addWidget(self.btn_set_volt, 0, 2)
        self.btn_reset_volt = QToolButton()
        self.btn_reset_volt.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.btn_reset_volt.setToolTip("Reset to 0 V")
        self.btn_reset_volt.setEnabled(False)
        self.btn_reset_volt.clicked.connect(self._reset_voltage)
        set_grid.addWidget(self.btn_reset_volt, 0, 3)

        # Current
        set_grid.addWidget(QLabel("Current Limit:"), 1, 0)
        self.spin_curr = QDoubleSpinBox()
        self.spin_curr.setRange(0, self.controller.MAX_CURRENT)
        self.spin_curr.setDecimals(4)
        self.spin_curr.setSuffix(" A")
        self.spin_curr.setFixedWidth(120)
        set_grid.addWidget(self.spin_curr, 1, 1)
        self.btn_set_curr = QToolButton()
        self.btn_set_curr.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.btn_set_curr.setToolTip("Apply current")
        self.btn_set_curr.setEnabled(False)
        self.btn_set_curr.clicked.connect(self._set_current)
        set_grid.addWidget(self.btn_set_curr, 1, 2)
        self.btn_reset_curr = QToolButton()
        self.btn_reset_curr.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.btn_reset_curr.setToolTip("Reset to max (7.0 A)")
        self.btn_reset_curr.setEnabled(False)
        self.btn_reset_curr.clicked.connect(self._reset_current)
        set_grid.addWidget(self.btn_reset_curr, 1, 3)

        # Power
        set_grid.addWidget(QLabel("Power Limit:"), 2, 0)
        self.spin_pow = QDoubleSpinBox()
        self.spin_pow.setRange(0, self.controller.MAX_POWER)
        self.spin_pow.setDecimals(2)
        self.spin_pow.setSuffix(" W")
        self.spin_pow.setFixedWidth(120)
        set_grid.addWidget(self.spin_pow, 2, 1)
        self.btn_set_pow = QToolButton()
        self.btn_set_pow.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.btn_set_pow.setToolTip("Apply power")
        self.btn_set_pow.setEnabled(False)
        self.btn_set_pow.clicked.connect(self._set_power)
        set_grid.addWidget(self.btn_set_pow, 2, 2)
        self.btn_reset_pow = QToolButton()
        self.btn_reset_pow.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.btn_reset_pow.setToolTip("Reset to max (4000 W)")
        self.btn_reset_pow.setEnabled(False)
        self.btn_reset_pow.clicked.connect(self._reset_power)
        set_grid.addWidget(self.btn_reset_pow, 2, 3)

        # OVP
        set_grid.addWidget(QLabel("OVP Setting:"), 3, 0)
        self.spin_ovp = QDoubleSpinBox()
        self.spin_ovp.setRange(0, self.controller.MAX_VOLTAGE * 1.2)
        self.spin_ovp.setDecimals(1)
        self.spin_ovp.setSuffix(" V")
        self.spin_ovp.setFixedWidth(120)
        set_grid.addWidget(self.spin_ovp, 3, 1)
        self.btn_set_ovp = QToolButton()
        self.btn_set_ovp.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.btn_set_ovp.setToolTip("Apply OVP")
        self.btn_set_ovp.setEnabled(False)
        self.btn_set_ovp.clicked.connect(self._set_ovp)
        set_grid.addWidget(self.btn_set_ovp, 3, 2)
        self.btn_reset_ovp = QToolButton()
        self.btn_reset_ovp.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.btn_reset_ovp.setToolTip("Reset to safe OVP (1100 V)")
        self.btn_reset_ovp.setEnabled(False)
        self.btn_reset_ovp.clicked.connect(self._reset_ovp)
        set_grid.addWidget(self.btn_reset_ovp, 3, 3)

        # Global reset
        self.btn_reset_all = QToolButton()
        self.btn_reset_all.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.btn_reset_all.setToolTip("Reset all setpoints")
        self.btn_reset_all.setEnabled(False)
        self.btn_reset_all.clicked.connect(self._reset_all_setpoints)
        set_grid.addWidget(self.btn_reset_all, 4, 1, 1, 2)

        set_grid.setColumnStretch(4, 1)
        left.addWidget(set_box)

        # Mode selector
        mode_box = QGroupBox("Operating Mode")
        mode_layout = QHBoxLayout(mode_box)
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["UI", "UIP", "UIR", "PVSIM", "USER"])
        self.combo_mode.setEnabled(False)
        mode_layout.addWidget(self.combo_mode)
        self.btn_set_mode = QToolButton()
        self.btn_set_mode.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.btn_set_mode.setToolTip("Set mode")
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

        self.lbl_limit_warning = QLabel("")
        self.lbl_limit_warning.setObjectName("limit_warning")
        self.lbl_limit_warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        meas_layout.addWidget(self.lbl_limit_warning, 2, 0, 1, 3)

        self.btn_refresh = QToolButton()
        self.btn_refresh.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.btn_refresh.setToolTip("Refresh measurements")
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.clicked.connect(self._force_measurement)
        meas_layout.addWidget(self.btn_refresh, 3, 0, 1, 3)

        right.addWidget(meas_box)

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

    def _build_logger_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setSpacing(10)

        # Top controls row
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Log Base:"))
        self.log_path_edit = QLineEdit("lab_hp_log")
        top_layout.addWidget(self.log_path_edit, 1)
        self.btn_browse = QToolButton()
        self.btn_browse.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        self.btn_browse.setToolTip("Choose log base name")
        self.btn_browse.clicked.connect(self._browse_log)
        top_layout.addWidget(self.btn_browse)
        top_layout.addWidget(QLabel("Interval(s):"))
        self.log_interval_spin = QDoubleSpinBox()
        self.log_interval_spin.setRange(0.1, 3600)
        self.log_interval_spin.setValue(1.0)
        self.log_interval_spin.setDecimals(1)
        top_layout.addWidget(self.log_interval_spin)
        layout.addLayout(top_layout)

        # Channel checkboxes
        chk_layout = QHBoxLayout()
        self.chk_log_volt = QCheckBox("Voltage")
        self.chk_log_volt.setChecked(True)
        self.chk_log_curr = QCheckBox("Current")
        self.chk_log_curr.setChecked(True)
        self.chk_log_pow = QCheckBox("Power")
        self.chk_log_pow.setChecked(True)
        self.chk_log_set = QCheckBox("Setpoints+State")
        self.chk_log_set.setChecked(True)
        chk_layout.addWidget(self.chk_log_volt)
        chk_layout.addWidget(self.chk_log_curr)
        chk_layout.addWidget(self.chk_log_pow)
        chk_layout.addWidget(self.chk_log_set)
        chk_layout.addStretch()
        layout.addLayout(chk_layout)

        # Control buttons (icon only)
        btn_layout = QHBoxLayout()
        self.btn_start_log = QToolButton()
        self.btn_start_log.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.btn_start_log.setToolTip("Start Logging")
        self.btn_start_log.setEnabled(False)
        self.btn_start_log.clicked.connect(self._start_logging)
        btn_layout.addWidget(self.btn_start_log)

        self.btn_stop_log = QToolButton()
        self.btn_stop_log.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.btn_stop_log.setToolTip("Stop Logging")
        self.btn_stop_log.setEnabled(False)
        self.btn_stop_log.clicked.connect(self._stop_logging)
        btn_layout.addWidget(self.btn_stop_log)

        self.btn_pause_log = QToolButton()
        self.btn_pause_log.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        self.btn_pause_log.setToolTip("Pause/Resume Logging")
        self.btn_pause_log.setEnabled(False)
        self.btn_pause_log.clicked.connect(self._pause_logging)
        btn_layout.addWidget(self.btn_pause_log)

        self.lbl_log_status = QLabel("Logging: Stopped")
        self.lbl_log_status.setStyleSheet("color: #808080; font-weight: bold;")
        btn_layout.addWidget(self.lbl_log_status)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Plot area (large)
        splitter = QSplitter(Qt.Orientation.Vertical)

        plot_container = QWidget()
        plot_layout = QVBoxLayout(plot_container)
        plot_layout.setContentsMargins(0, 0, 0, 0)

        # Channel visibility and plot settings gear
        vis_layout = QHBoxLayout()
        self.chk_plot_volt = QCheckBox("Voltage")
        self.chk_plot_volt.setChecked(True)
        self.chk_plot_volt.stateChanged.connect(self._update_plot_visibility)
        self.chk_plot_curr = QCheckBox("Current")
        self.chk_plot_curr.setChecked(True)
        self.chk_plot_curr.stateChanged.connect(self._update_plot_visibility)
        self.chk_plot_pow = QCheckBox("Power")
        self.chk_plot_pow.setChecked(True)
        self.chk_plot_pow.stateChanged.connect(self._update_plot_visibility)
        vis_layout.addWidget(self.chk_plot_volt)
        vis_layout.addWidget(self.chk_plot_curr)
        vis_layout.addWidget(self.chk_plot_pow)

        self.btn_plot_settings = QToolButton()
        self.btn_plot_settings.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self.btn_plot_settings.setToolTip("Plot appearance settings")
        self.btn_plot_settings.clicked.connect(self._open_plot_settings)
        vis_layout.addWidget(self.btn_plot_settings)

        self.btn_save_plot = QToolButton()
        self.btn_save_plot.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.btn_save_plot.setToolTip("Save plot")
        self.btn_save_plot.clicked.connect(self._save_plot)
        vis_layout.addWidget(self.btn_save_plot)

        vis_layout.addStretch()
        plot_layout.addLayout(vis_layout)

        # Matplotlib figure
        self.fig = Figure(figsize=(8, 4), facecolor="#1e1e1e")
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("#1e1e1e")
        self.ax.tick_params(colors="#d4d4d4")
        for spine in self.ax.spines.values():
            spine.set_color("#3c3c3c")
        self.line_volt, = self.ax.plot([], [], "#569cd6", label="Voltage (V)", linewidth=1.2)
        self.line_curr, = self.ax.plot([], [], "#b5cea8", label="Current (A)", linewidth=1.2)
        self.line_pow,  = self.ax.plot([], [], "#ce9178", label="Power (W)", linewidth=1.2)
        self.ax.legend(facecolor="#1e1e1e", edgecolor="#3c3c3c", labelcolor="#d4d4d4")
        self.canvas = FigureCanvas(self.fig)
        plot_layout.addWidget(self.canvas)

        splitter.addWidget(plot_container)

        # Log text
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.document().setMaximumBlockCount(1000)
        splitter.addWidget(self.log_text)
        splitter.setSizes([600, 200])

        layout.addWidget(splitter, 1)

        self.plot_t: list[float] = []
        self.plot_v: list[float] = []
        self.plot_i: list[float] = []
        self.plot_p: list[float] = []
        self.plot_start_time: float | None = None

        self._update_plot_appearance()

    def _build_advanced_tab(self, parent):
        layout = QVBoxLayout(parent)

        # Command terminal
        term_box = QGroupBox("Command Terminal")
        term_layout = QGridLayout(term_box)
        term_layout.addWidget(QLabel("Command:"), 0, 0)
        self.cmd_edit = QLineEdit()
        self.cmd_edit.setPlaceholderText("e.g. ID  or  UA,50  or  MU")
        self.cmd_edit.returnPressed.connect(self._send_command)
        self.cmd_edit.installEventFilter(self)
        term_layout.addWidget(self.cmd_edit, 0, 1)
        self.btn_send = QToolButton()
        self.btn_send.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOkButton))
        self.btn_send.setToolTip("Send command")
        self.btn_send.setEnabled(False)
        self.btn_send.clicked.connect(self._send_command)
        term_layout.addWidget(self.btn_send, 0, 2)
        term_layout.addWidget(QLabel("Response:"), 1, 0)
        self.lbl_resp = QLabel("—")
        self.lbl_resp.setStyleSheet("color: #b5cea8; font-family: Consolas;")
        self.lbl_resp.setWordWrap(True)
        term_layout.addWidget(self.lbl_resp, 1, 1, 1, 2)
        layout.addWidget(term_box)

        # Quick commands as dropdown
        quick_box = QGroupBox("Quick Commands")
        quick_layout = QHBoxLayout(quick_box)
        self.combo_quick = QComboBox()
        self.combo_quick.addItems([
            "ID", "MU", "MI", "UA", "IA", "PA", "OVP",
            "SB,R", "SB,S", "STATUS", "MODE", "LIMU", "LIMI", "LIMP",
            "GTR", "GTL", "*RST", "SS"
        ])
        quick_layout.addWidget(self.combo_quick)
        self.btn_quick_send = QToolButton()
        self.btn_quick_send.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOkButton))
        self.btn_quick_send.setToolTip("Send quick command")
        self.btn_quick_send.clicked.connect(self._send_quick_command)
        quick_layout.addWidget(self.btn_quick_send)
        quick_layout.addStretch()
        layout.addWidget(quick_box)

        # Device info
        info_box = QGroupBox("Device Information")
        info_layout = QVBoxLayout(info_box)
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(150)
        info_layout.addWidget(self.info_text)
        self.btn_read_info = QToolButton()
        self.btn_read_info.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView))
        self.btn_read_info.setToolTip("Read device info")
        self.btn_read_info.setEnabled(False)
        self.btn_read_info.clicked.connect(self._read_info)
        info_layout.addWidget(self.btn_read_info)
        layout.addWidget(info_box)

        # Status LEDs
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
        self.btn_update_status = QToolButton()
        self.btn_update_status.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.btn_update_status.setToolTip("Update status")
        self.btn_update_status.setEnabled(False)
        self.btn_update_status.clicked.connect(self._manual_status_update)
        status_layout.addWidget(self.btn_update_status, 4, 0, 1, 4)
        layout.addWidget(status_box)

        layout.addStretch()

    # -------------------------------------------------------------------------
    # SETTINGS PERSISTENCE
    # -------------------------------------------------------------------------
    def _load_settings(self):
        ips = self.settings.value("ip_history", [])
        if ips:
            self.ip_combo.addItems(ips)
        last_ip = self.settings.value("last_ip", "")
        if last_ip:
            self.ip_combo.setCurrentText(last_ip)
        self.port_spin.setValue(self.settings.value("port", 10001, type=int))

        self.log_path_edit.setText(self.settings.value("log_base_name", "lab_hp_log"))
        self.log_interval_spin.setValue(self.settings.value("log_interval", 1.0, type=float))
        self.chk_log_volt.setChecked(self.settings.value("log_volt", True, type=bool))
        self.chk_log_curr.setChecked(self.settings.value("log_curr", True, type=bool))
        self.chk_log_pow.setChecked(self.settings.value("log_pow", True, type=bool))
        self.chk_log_set.setChecked(self.settings.value("log_set", True, type=bool))

        self.chk_poll.setChecked(self.settings.value("poll_enabled", False, type=bool))
        self.spin_poll_ms.setValue(self.settings.value("poll_ms", 1000, type=int))
        self.chk_safety.setChecked(self.settings.value("safety_confirm", True, type=bool))

        self.plot_bg_color = self.settings.value("plot_bg", "Dark")
        self.plot_grid = self.settings.value("plot_grid", False, type=bool)
        self.plot_legend = self.settings.value("plot_legend", True, type=bool)
        self.plot_xlabel = self.settings.value("plot_xlabel", "Time (s)")
        self.plot_ylabel = self.settings.value("plot_ylabel", "Value")
        self.plot_title = self.settings.value("plot_title", "")

        self._update_plot_appearance()

    def _save_settings(self):
        current_ip = self.ip_combo.currentText().strip()
        if current_ip:
            self.settings.setValue("last_ip", current_ip)
            history = []
            for i in range(self.ip_combo.count()):
                text = self.ip_combo.itemText(i)
                if text and text not in history:
                    history.append(text)
            if current_ip not in history:
                history.insert(0, current_ip)
            self.settings.setValue("ip_history", history[:10])
        self.settings.setValue("port", self.port_spin.value())
        self.settings.setValue("log_base_name", self.log_path_edit.text())
        self.settings.setValue("log_interval", self.log_interval_spin.value())
        self.settings.setValue("log_volt", self.chk_log_volt.isChecked())
        self.settings.setValue("log_curr", self.chk_log_curr.isChecked())
        self.settings.setValue("log_pow", self.chk_log_pow.isChecked())
        self.settings.setValue("log_set", self.chk_log_set.isChecked())
        self.settings.setValue("poll_enabled", self.chk_poll.isChecked())
        self.settings.setValue("poll_ms", self.spin_poll_ms.value())
        self.settings.setValue("safety_confirm", self.chk_safety.isChecked())
        self.settings.setValue("plot_bg", self.plot_bg_color)
        self.settings.setValue("plot_grid", self.plot_grid)
        self.settings.setValue("plot_legend", self.plot_legend)
        self.settings.setValue("plot_xlabel", self.plot_xlabel)
        self.settings.setValue("plot_ylabel", self.plot_ylabel)
        self.settings.setValue("plot_title", self.plot_title)

    # -------------------------------------------------------------------------
    # COMMAND HISTORY
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
        existing = [self.ip_combo.itemText(i) for i in range(self.ip_combo.count())]
        if ip not in existing:
            self.ip_combo.addItem(ip)
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
    # CONNECTION
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
            self.status_bar.showMessage(f"Connected to {ip}:{port} – Remote mode set")
            self._read_info()
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
        self.lbl_out_state.setText("Output: OFF")
        self.lbl_out_state.setStyleSheet("color: #c75450; font-weight: bold; font-size: 12pt;")
        self.status_bar.showMessage("Disconnected")

    def _set_controls_enabled(self, enabled):
        widgets = [
            self.btn_disconnect, self.btn_set_volt, self.btn_set_curr,
            self.btn_set_pow, self.btn_set_ovp, self.btn_set_mode,
            self.btn_out_on, self.btn_out_off, self.btn_refresh,
            self.btn_start_log, self.btn_send, self.btn_read_info,
            self.btn_update_status, self.btn_quick_send,
            self.cmd_edit, self.combo_mode, self.combo_quick,
            self.btn_reset_volt, self.btn_reset_curr,
            self.btn_reset_pow, self.btn_reset_ovp,
            self.btn_reset_all, self.btn_plot_settings
        ]
        for w in widgets:
            w.setEnabled(enabled)
        self.btn_connect.setEnabled(not enabled)
        self.btn_emergency.setEnabled(enabled)
        if not enabled:
            self.btn_pause_log.setEnabled(False)

    # -------------------------------------------------------------------------
    # MEASUREMENT THREAD
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
        if status.get("Current limit") or status.get("Power limit"):
            self.lbl_limit_warning.setText("LIMIT ACTIVE")
        else:
            self.lbl_limit_warning.setText("")

    def _on_measurement_error(self, error_msg):
        self.status_bar.showMessage(f"Measurement error: {error_msg}")

    def _on_connection_lost(self):
        if self.controller.connected:
            self._disconnect()
            QMessageBox.warning(self, "Connection Lost", "The connection to the device was lost.")

    def _on_local_mode_detected(self, is_local):
        if is_local:
            self.status_bar.showMessage("Warning: Device is in Local mode. Remote commands may be ignored.")

    # -------------------------------------------------------------------------
    # WATCHDOG
    # -------------------------------------------------------------------------
    def _watchdog_check(self):
        if not self.controller.connected:
            return
        try:
            self.controller.get_idn()
        except Exception:
            self._on_connection_lost()

    # -------------------------------------------------------------------------
    # SETPOINTS
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

    def _reset_voltage(self):
        self.spin_volt.setValue(0.0)
        self._set_voltage()

    def _reset_current(self):
        self.spin_curr.setValue(self.controller.MAX_CURRENT)
        self._set_current()

    def _reset_power(self):
        self.spin_pow.setValue(self.controller.MAX_POWER)
        self._set_power()

    def _reset_ovp(self):
        self.spin_ovp.setValue(1100.0)
        self._set_ovp()

    def _reset_all_setpoints(self):
        self._reset_voltage()
        self._reset_current()
        self._reset_power()
        self._reset_ovp()
        self.status_bar.showMessage("All setpoints reset to defaults")

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
        if not self.emergency_latched:
            try:
                self.controller.output_off()
                self.controller.set_local()
                self._on_output_state_updated(False)
                self.emergency_latched = True
                self.btn_emergency.setProperty("latched", True)
                self.btn_emergency.setText("STOPPED")
                self.btn_emergency.style().unpolish(self.btn_emergency)
                self.btn_emergency.style().polish(self.btn_emergency)
                self.status_bar.showMessage("EMERGENCY STOP ACTIVATED: Output OFF and Local mode set.")
            except Exception as e:
                QMessageBox.critical(self, "Emergency Stop Failed", str(e))
        else:
            # Reset latch (does not turn output on)
            self.emergency_latched = False
            self.btn_emergency.setProperty("latched", False)
            self.btn_emergency.setText("EMERGENCY\nSTOP")
            self.btn_emergency.style().unpolish(self.btn_emergency)
            self.btn_emergency.style().polish(self.btn_emergency)
            self.status_bar.showMessage("Emergency stop reset. Output remains OFF.")

    # -------------------------------------------------------------------------
    # LOGGING
    # -------------------------------------------------------------------------
    def _browse_log(self):
        path, _ = QFileDialog.getSaveFileName(self, "Set Log Base Name", self.log_path_edit.text(), "CSV (*.csv)")
        if path:
            base, ext = os.path.splitext(path)
            base = re.sub(r'_\d{8}_\d{6}$', '', base)
            self.log_path_edit.setText(base + ".csv")

    def _start_logging(self):
        base_path = self.log_path_edit.text().strip()
        if not base_path:
            QMessageBox.warning(self, "Log Error", "Please specify a log file base name.")
            return
        unique_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.temp_log_path = f"lab_hp_log_temp_{unique_id}.csv"
        self.final_log_path = None

        self.plot_t.clear()
        self.plot_v.clear()
        self.plot_i.clear()
        self.plot_p.clear()
        self.plot_start_time = None

        self.log_thread = LoggingThread(
            self.controller,
            self.log_interval_spin.value(),
            self.temp_log_path,
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
        self.status_bar.showMessage(f"Logging started to temporary file: {self.temp_log_path}")

    def _stop_logging(self):
        if self.log_thread and self.log_thread.isRunning():
            self.log_thread.stop()
            self.log_thread.wait(5000)

            if self.temp_log_path and os.path.exists(self.temp_log_path):
                stop_ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                base, ext = os.path.splitext(self.log_path_edit.text())
                final_name = f"{base}_{stop_ts}.csv"
                try:
                    os.rename(self.temp_log_path, final_name)
                    self.final_log_path = final_name
                    self.status_bar.showMessage(f"Log saved as: {final_name}")
                except Exception as e:
                    QMessageBox.critical(self, "Rename Error", f"Could not rename temp file: {e}")
                    self.final_log_path = self.temp_log_path
            else:
                self.final_log_path = None

        self.log_thread = None
        self.temp_log_path = None
        self.btn_start_log.setEnabled(True)
        self.btn_stop_log.setEnabled(False)
        self.btn_pause_log.setEnabled(False)
        self.btn_pause_log.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        self.lbl_log_status.setText("Logging: Stopped")
        self.lbl_log_status.setStyleSheet("color: #808080; font-weight: bold;")

    def _pause_logging(self):
        if self.log_thread and self.log_thread.isRunning():
            if self.btn_pause_log.icon().cacheKey() == self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause).cacheKey():
                self.log_thread.pause()
                self.btn_pause_log.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
                self.lbl_log_status.setText("Logging: PAUSED")
                self.lbl_log_status.setStyleSheet("color: #c8c800; font-weight: bold;")
            else:
                self.log_thread.resume()
                self.btn_pause_log.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
                self.lbl_log_status.setText("Logging: RUNNING")
                self.lbl_log_status.setStyleSheet("color: #2ea043; font-weight: bold;")

    def _on_log_line(self, line):
        self.log_text.append(line)

    def _on_log_error(self, error_msg):
        QMessageBox.critical(self, "Log Error", error_msg)
        self._stop_logging()

    # -------------------------------------------------------------------------
    # PLOT APPEARANCE & SAVING
    # -------------------------------------------------------------------------
    def _open_plot_settings(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Plot Settings")
        form = QFormLayout(dialog)

        bg_combo = QComboBox()
        bg_combo.addItems(["Dark", "White"])
        bg_combo.setCurrentText(self.plot_bg_color)
        form.addRow("Background:", bg_combo)

        grid_check = QCheckBox()
        grid_check.setChecked(self.plot_grid)
        form.addRow("Show grid:", grid_check)

        legend_check = QCheckBox()
        legend_check.setChecked(self.plot_legend)
        form.addRow("Show legend:", legend_check)

        xlabel_edit = QLineEdit(self.plot_xlabel)
        form.addRow("X label:", xlabel_edit)

        ylabel_edit = QLineEdit(self.plot_ylabel)
        form.addRow("Y label:", ylabel_edit)

        title_edit = QLineEdit(self.plot_title)
        form.addRow("Title:", title_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.plot_bg_color = bg_combo.currentText()
            self.plot_grid = grid_check.isChecked()
            self.plot_legend = legend_check.isChecked()
            self.plot_xlabel = xlabel_edit.text()
            self.plot_ylabel = ylabel_edit.text()
            self.plot_title = title_edit.text()
            self._update_plot_appearance()

    def _update_plot_appearance(self):
        if not hasattr(self, 'ax'):
            return
        bg = self.plot_bg_color
        if bg == "White":
            facecolor = "#ffffff"
            ax_color = "#ffffff"
            tick_color = "#000000"
            spine_color = "#000000"
            legend_face = "#ffffff"
            legend_edge = "#000000"
            legend_text = "#000000"
        else:
            facecolor = "#1e1e1e"
            ax_color = "#1e1e1e"
            tick_color = "#d4d4d4"
            spine_color = "#3c3c3c"
            legend_face = "#1e1e1e"
            legend_edge = "#3c3c3c"
            legend_text = "#d4d4d4"

        self.fig.set_facecolor(facecolor)
        self.ax.set_facecolor(ax_color)
        self.ax.tick_params(colors=tick_color)
        for spine in self.ax.spines.values():
            spine.set_color(spine_color)

        legend = self.ax.get_legend()
        if legend:
            legend.set_visible(self.plot_legend)
            legend.get_frame().set_facecolor(legend_face)
            legend.get_frame().set_edgecolor(legend_edge)
            for text in legend.get_texts():
                text.set_color(legend_text)
        else:
            if self.plot_legend:
                self.ax.legend(facecolor=legend_face, edgecolor=legend_edge, labelcolor=legend_text)

        self.ax.grid(self.plot_grid)
        self.ax.set_xlabel(self.plot_xlabel, color=tick_color)
        self.ax.set_ylabel(self.plot_ylabel, color=tick_color)
        self.ax.set_title(self.plot_title, color=tick_color)
        self.canvas.draw_idle()

    def _update_plot_visibility(self):
        self.line_volt.set_visible(self.chk_plot_volt.isChecked())
        self.line_curr.set_visible(self.chk_plot_curr.isChecked())
        self.line_pow.set_visible(self.chk_plot_pow.isChecked())
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw_idle()

    def _save_plot(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Save Plot")
        msg_box.setText("Choose what to save:")
        btn_current = msg_box.addButton("Current Screen", QMessageBox.ButtonRole.AcceptRole)
        btn_full = msg_box.addButton("Full Data Log", QMessageBox.ButtonRole.ActionRole)
        msg_box.addButton(QMessageBox.StandardButton.Cancel)
        msg_box.exec()

        if msg_box.clickedButton() == btn_current:
            self._save_current_screen()
        elif msg_box.clickedButton() == btn_full:
            self._save_full_data()

    def _save_current_screen(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Current Screen", "", "PNG (*.png);;PDF (*.pdf);;SVG (*.svg)")
        if not file_path:
            return
        try:
            self.fig.savefig(file_path, facecolor=self.fig.get_facecolor())
            self.status_bar.showMessage(f"Plot saved to {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))

    def _save_full_data(self):
        if not self.final_log_path or not os.path.exists(self.final_log_path):
            QMessageBox.warning(self, "Full Data Save", "No stopped log file available. Please stop logging first.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Select Channels for Full Data Plot")
        layout = QVBoxLayout(dialog)
        chk_v = QCheckBox("Voltage")
        chk_v.setChecked(True)
        chk_i = QCheckBox("Current")
        chk_i.setChecked(True)
        chk_p = QCheckBox("Power")
        chk_p.setChecked(True)
        layout.addWidget(chk_v)
        layout.addWidget(chk_i)
        layout.addWidget(chk_p)
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Full Data Plot", "", "PNG (*.png);;PDF (*.pdf);;SVG (*.svg)")
        if not file_path:
            return

        try:
            with open(self.final_log_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader)
                idx_time = header.index("UnixTime") if "UnixTime" in header else None
                idx_v = header.index("Voltage_Meas_V") if "Voltage_Meas_V" in header else None
                idx_i = header.index("Current_Meas_A") if "Current_Meas_A" in header else None
                idx_p = header.index("Power_Meas_W") if "Power_Meas_W" in header else None

                times = []
                v_vals = []
                i_vals = []
                p_vals = []
                first_time = None

                for row in reader:
                    t = float(row[idx_time]) if idx_time is not None else 0.0
                    if first_time is None:
                        first_time = t
                    t_elapsed = t - first_time
                    times.append(t_elapsed)
                    if chk_v.isChecked() and idx_v is not None:
                        v_vals.append(float(row[idx_v]))
                    if chk_i.isChecked() and idx_i is not None:
                        i_vals.append(float(row[idx_i]))
                    if chk_p.isChecked() and idx_p is not None:
                        p_vals.append(float(row[idx_p]))

                fig_full, ax_full = self._create_plot_figure()

                if chk_v.isChecked() and v_vals:
                    ax_full.plot(times, v_vals, "#569cd6", label="Voltage (V)")
                if chk_i.isChecked() and i_vals:
                    ax_full.plot(times, i_vals, "#b5cea8", label="Current (A)")
                if chk_p.isChecked() and p_vals:
                    ax_full.plot(times, p_vals, "#ce9178", label="Power (W)")

                ax_full.set_xlabel(self.plot_xlabel)
                ax_full.set_ylabel(self.plot_ylabel)
                ax_full.set_title(self.plot_title)
                if self.plot_legend:
                    legend_face = fig_full.get_facecolor()
                    legend_edge = '#3c3c3c' if self.plot_bg_color == "Dark" else '#000000'
                    legend_text = '#d4d4d4' if self.plot_bg_color == "Dark" else '#000000'
                    ax_full.legend(facecolor=legend_face, edgecolor=legend_edge, labelcolor=legend_text)
                ax_full.grid(self.plot_grid)

                fig_full.savefig(file_path, facecolor=fig_full.get_facecolor())
                self.status_bar.showMessage(f"Full data plot saved to {file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Full Data Plot Error", str(e))

    def _create_plot_figure(self):
        bg = self.plot_bg_color
        if bg == "White":
            facecolor = "#ffffff"
            ax_color = "#ffffff"
            tick_color = "#000000"
            spine_color = "#000000"
        else:
            facecolor = "#1e1e1e"
            ax_color = "#1e1e1e"
            tick_color = "#d4d4d4"
            spine_color = "#3c3c3c"

        fig = Figure(figsize=(8, 4), facecolor=facecolor)
        ax = fig.add_subplot(111)
        ax.set_facecolor(ax_color)
        ax.tick_params(colors=tick_color)
        for spine in ax.spines.values():
            spine.set_color(spine_color)
        return fig, ax

    # -------------------------------------------------------------------------
    # COMMAND SENDING
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

    def _send_quick_command(self):
        cmd = self.combo_quick.currentText()
        self.cmd_edit.setText(cmd)
        self._send_command()

    def _quick_cmd(self, cmd):
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