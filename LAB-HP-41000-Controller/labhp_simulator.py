#!/usr/bin/env python3
"""
LAB-HP 41000 Simulator GUI
==========================
Emulates the ETPS LAB-HP 41000 DC source over TCP port 10001.
Allows testing of the main controller GUI without hardware.

Run this file first, then run the main controller GUI.
Use the IP address displayed in the simulator window to connect.

Features:
- Full TCP server implementing the native ASCII protocol
- Adjustable setpoints, load resistance, and manual control
- OVP trip simulation
- Remote/Local mode switching
- Command log
- Thread-safe shared state

Requires: PyQt6

Author: Laboratory Automation
Date: 2026-08-14
"""

import sys
import socket
import threading
import time
import re
import math

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QGroupBox, QLabel, QLineEdit, QSpinBox,
    QDoubleSpinBox, QPushButton, QCheckBox, QTextEdit, QLCDNumber,
    QFileDialog, QMessageBox, QSplitter, QFrame, QProgressBar,
    QSizePolicy, QStatusBar, QComboBox, QSlider, QDialog,
    QDialogButtonBox, QFormLayout
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QSettings, QEvent, QObject
from PyQt6.QtGui import QFont, QColor, QPalette, QKeySequence, QShortcut

import matplotlib
matplotlib.use("QtAgg")  # not used but can be for future plotting
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


# =============================================================================
# DARK PALETTE
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
# DEVICE STATE (shared between GUI and server)
# =============================================================================
class DeviceState:
    """Thread-safe state of the simulated LAB-HP 41000."""

    def __init__(self):
        self._lock = threading.RLock()
        self.reset()

    def reset(self):
        with self._lock:
            self.voltage_setpoint = 0.0        # V
            self.current_limit = 7.0           # A
            self.power_limit = 4000.0          # W
            self.ovp_setting = 1100.0          # V (default > max)
            self.output_on = False
            self.remote_mode = True
            self.local_mode = False
            self.mode = "UI"
            self.load_resistance = 100.0       # ohms
            self.ovp_tripped = False
            self.current_limit_active = False
            self.power_limit_active = False
            self.max_voltage = 1000.0
            self.max_current = 7.0
            self.max_power = 4000.0

    # ------------------------------------------------------------------
    # Setters / Getters (all locked)
    # ------------------------------------------------------------------
    def set_voltage(self, val):
        with self._lock:
            self.voltage_setpoint = min(max(val, 0.0), self.max_voltage)

    def get_voltage_setpoint(self):
        with self._lock:
            return self.voltage_setpoint

    def set_current(self, val):
        with self._lock:
            self.current_limit = min(max(val, 0.0), self.max_current)

    def get_current_limit(self):
        with self._lock:
            return self.current_limit

    def set_power(self, val):
        with self._lock:
            self.power_limit = min(max(val, 0.0), self.max_power)

    def get_power_limit(self):
        with self._lock:
            return self.power_limit

    def set_ovp(self, val):
        with self._lock:
            self.ovp_setting = min(max(val, 0.0), self.max_voltage * 1.2)

    def get_ovp(self):
        with self._lock:
            return self.ovp_setting

    def set_output_on(self, on):
        with self._lock:
            if on and self.ovp_tripped:
                # Cannot turn on until OVP cleared
                self.output_on = False
                return
            self.output_on = on
            if not on:
                self.ovp_tripped = False  # turning off clears OVP latch

    def get_output_on(self):
        with self._lock:
            return self.output_on

    def set_remote_mode(self, remote):
        with self._lock:
            self.remote_mode = remote
            self.local_mode = not remote

    def get_remote_mode(self):
        with self._lock:
            return self.remote_mode

    def get_local_mode(self):
        with self._lock:
            return self.local_mode

    def set_mode(self, mode):
        with self._lock:
            valid_modes = ["UI", "UIP", "UIR", "PVSIM", "USER"]
            if mode in valid_modes:
                self.mode = mode

    def get_mode(self):
        with self._lock:
            return self.mode

    def set_load_resistance(self, ohms):
        with self._lock:
            self.load_resistance = max(ohms, 0.1)  # prevent division by zero

    def get_load_resistance(self):
        with self._lock:
            return self.load_resistance

    def trigger_ovp(self):
        with self._lock:
            self.ovp_tripped = True
            self.output_on = False

    def clear_ovp(self):
        with self._lock:
            self.ovp_tripped = False

    # ------------------------------------------------------------------
    # Measurement computation
    # ------------------------------------------------------------------
    def compute_measurements(self):
        """Return (voltage, current, power) based on current state."""
        with self._lock:
            if not self.output_on or self.ovp_tripped:
                # Output off or OVP tripped -> all zero
                self.current_limit_active = False
                self.power_limit_active = False
                return 0.0, 0.0, 0.0

            v_set = self.voltage_setpoint
            i_limit = self.current_limit
            p_limit = self.power_limit
            r_load = self.load_resistance

            # Ideal current if no limits
            if r_load <= 0:
                i_ideal = i_limit  # short circuit, limited by current limit
            else:
                i_ideal = v_set / r_load

            # Apply current limit
            i_actual = min(i_ideal, i_limit)

            # Apply power limit
            if v_set * i_actual > p_limit:
                # Current must be reduced to respect power limit
                i_actual = p_limit / v_set if v_set > 0 else 0.0

            # Ensure we don't exceed voltage limit (setpoint is already within limit)
            v_actual = v_set if i_actual > 0 else 0.0
            p_actual = v_actual * i_actual

            # Update limit flags
            self.current_limit_active = (i_ideal > i_limit)
            self.power_limit_active = (v_set * i_ideal > p_limit)

            return v_actual, i_actual, p_actual

    # ------------------------------------------------------------------
    # Status word (16-bit, MSB first)
    # ------------------------------------------------------------------
    def get_status_word(self):
        with self._lock:
            # Bits: D15..D0
            # D0 = OVP shutdown
            # D1 = Standby (output off)
            # D4 = Remote mode
            # D5 = Local mode
            # D6 = Local lockout (0)
            # D7 = Current limit
            # D8 = Power limit
            bits = [0] * 16
            bits[0] = 1 if self.ovp_tripped else 0
            bits[1] = 1 if not self.output_on else 0
            bits[4] = 1 if self.remote_mode else 0
            bits[5] = 1 if self.local_mode else 0
            bits[6] = 0  # local lockout not implemented
            # Compute limits flags by calling compute_measurements (updates flags)
            self.compute_measurements()
            bits[7] = 1 if self.current_limit_active else 0
            bits[8] = 1 if self.power_limit_active else 0
            # Convert to MSB-first binary string
            bits_rev = bits[::-1]
            return ''.join(str(b) for b in bits_rev)

    def get_all_snapshot(self):
        """Return a dict copy of all state for GUI display."""
        with self._lock:
            v, i, p = self.compute_measurements()
            return {
                "voltage_setpoint": self.voltage_setpoint,
                "current_limit": self.current_limit,
                "power_limit": self.power_limit,
                "ovp_setting": self.ovp_setting,
                "output_on": self.output_on,
                "remote_mode": self.remote_mode,
                "local_mode": self.local_mode,
                "mode": self.mode,
                "load_resistance": self.load_resistance,
                "ovp_tripped": self.ovp_tripped,
                "current_limit_active": self.current_limit_active,
                "power_limit_active": self.power_limit_active,
                "measured_voltage": v,
                "measured_current": i,
                "measured_power": p,
            }


# =============================================================================
# TCP SERVER THREAD
# =============================================================================
class SimulatorServer(QThread):
    """Listens for connections and processes the native protocol."""
    log_message = pyqtSignal(str)
    client_connected = pyqtSignal(bool)
    error = pyqtSignal(str)

    def __init__(self, state, port=10001):
        super().__init__()
        self.state = state
        self.port = port
        self.running = False
        self.server_socket = None
        self.client_socket = None

    def run(self):
        self.running = True
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', self.port))
            self.server_socket.listen(1)
            self.server_socket.settimeout(1.0)  # allows checking stop flag
            self.log_message.emit(f"Server listening on port {self.port}")
            while self.running:
                try:
                    self.client_socket, addr = self.server_socket.accept()
                    self.client_socket.settimeout(0.5)
                    self.log_message.emit(f"Client connected: {addr[0]}:{addr[1]}")
                    self.client_connected.emit(True)
                    self.handle_client()
                except socket.timeout:
                    continue
                except OSError as e:
                    if self.running:
                        self.log_message.emit(f"Socket error: {e}")
                    break
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.running = False
            if self.client_socket:
                self.client_socket.close()
            if self.server_socket:
                self.server_socket.close()
            self.client_connected.emit(False)
            self.log_message.emit("Server stopped")

    def handle_client(self):
        buffer = b""
        while self.running:
            try:
                data = self.client_socket.recv(4096)
                if not data:
                    break
                buffer += data
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    line = line.strip()
                    if line:
                        self.process_command(line.decode('ascii', errors='ignore'))
            except socket.timeout:
                continue
            except OSError:
                break
        self.log_message.emit("Client disconnected")
        self.client_connected.emit(False)

    def process_command(self, cmd_str):
        cmd_str = cmd_str.strip()
        if not cmd_str:
            return
        self.log_message.emit(f"Received: {cmd_str}")
        parts = cmd_str.split(',', 1)
        cmd = parts[0].strip().upper()
        param = parts[1].strip() if len(parts) > 1 else None

        response = self.execute_command(cmd, param)
        if response is not None:
            self.send_response(response)
            self.log_message.emit(f"Sent: {response}")

    def execute_command(self, cmd, param):
        state = self.state
        # Helper to parse numeric parameter
        def parse_float(s):
            try:
                return float(s)
            except:
                return None

        # Commands
        if cmd == "ID":
            return "LAB-HP 41000 SIMULATOR V1.0"
        elif cmd == "UA":
            if param is not None:
                val = parse_float(param)
                if val is not None:
                    # Only apply if in remote mode? Real device may ignore in local.
                    # We'll allow setting even in local for simulation simplicity,
                    # but optionally we can check remote_mode. We'll apply always.
                    state.set_voltage(val)
                return None
            else:
                return f"UA,{state.get_voltage_setpoint():.2f}"
        elif cmd == "IA":
            if param is not None:
                val = parse_float(param)
                if val is not None:
                    state.set_current(val)
                return None
            else:
                return f"IA,{state.get_current_limit():.4f}"
        elif cmd == "PA":
            if param is not None:
                val = parse_float(param)
                if val is not None:
                    state.set_power(val)
                return None
            else:
                return f"PA,{state.get_power_limit():.2f}"
        elif cmd == "OVP":
            if param is not None:
                val = parse_float(param)
                if val is not None:
                    state.set_ovp(val)
                return None
            else:
                return f"OVP,{state.get_ovp():.1f}"
        elif cmd == "SB":
            if param is not None:
                if param.upper() in ("R", "0"):
                    state.set_output_on(True)
                elif param.upper() in ("S", "1"):
                    state.set_output_on(False)
                return None
            else:
                return f"SB,{'R' if state.get_output_on() else 'S'}"
        elif cmd == "MU":
            v, _, _ = state.compute_measurements()
            return f"{v:.4f}"
        elif cmd == "MI":
            _, i, _ = state.compute_measurements()
            return f"{i:.4f}"
        elif cmd == "GTR":
            state.set_remote_mode(True)
            return None
        elif cmd == "GTL":
            state.set_remote_mode(False)
            return None
        elif cmd == "STATUS":
            status_word = state.get_status_word()
            return f"STATUS,{status_word}"
        elif cmd == "*RST" or cmd == "RI":
            state.reset()
            return None
        elif cmd == "MODE":
            if param is not None:
                state.set_mode(param.upper())
                return None
            else:
                return f"MODE,{state.get_mode()}"
        elif cmd == "LIMU":
            return f"{state.max_voltage:.1f}"
        elif cmd == "LIMI":
            return f"{state.max_current:.4f}"
        elif cmd == "LIMP":
            return f"{state.max_power:.1f}"
        elif cmd == "SS":
            # Simulate save (no actual file)
            return "OK"
        else:
            self.log_message.emit(f"Unknown command: {cmd}")
            return None

    def send_response(self, response):
        if self.client_socket:
            try:
                self.client_socket.sendall((response + "\r\n").encode('ascii'))
            except OSError as e:
                self.log_message.emit(f"Send error: {e}")

    def stop_server(self):
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        self.wait(2000)


# =============================================================================
# SIMULATOR GUI
# =============================================================================
class SimulatorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LAB-HP 41000 Simulator")
        self.setMinimumSize(900, 700)
        self.state = DeviceState()
        self.server = None
        self._updating_ui = False

        self._build_ui()
        self.setStyleSheet(DARK_STYLESHEET)

        # Timer to refresh display
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._refresh_display)
        self.update_timer.start(200)  # 5 Hz

        # Automatically start server on default port
        self.start_server()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # Title
        title = QLabel("LAB-HP 41000 Device Simulator")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #569cd6;")
        main_layout.addWidget(title)

        # Server configuration
        server_box = QGroupBox("Server Configuration")
        server_layout = QHBoxLayout(server_box)
        server_layout.addWidget(QLabel("Port:"))
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(10001)
        self.port_spin.setFixedWidth(80)
        server_layout.addWidget(self.port_spin)

        self.btn_start = QPushButton("Start Server")
        self.btn_start.clicked.connect(self.start_server)
        server_layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton("Stop Server")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_server)
        server_layout.addWidget(self.btn_stop)

        self.lbl_server_status = QLabel("Server: Stopped")
        self.lbl_server_status.setStyleSheet("color: #c75450; font-weight: bold;")
        server_layout.addWidget(self.lbl_server_status)

        server_layout.addStretch()
        main_layout.addWidget(server_box)

        # IP address display
        ip_box = QGroupBox("Device IP Addresses")
        ip_layout = QVBoxLayout(ip_box)
        self.lbl_ips = QLabel("Detecting...")
        self.lbl_ips.setStyleSheet("color: #b5cea8; font-family: Consolas;")
        ip_layout.addWidget(self.lbl_ips)
        self.btn_refresh_ips = QPushButton("Refresh IPs")
        self.btn_refresh_ips.clicked.connect(self._update_ip_display)
        ip_layout.addWidget(self.btn_refresh_ips)
        main_layout.addWidget(ip_box)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter, 1)

        # Left panel: Controls and state
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(10)

        # Setpoints
        setpoint_box = QGroupBox("Device Setpoints (Remote can change)")
        setpoint_grid = QGridLayout(setpoint_box)

        setpoint_grid.addWidget(QLabel("Voltage (V):"), 0, 0)
        self.spin_voltage = QDoubleSpinBox()
        self.spin_voltage.setRange(0, 1000)
        self.spin_voltage.setDecimals(2)
        self.spin_voltage.setValue(0)
        self.spin_voltage.valueChanged.connect(self._on_voltage_changed)
        setpoint_grid.addWidget(self.spin_voltage, 0, 1)

        setpoint_grid.addWidget(QLabel("Current (A):"), 1, 0)
        self.spin_current = QDoubleSpinBox()
        self.spin_current.setRange(0, 7)
        self.spin_current.setDecimals(4)
        self.spin_current.setValue(7)
        self.spin_current.valueChanged.connect(self._on_current_changed)
        setpoint_grid.addWidget(self.spin_current, 1, 1)

        setpoint_grid.addWidget(QLabel("Power (W):"), 2, 0)
        self.spin_power = QDoubleSpinBox()
        self.spin_power.setRange(0, 4000)
        self.spin_power.setDecimals(2)
        self.spin_power.setValue(4000)
        self.spin_power.valueChanged.connect(self._on_power_changed)
        setpoint_grid.addWidget(self.spin_power, 2, 1)

        setpoint_grid.addWidget(QLabel("OVP (V):"), 3, 0)
        self.spin_ovp = QDoubleSpinBox()
        self.spin_ovp.setRange(0, 1200)
        self.spin_ovp.setDecimals(1)
        self.spin_ovp.setValue(1100)
        self.spin_ovp.valueChanged.connect(self._on_ovp_changed)
        setpoint_grid.addWidget(self.spin_ovp, 3, 1)

        setpoint_grid.addWidget(QLabel("Load (Ω):"), 4, 0)
        self.slider_load = QSlider(Qt.Orientation.Horizontal)
        self.slider_load.setRange(1, 1000)  # logarithmically mapped 1Ω to 10kΩ
        self.slider_load.setValue(self._resistance_to_slider(100))
        self.slider_load.valueChanged.connect(self._on_load_slider)
        self.lbl_load_value = QLabel("100 Ω")
        setpoint_grid.addWidget(self.slider_load, 4, 1)
        setpoint_grid.addWidget(self.lbl_load_value, 4, 2)

        left_layout.addWidget(setpoint_box)

        # Output and mode control
        control_box = QGroupBox("Manual Controls")
        control_grid = QGridLayout(control_box)

        self.btn_output_toggle = QPushButton("Output OFF")
        self.btn_output_toggle.clicked.connect(self._toggle_output)
        control_grid.addWidget(self.btn_output_toggle, 0, 0)

        self.btn_remote = QPushButton("Remote Mode")
        self.btn_remote.clicked.connect(lambda: self._set_remote(True))
        control_grid.addWidget(self.btn_remote, 0, 1)

        self.btn_local = QPushButton("Local Mode")
        self.btn_local.clicked.connect(lambda: self._set_remote(False))
        control_grid.addWidget(self.btn_local, 0, 2)

        self.btn_trigger_ovp = QPushButton("Trigger OVP")
        self.btn_trigger_ovp.setObjectName("danger")
        self.btn_trigger_ovp.clicked.connect(self._trigger_ovp)
        control_grid.addWidget(self.btn_trigger_ovp, 1, 0)

        self.btn_reset = QPushButton("Reset Device")
        self.btn_reset.clicked.connect(self._reset_device)
        control_grid.addWidget(self.btn_reset, 1, 1)

        left_layout.addWidget(control_box)

        # Status LEDs
        led_box = QGroupBox("Status")
        led_grid = QGridLayout(led_box)
        self.leds = {}
        led_names = [
            ("remote", "Remote Mode"),
            ("local", "Local Mode"),
            ("output", "Output ON"),
            ("ovp", "OVP Tripped"),
            ("curr_lim", "Current Limit"),
            ("pow_lim", "Power Limit"),
        ]
        for i, (key, desc) in enumerate(led_names):
            led = QLabel()
            led.setObjectName("led")
            led.setFixedSize(16, 16)
            label = QLabel(desc)
            self.leds[key] = led
            led_grid.addWidget(led, i // 2, (i % 2) * 2)
            led_grid.addWidget(label, i // 2, (i % 2) * 2 + 1)
        left_layout.addWidget(led_box)

        left_layout.addStretch()
        splitter.addWidget(left_widget)

        # Right panel: Measurements and log
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(10)

        meas_box = QGroupBox("Measured Values")
        meas_grid = QGridLayout(meas_box)

        meas_grid.addWidget(QLabel("Voltage (V)"), 0, 0, Qt.AlignmentFlag.AlignCenter)
        self.lcd_voltage = QLCDNumber()
        self.lcd_voltage.setDigitCount(8)
        self.lcd_voltage.setSegmentStyle(QLCDNumber.SegmentStyle.Flat)
        meas_grid.addWidget(self.lcd_voltage, 1, 0)

        meas_grid.addWidget(QLabel("Current (A)"), 0, 1, Qt.AlignmentFlag.AlignCenter)
        self.lcd_current = QLCDNumber()
        self.lcd_current.setDigitCount(8)
        self.lcd_current.setSegmentStyle(QLCDNumber.SegmentStyle.Flat)
        meas_grid.addWidget(self.lcd_current, 1, 1)

        meas_grid.addWidget(QLabel("Power (W)"), 0, 2, Qt.AlignmentFlag.AlignCenter)
        self.lcd_power = QLCDNumber()
        self.lcd_power.setDigitCount(8)
        self.lcd_power.setSegmentStyle(QLCDNumber.SegmentStyle.Flat)
        meas_grid.addWidget(self.lcd_power, 1, 2)

        right_layout.addWidget(meas_box)

        # Command log
        log_box = QGroupBox("Command Log")
        log_layout = QVBoxLayout(log_box)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.document().setMaximumBlockCount(1000)
        log_layout.addWidget(self.log_text)
        btn_clear_log = QPushButton("Clear Log")
        btn_clear_log.clicked.connect(self.log_text.clear)
        log_layout.addWidget(btn_clear_log)
        right_layout.addWidget(log_box, 1)

        splitter.addWidget(right_widget)
        splitter.setSizes([450, 450])

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Simulator ready")

        # Initial IP display
        self._update_ip_display()

    # ------------------------------------------------------------------
    # UI helper methods
    # ------------------------------------------------------------------
    def _resistance_to_slider(self, ohms):
        """Map resistance 1Ω..10kΩ to slider 1..1000 logarithmically."""
        min_ohm, max_ohm = 1.0, 10000.0
        ohms = max(min(ohms, max_ohm), min_ohm)
        slider_min, slider_max = 1, 1000
        log_ohm = math.log10(ohms)
        log_min = math.log10(min_ohm)
        log_max = math.log10(max_ohm)
        pos = int((log_ohm - log_min) / (log_max - log_min) * (slider_max - slider_min) + slider_min)
        return pos

    def _slider_to_resistance(self, slider_val):
        min_ohm, max_ohm = 1.0, 10000.0
        slider_min, slider_max = 1, 1000
        log_min = math.log10(min_ohm)
        log_max = math.log10(max_ohm)
        log_ohm = log_min + (slider_val - slider_min) / (slider_max - slider_min) * (log_max - log_min)
        return 10 ** log_ohm

    def _update_ip_display(self):
        try:
            hostname = socket.gethostname()
            ips = socket.gethostbyname_ex(hostname)[2]
            # Also include localhost
            all_ips = set(ips)
            all_ips.add("127.0.0.1")
            ip_str = "\n".join(sorted(all_ips))
            self.lbl_ips.setText(ip_str)
        except Exception as e:
            self.lbl_ips.setText(f"Could not determine IPs: {e}")

    def _refresh_display(self):
        """Update all display elements from shared state."""
        if self._updating_ui:
            return
        snapshot = self.state.get_all_snapshot()

        # Update spinboxes only if not focused (to avoid disturbing user typing)
        if not self.spin_voltage.hasFocus():
            self.spin_voltage.setValue(snapshot["voltage_setpoint"])
        if not self.spin_current.hasFocus():
            self.spin_current.setValue(snapshot["current_limit"])
        if not self.spin_power.hasFocus():
            self.spin_power.setValue(snapshot["power_limit"])
        if not self.spin_ovp.hasFocus():
            self.spin_ovp.setValue(snapshot["ovp_setting"])

        # Update load slider and label
        res = snapshot["load_resistance"]
        if not self.slider_load.isSliderDown():
            self.slider_load.setValue(self._resistance_to_slider(res))
        self.lbl_load_value.setText(f"{res:.1f} Ω")

        # Output button text
        if snapshot["output_on"]:
            self.btn_output_toggle.setText("Output ON")
            self.btn_output_toggle.setObjectName("danger")
        else:
            self.btn_output_toggle.setText("Output OFF")
            self.btn_output_toggle.setObjectName("success")
        # Re-style buttons (objectName changed may need re-polish)
        self.btn_output_toggle.style().unpolish(self.btn_output_toggle)
        self.btn_output_toggle.style().polish(self.btn_output_toggle)

        # Remote/Local buttons enable state
        self.btn_remote.setEnabled(not snapshot["remote_mode"])
        self.btn_local.setEnabled(not snapshot["local_mode"])

        # Update LEDs
        led_states = {
            "remote": snapshot["remote_mode"],
            "local": snapshot["local_mode"],
            "output": snapshot["output_on"],
            "ovp": snapshot["ovp_tripped"],
            "curr_lim": snapshot["current_limit_active"],
            "pow_lim": snapshot["power_limit_active"],
        }
        for key, led in self.leds.items():
            active = led_states.get(key, False)
            color = "#00ff00" if active else "#555555"
            led.setStyleSheet(f"background-color: {color}; border-radius: 8px;")

        # LCDs
        self.lcd_voltage.display(f"{snapshot['measured_voltage']:.2f}")
        self.lcd_current.display(f"{snapshot['measured_current']:.4f}")
        self.lcd_power.display(f"{snapshot['measured_power']:.2f}")

    # ------------------------------------------------------------------
    # Slot handlers for user interactions
    # ------------------------------------------------------------------
    def _on_voltage_changed(self, val):
        if not self._updating_ui:
            self.state.set_voltage(val)

    def _on_current_changed(self, val):
        if not self._updating_ui:
            self.state.set_current(val)

    def _on_power_changed(self, val):
        if not self._updating_ui:
            self.state.set_power(val)

    def _on_ovp_changed(self, val):
        if not self._updating_ui:
            self.state.set_ovp(val)

    def _on_load_slider(self, slider_val):
        if not self._updating_ui:
            res = self._slider_to_resistance(slider_val)
            self.state.set_load_resistance(res)
            self.lbl_load_value.setText(f"{res:.1f} Ω")

    def _toggle_output(self):
        current = self.state.get_output_on()
        self.state.set_output_on(not current)

    def _set_remote(self, remote):
        self.state.set_remote_mode(remote)

    def _trigger_ovp(self):
        self.state.trigger_ovp()
        self.status_bar.showMessage("OVP tripped!")

    def _reset_device(self):
        self.state.reset()
        self.status_bar.showMessage("Device reset to defaults")

    # ------------------------------------------------------------------
    # Server start/stop
    # ------------------------------------------------------------------
    def start_server(self):
        if self.server and self.server.isRunning():
            return
        port = self.port_spin.value()
        self.server = SimulatorServer(self.state, port)
        self.server.log_message.connect(self._on_log_message)
        self.server.client_connected.connect(self._on_client_connected)
        self.server.error.connect(self._on_server_error)
        self.server.start()
        self.lbl_server_status.setText("Server: Running")
        self.lbl_server_status.setStyleSheet("color: #2ea043; font-weight: bold;")
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.status_bar.showMessage(f"Server started on port {port}")

    def stop_server(self):
        if self.server and self.server.isRunning():
            self.server.stop_server()
            self.server = None
        self.lbl_server_status.setText("Server: Stopped")
        self.lbl_server_status.setStyleSheet("color: #c75450; font-weight: bold;")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status_bar.showMessage("Server stopped")

    def _on_log_message(self, msg):
        self.log_text.append(msg)

    def _on_client_connected(self, connected):
        if connected:
            self.status_bar.showMessage("Client connected")
        else:
            self.status_bar.showMessage("Client disconnected")

    def _on_server_error(self, err):
        QMessageBox.critical(self, "Server Error", err)
        self.stop_server()

    # ------------------------------------------------------------------
    # Close event
    # ------------------------------------------------------------------
    def closeEvent(self, event):
        self.stop_server()
        event.accept()


# =============================================================================
# ENTRY POINT
# =============================================================================
def main():
    app = QApplication(sys.argv)
    window = SimulatorWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()