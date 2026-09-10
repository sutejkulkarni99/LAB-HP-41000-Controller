"""MainWindow — Primary unified interface for Modular Multi-Instrument Laboratory Suite v6."""
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from PyQt6.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
        QComboBox, QSpinBox, QPushButton, QToolButton, QTabWidget,
        QStatusBar, QFrame, QMessageBox, QApplication, QStyle
    )
    from PyQt6.QtGui import QKeySequence, QShortcut
    from PyQt6.QtCore import Qt, QTimer
except ImportError:
    class QMainWindow:
        def __init__(self, parent=None): pass
    class QWidget:
        def __init__(self, parent=None): pass
    class QVBoxLayout:
        def __init__(self, parent=None): pass
    class QHBoxLayout:
        def __init__(self, parent=None): pass
    class QLabel:
        def __init__(self, text=""): pass
    class QComboBox:
        def __init__(self, parent=None): pass
    class QSpinBox:
        def __init__(self, parent=None): pass
    class QPushButton:
        def __init__(self, text=""): pass
    class QToolButton:
        def __init__(self, parent=None): pass
    class QTabWidget:
        def __init__(self, parent=None): pass
    class QStatusBar:
        def __init__(self, parent=None): pass
    class QFrame:
        def __init__(self, parent=None): pass

from .styles.dark import MODERN_DARK_STYLESHEET
from .styles.light import MODERN_LIGHT_STYLESHEET
from .widgets.estop_button import EStopButton
from .widgets.connection_chip import ConnectionChip
from .tabs.psu_tab import PSUTab
from .tabs.scope_tab import ScopeTab
from .tabs.session_tab import SessionTab
from .tabs.plots_tab import PlotsTab
from .tabs.soa_tab import SOATab
from .tabs.terminal_tab import TerminalTab

from ..core.session_clock import SessionClock
from ..core.session import LoggingSession
from ..instruments.labhp_41000.instrument import LABHPInstrument
from ..instruments.rtb2000.instrument import RTB2000Instrument
from ..workers.telemetry_worker import TelemetryWorker
from ..workers.scope_worker import ScopeWorker
from ..workers.scanner_worker import ScannerWorker


class MainWindow(QMainWindow):
    """
    Primary Application Window uniting ETPS LAB-HP 41000 power supply and
    Rohde & Schwarz RTB2000 oscilloscope under a shared session clock.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lab Suite v6 — Modular Multi-Instrument Laboratory Suite")
        self.resize(1340, 880)

        self.is_dark_mode = True
        self.is_local_mode = False

        # Core Clock & Instruments
        self.session_clock = SessionClock()
        self.psu_instrument = LABHPInstrument()
        self.scope_instrument = RTB2000Instrument()

        # Background Workers
        self.telemetry_worker: Optional[TelemetryWorker] = None
        self.scope_worker: Optional[ScopeWorker] = None
        self.session: Optional[LoggingSession] = None
        self.scanner_worker: Optional[ScannerWorker] = None

        # Build UI Architecture
        self._build_ui()
        self.setStyleSheet(MODERN_DARK_STYLESHEET)

        # Wire Signals
        self._wire_signals()

        # Global Keyboard Shortcuts
        self._setup_shortcuts()

        # Periodic UI update timer (10 Hz for clock & status)
        self.ui_timer = QTimer(self)
        self.ui_timer.timeout.connect(self._on_ui_tick)
        self.ui_timer.start(100)

    # -------------------------------------------------------------------------
    # UI CONSTRUCTION
    # -------------------------------------------------------------------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(12, 10, 12, 10)
        root_layout.setSpacing(10)

        # 1. Header Bar
        root_layout.addWidget(self._build_header_bar())

        # 2. Main Workspace Tabs
        self.tabs = QTabWidget()
        root_layout.addWidget(self.tabs, 1)

        self.tab_psu = PSUTab(self)
        self.tab_scope = ScopeTab(self)
        self.tab_session = SessionTab(self)
        self.tab_plots = PlotsTab(self)
        self.tab_soa = SOATab(self)
        self.tab_terminal = TerminalTab(self)

        self.tabs.addTab(self.tab_psu, "  ⚡ Benchtop PSU (LAB-HP)  ")
        self.tabs.addTab(self.tab_scope, "  🌊 Oscilloscope (RTB2000)  ")
        self.tabs.addTab(self.tab_session, "  🗂 Unified Session  ")
        self.tabs.addTab(self.tab_plots, "  📈 Multi-Trace Plots  ")
        self.tabs.addTab(self.tab_soa, "  🛡 Safe Operating Area (SOA)  ")
        self.tabs.addTab(self.tab_terminal, "  💻 SCPI / ASCII Terminal  ")

        # 3. Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Select instruments and click Connect.")

    def _build_header_bar(self) -> QWidget:
        header_card = QFrame()
        header_card.setObjectName("header_card")
        header_card.setStyleSheet("""
            QFrame#header_card {
                background-color: #16181D;
                border: 1px solid #272A31;
                border-radius: 8px;
            }
        """)
        h_layout = QHBoxLayout(header_card)
        h_layout.setContentsMargins(14, 8, 14, 8)
        h_layout.setSpacing(12)

        # Title & Subtitle Left
        title_box = QVBoxLayout()
        lbl_title = QLabel("LAB SUITE v6")
        lbl_title.setStyleSheet("font-size: 13pt; font-weight: 800; color: #38BDF8; letter-spacing: 0.5px;")
        lbl_sub = QLabel("ETPS LAB-HP 41000  •  R&S RTB2000 Scope")
        lbl_sub.setStyleSheet("font-size: 8pt; color: #94A3B8;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        h_layout.addLayout(title_box)

        h_layout.addSpacing(10)

        # PSU Connection Section
        psu_conn_box = QHBoxLayout()
        psu_conn_box.addWidget(QLabel("PSU IP:"))
        self.combo_psu_ip = QComboBox()
        self.combo_psu_ip.setEditable(True)
        self.combo_psu_ip.addItem("127.0.0.1")
        self.combo_psu_ip.addItem("192.168.1.100")
        self.combo_psu_ip.setMinimumWidth(115)
        psu_conn_box.addWidget(self.combo_psu_ip)

        self.btn_scan = QToolButton()
        if hasattr(QStyle.StandardPixmap, "SP_BrowserReload"):
            self.btn_scan.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.btn_scan.setToolTip("Auto-Scan Local Subnet for LAN Instruments")
        self.btn_scan.clicked.connect(self._start_network_scan)
        psu_conn_box.addWidget(self.btn_scan)

        self.btn_connect_psu = QPushButton("PSU CONNECT")
        self.btn_connect_psu.setObjectName("primary")
        self.btn_connect_psu.clicked.connect(self._toggle_psu_connection)
        psu_conn_box.addWidget(self.btn_connect_psu)
        h_layout.addLayout(psu_conn_box)

        # Scope Connection Section
        scope_conn_box = QHBoxLayout()
        scope_conn_box.addWidget(QLabel("Scope IP:"))
        self.combo_scope_ip = QComboBox()
        self.combo_scope_ip.setEditable(True)
        self.combo_scope_ip.addItem("127.0.0.1")
        self.combo_scope_ip.addItem("192.168.1.101")
        self.combo_scope_ip.setMinimumWidth(115)
        scope_conn_box.addWidget(self.combo_scope_ip)

        self.btn_connect_scope = QPushButton("SCOPE CONNECT")
        self.btn_connect_scope.setObjectName("primary")
        self.btn_connect_scope.clicked.connect(self._toggle_scope_connection)
        scope_conn_box.addWidget(self.btn_connect_scope)
        h_layout.addLayout(scope_conn_box)

        h_layout.addStretch()

        # Local/Remote Mode Switch
        mode_box = QVBoxLayout()
        mode_box.setSpacing(2)
        lbl_mode_caption = QLabel("BUS CONTROL MODE")
        lbl_mode_caption.setStyleSheet("font-size: 7.5pt; font-weight: 700; color: #64748B; letter-spacing: 0.5px;")
        lbl_mode_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mode_box.addWidget(lbl_mode_caption)

        self.btn_mode_toggle = QPushButton("⚡ REMOTE MODE")
        self.btn_mode_toggle.setObjectName("mode_remote")
        self.btn_mode_toggle.setToolTip("Toggle between REMOTE (computer control) and LOCAL (front-panel control).")
        self.btn_mode_toggle.clicked.connect(self._toggle_local_remote)
        self.btn_mode_toggle.setEnabled(False)
        mode_box.addWidget(self.btn_mode_toggle)
        h_layout.addLayout(mode_box)

        h_layout.addSpacing(6)

        # Global Theme Toggle (Dark/Light)
        theme_box = QVBoxLayout()
        theme_box.setSpacing(2)
        lbl_theme_caption = QLabel("DISPLAY THEME")
        lbl_theme_caption.setStyleSheet("font-size: 7.5pt; font-weight: 700; color: #64748B; letter-spacing: 0.5px;")
        lbl_theme_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        theme_box.addWidget(lbl_theme_caption)

        self.btn_theme_toggle = QPushButton("☀️ LIGHT MODE")
        self.btn_theme_toggle.clicked.connect(self._toggle_theme)
        theme_box.addWidget(self.btn_theme_toggle)
        h_layout.addLayout(theme_box)

        h_layout.addSpacing(10)

        # Industrial Latching Emergency Stop Button (Inherited from v5)
        estop_box = QVBoxLayout()
        estop_box.setSpacing(2)
        lbl_estop_caption = QLabel("EMERGENCY STOP")
        lbl_estop_caption.setStyleSheet("font-size: 7.5pt; font-weight: 800; color: #EF4444; letter-spacing: 0.5px;")
        lbl_estop_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        estop_box.addWidget(lbl_estop_caption)

        self.btn_estop = EStopButton(self)
        self.btn_estop.emergency_stopped.connect(self._handle_emergency_stop)
        self.btn_estop.emergency_cleared.connect(self._handle_emergency_cleared)
        estop_box.addWidget(self.btn_estop)
        h_layout.addLayout(estop_box)

        return header_card

    # -------------------------------------------------------------------------
    # KEYBOARD SHORTCUTS & WIRING
    # -------------------------------------------------------------------------
    def _setup_shortcuts(self):
        self.shortcut_estop = QShortcut(QKeySequence("Ctrl+E"), self)
        self.shortcut_estop.activated.connect(self.btn_estop.click)

        self.shortcut_output = QShortcut(QKeySequence("Ctrl+O"), self)
        self.shortcut_output.activated.connect(self._toggle_output_shortcut)

    def _wire_signals(self):
        # PSU Tab Signals
        self.tab_psu.set_voltage_requested.connect(self._on_psu_set_voltage)
        self.tab_psu.set_current_requested.connect(self._on_psu_set_current)
        self.tab_psu.set_power_requested.connect(self._on_psu_set_power)
        self.tab_psu.set_ovp_requested.connect(self._on_psu_set_ovp)
        self.tab_psu.output_state_requested.connect(self._on_psu_set_output)
        self.tab_psu.operating_mode_requested.connect(self._on_psu_set_mode)

        # Scope Tab Signals
        self.tab_scope.timebase_scale_requested.connect(self._on_scope_timebase_scale)
        self.tab_scope.channel_scale_requested.connect(self._on_scope_channel_scale)
        self.tab_scope.channel_state_requested.connect(self._on_scope_channel_state)
        self.tab_scope.trigger_level_requested.connect(self._on_scope_trigger_level)
        self.tab_scope.trigger_source_requested.connect(self._on_scope_trigger_source)
        self.tab_scope.run_requested.connect(self._on_scope_run)
        self.tab_scope.stop_requested.connect(self._on_scope_stop)
        self.tab_scope.single_capture_requested.connect(self._on_scope_single)
        self.tab_scope.autoscale_requested.connect(self._on_scope_autoscale)

        # Session Tab Signals
        self.tab_session.session_start_requested.connect(self._on_session_start)
        self.tab_session.session_pause_requested.connect(self._on_session_pause)
        self.tab_session.session_stop_requested.connect(self._on_session_stop)

        # Terminal Tab Signals
        self.tab_terminal.command_send_requested.connect(self._on_terminal_send_command)

    # -------------------------------------------------------------------------
    # PSU CONNECTION & TELEMETRY
    # -------------------------------------------------------------------------
    def _toggle_psu_connection(self):
        if self.psu_instrument.connected:
            self._disconnect_psu()
        else:
            self._connect_psu()

    def _connect_psu(self):
        ip = self.combo_psu_ip.currentText().strip()
        port = 10001
        self.status_bar.showMessage(f"Connecting to LAB-HP 41000 @ {ip}:{port}...")
        QApplication.processEvents()

        try:
            self.psu_instrument.connect(ip, port)
            self.btn_connect_psu.setText("PSU DISCONNECT")
            self.btn_connect_psu.setObjectName("danger")
            self.btn_connect_psu.setStyleSheet("")
            self.btn_mode_toggle.setEnabled(True)
            self.tab_psu.set_connected(True)

            # Start Telemetry Worker
            self.telemetry_worker = TelemetryWorker(self.psu_instrument.driver, interval_s=0.1)
            self.telemetry_worker.telemetry_received.connect(self._on_psu_telemetry_received)
            self.telemetry_worker.output_state_received.connect(self.tab_psu.update_output_state)
            self.telemetry_worker.status_received.connect(self.tab_psu.update_status_badges)
            self.telemetry_worker.connection_lost.connect(self._on_psu_connection_lost)
            self.telemetry_worker.start()

            self.status_bar.showMessage(f"Connected to LAB-HP 41000 ({ip}:{port})")
            self.tab_session.update_instrument_stats(0, "Connected", 0)
        except Exception as e:
            self.psu_instrument.disconnect()
            QMessageBox.critical(self, "PSU Connection Failed", f"Could not connect to LAB-HP:\n{e}")
            self.status_bar.showMessage("PSU Connection failed.")

    def _disconnect_psu(self):
        if self.telemetry_worker:
            self.telemetry_worker.stop()
            self.telemetry_worker = None

        self.psu_instrument.disconnect()
        self.btn_connect_psu.setText("PSU CONNECT")
        self.btn_connect_psu.setObjectName("primary")
        self.btn_connect_psu.setStyleSheet("")
        self.btn_mode_toggle.setEnabled(False)
        self.tab_psu.set_connected(False)
        self.status_bar.showMessage("PSU Disconnected.")
        self.tab_session.update_instrument_stats(0, "Disconnected", 0)

    def _on_psu_connection_lost(self, msg: str):
        self._disconnect_psu()
        QMessageBox.warning(self, "PSU Connection Lost", f"Lost connection to LAB-HP 41000:\n{msg}")

    def _on_psu_telemetry_received(self, t_sec: float, v: float, i: float, p: float, r: float):
        self.tab_psu.update_telemetry(t_sec, v, i, p, r)
        self.tab_soa.update_point(v, i, p)

        # Sync to multi-trace plots
        scope_metrics = {}
        if self.scope_worker:
            scope_metrics = self.scope_worker.last_telemetry
        self.tab_plots.append_data(t_sec, {"voltage": v, "current": i, "power": p}, scope_metrics)

    # -------------------------------------------------------------------------
    # SCOPE CONNECTION & WORKER
    # -------------------------------------------------------------------------
    def _toggle_scope_connection(self):
        if self.scope_instrument.connected:
            self._disconnect_scope()
        else:
            self._connect_scope()

    def _connect_scope(self):
        ip = self.combo_scope_ip.currentText().strip()
        port = 5025
        self.status_bar.showMessage(f"Connecting to R&S RTB2000 @ {ip}:{port}...")
        QApplication.processEvents()

        try:
            self.scope_instrument.connect(ip, port)
            self.btn_connect_scope.setText("SCOPE DISCONNECT")
            self.btn_connect_scope.setObjectName("danger")
            self.btn_connect_scope.setStyleSheet("")

            # Start Scope Worker
            self.scope_worker = ScopeWorker(self.scope_instrument, capture_interval_s=0.2)
            self.scope_worker.waveform_captured.connect(self._on_scope_waveform_received)
            self.scope_worker.telemetry_received.connect(self._on_scope_telemetry_received)
            self.scope_worker.status_verified.connect(self.tab_scope.set_verified_settings)
            self.scope_worker.start()

            self.status_bar.showMessage(f"Connected to R&S RTB2000 ({ip}:{port})")
            self.tab_session.update_instrument_stats(1, "Connected", 0)
        except Exception as e:
            self.scope_instrument.disconnect()
            QMessageBox.critical(self, "Scope Connection Failed", f"Could not connect to RTB2000:\n{e}")
            self.status_bar.showMessage("Scope Connection failed.")

    def _disconnect_scope(self):
        if self.scope_worker:
            self.scope_worker.stop()
            self.scope_worker = None

        self.scope_instrument.disconnect()
        self.btn_connect_scope.setText("SCOPE CONNECT")
        self.btn_connect_scope.setObjectName("primary")
        self.btn_connect_scope.setStyleSheet("")
        self.status_bar.showMessage("Scope Disconnected.")
        self.tab_session.update_instrument_stats(1, "Disconnected", 0)

    def _on_scope_waveform_received(self, wf_dict: Dict[str, Any]):
        self.tab_scope.update_waveform_display(wf_dict)

        if self.session and self.session.is_running:
            scope_logger = self.session.loggers.get("rtb2000")
            if scope_logger:
                session_t = self.session_clock.now()
                scope_logger.queue_waveform(session_t, "rtb2000", "CH1,CH2", "")

    def _on_scope_telemetry_received(self, telem: Dict[str, Any]):
        self.tab_scope.update_measurements(telem)

    # -------------------------------------------------------------------------
    # PSU ACTIONS
    # -------------------------------------------------------------------------
    def _on_psu_set_voltage(self, v: float):
        if self.psu_instrument.connected:
            self.psu_instrument.driver.set_voltage(v)
            self.status_bar.showMessage(f"Voltage set to {v:.2f} V")

    def _on_psu_set_current(self, i: float):
        if self.psu_instrument.connected:
            self.psu_instrument.driver.set_current(i)
            self.status_bar.showMessage(f"Current limit set to {i:.4f} A")

    def _on_psu_set_power(self, p: float):
        if self.psu_instrument.connected:
            self.psu_instrument.driver.set_power(p)
            self.status_bar.showMessage(f"Power limit set to {p:.1f} W")

    def _on_psu_set_ovp(self, ovp: float):
        if self.psu_instrument.connected:
            self.psu_instrument.driver.set_ovp(ovp)
            self.status_bar.showMessage(f"OVP limit set to {ovp:.1f} V")

    def _on_psu_set_output(self, state: bool):
        if self.psu_instrument.connected:
            self.psu_instrument.driver.set_output(state)
            self.status_bar.showMessage(f"PSU Output set to {'ON' if state else 'OFF'}")

    def _on_psu_set_mode(self, mode: str):
        if self.psu_instrument.connected:
            self.psu_instrument.driver.set_operating_mode(mode)
            self.status_bar.showMessage(f"Operating mode set to {mode}")

    def _toggle_output_shortcut(self):
        if self.psu_instrument.connected and not self.is_local_mode:
            new_st = not self.psu_instrument.driver.output_state
            self._on_psu_set_output(new_st)

    def _toggle_local_remote(self):
        if not self.psu_instrument.connected:
            return
        new_local = not self.is_local_mode
        self.is_local_mode = new_local
        if new_local:
            self.psu_instrument.driver.set_local()
            self.btn_mode_toggle.setText("🔒 LOCAL (PANEL)")
            self.btn_mode_toggle.setObjectName("mode_local")
            self.status_bar.showMessage("Switched to LOCAL MODE: Front panel physical controls active.")
        else:
            self.psu_instrument.driver.set_remote()
            self.btn_mode_toggle.setText("⚡ REMOTE MODE")
            self.btn_mode_toggle.setObjectName("mode_remote")
            self.status_bar.showMessage("Switched to REMOTE MODE: Software controls active.")
        self.tab_psu.set_local_mode(new_local)
        self.btn_mode_toggle.style().unpolish(self.btn_mode_toggle)
        self.btn_mode_toggle.style().polish(self.btn_mode_toggle)

    # -------------------------------------------------------------------------
    # SCOPE ACTIONS
    # -------------------------------------------------------------------------
    def _on_scope_timebase_scale(self, s: float):
        if self.scope_worker:
            self.scope_worker.queue_command(lambda d: d.set_timebase_scale(s))

    def _on_scope_channel_scale(self, ch: int, v_div: float):
        if self.scope_worker:
            self.scope_worker.queue_command(lambda d: d.set_channel_scale(ch, v_div))

    def _on_scope_channel_state(self, ch: int, en: bool):
        if self.scope_worker:
            self.scope_worker.queue_command(lambda d: d.set_channel_state(ch, en))

    def _on_scope_trigger_level(self, lev: float):
        if self.scope_worker:
            self.scope_worker.queue_command(lambda d: d.set_trigger_level(lev))

    def _on_scope_trigger_source(self, src: str):
        if self.scope_worker:
            self.scope_worker.queue_command(lambda d: d.set_trigger_source(src))

    def _on_scope_run(self):
        if self.scope_worker:
            self.scope_worker.queue_command(lambda d: d.run())

    def _on_scope_stop(self):
        if self.scope_worker:
            self.scope_worker.queue_command(lambda d: d.stop())

    def _on_scope_single(self):
        if self.scope_worker:
            self.scope_worker.queue_command(lambda d: d.single())

    def _on_scope_autoscale(self):
        if self.scope_worker:
            self.scope_worker.queue_command(lambda d: d.autoscale())

    # -------------------------------------------------------------------------
    # SESSION & LOGGING COORDINATOR
    # -------------------------------------------------------------------------
    def _on_session_start(self, meta: dict):
        base_dir = meta.get("session_dir", str(Path.cwd() / "sessions"))
        ts_dir = Path(base_dir) / f"session_{time.strftime('%Y%m%d_%H%M%S')}"
        ts_dir.mkdir(parents=True, exist_ok=True)

        self.session = LoggingSession(clock=self.session_clock)
        self.session.set_metadata(meta)
        self.session.stopped.connect(self._on_session_stopped_with_paths)

        # Pass instruments with intervals in seconds (PSU: 0.1s, Scope: 0.2s)
        inst_with_intervals = [
            (self.psu_instrument, 0.1),
            (self.scope_instrument, 0.2)
        ]
        self.session.start(str(ts_dir), inst_with_intervals)
        self.status_bar.showMessage(f"Recording session to: {ts_dir}")

    def _on_session_pause(self):
        if self.session and self.session.is_running:
            if self.session.is_paused:
                self.session.resume()
                self.status_bar.showMessage("Session Resumed.")
            else:
                self.session.pause()
                self.status_bar.showMessage("Session Paused.")

    def _on_session_stop(self):
        if self.session and self.session.is_running:
            self.session.stop()

    def _on_session_stopped_with_paths(self, session_dir: str, final_csv_paths: dict):
        self.status_bar.showMessage(f"Session Closed & Manifest Sealed at {session_dir}")
        # Autoload session data into Plots tab
        if not final_csv_paths:
            return
        psu_csv = final_csv_paths.get("labhp_41000")
        scope_csv = final_csv_paths.get("rtb2000")
        try:
            import csv
            psu_pts = {}
            if psu_csv and Path(psu_csv).exists():
                with open(psu_csv, "r", encoding="utf-8") as f:
                    r = csv.DictReader(f)
                    for row in r:
                        try:
                            t = float(row.get("elapsed_s", 0.0))
                            psu_pts[t] = {
                                "voltage": float(row.get("voltage_v", row.get("voltage", 0.0))),
                                "current": float(row.get("current_a", row.get("current", 0.0))),
                                "power": float(row.get("power_w", row.get("power", 0.0)))
                            }
                        except Exception:
                            pass

            scope_pts = {}
            if scope_csv and Path(scope_csv).exists():
                with open(scope_csv, "r", encoding="utf-8") as f:
                    r = csv.DictReader(f)
                    for row in r:
                        try:
                            t = float(row.get("elapsed_s", 0.0))
                            scope_pts[t] = {
                                "ch1_vrms": float(row.get("ch1_vrms", 0.0)),
                                "ch2_vrms": float(row.get("ch2_vrms", 0.0))
                            }
                        except Exception:
                            pass

            all_times = sorted(set(list(psu_pts.keys()) + list(scope_pts.keys())))
            for t in all_times:
                pv = psu_pts.get(t, {})
                sv = scope_pts.get(t, {})
                self.tab_plots.append_data(t, pv, sv)
            if all_times and hasattr(self.tab_plots, "_autorange"):
                self.tab_plots._autorange()
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # EMERGENCY STOP
    # -------------------------------------------------------------------------
    def _handle_emergency_stop(self):
        # 1. Immediately kill PSU output
        if self.psu_instrument.connected:
            try:
                self.psu_instrument.driver.set_output(False)
                self.psu_instrument.driver.set_voltage(0.0)
                self.psu_instrument.driver.set_current(0.0)
            except Exception:
                pass

        # 2. Freeze Oscilloscope acquisition
        if self.scope_worker:
            self.scope_worker.queue_command(lambda d: d.stop())

        self.tab_psu.update_output_state(False)
        self.status_bar.showMessage("⚠️ EMERGENCY STOP TRIPPED: All outputs forced to 0V / Standby.")

    def _handle_emergency_cleared(self):
        self.status_bar.showMessage("E-Stop Released. Normal operations may resume.")

    # -------------------------------------------------------------------------
    # TERMINAL COMMANDS
    # -------------------------------------------------------------------------
    def _on_terminal_send_command(self, target_id: str, cmd_str: str):
        try:
            if target_id == "rtb2000":
                if not self.scope_instrument.connected:
                    self.tab_terminal.log_response(target_id, "Scope not connected", is_error=True)
                    return
                resp = self.scope_instrument.driver.send_scpi(cmd_str)
                self.tab_terminal.log_response(target_id, resp if resp else "[OK/Acknowledged]")
            else:
                if not self.psu_instrument.connected:
                    self.tab_terminal.log_response(target_id, "PSU not connected", is_error=True)
                    return
                resp = self.psu_instrument.driver.send_cmd(cmd_str)
                self.tab_terminal.log_response(target_id, resp if resp else "[OK/Acknowledged]")
        except Exception as e:
            self.tab_terminal.log_response(target_id, str(e), is_error=True)

    # -------------------------------------------------------------------------
    # NETWORK SCANNER
    # -------------------------------------------------------------------------
    def _start_network_scan(self):
        self.btn_scan.setEnabled(False)
        self.status_bar.showMessage("Scanning local subnet for instruments...")

        self.scanner_worker = ScannerWorker("192.168.1.1/24", [10001, 5025])
        self.scanner_worker.device_discovered.connect(self._on_device_discovered)
        self.scanner_worker.scan_completed.connect(self._on_scan_completed)
        self.scanner_worker.start()

    def _on_device_discovered(self, ip: str, port: int, idn: str):
        self.status_bar.showMessage(f"Discovered: {idn} @ {ip}:{port}")
        if port == 10001 or "LAB-HP" in idn:
            if self.combo_psu_ip.findText(ip) == -1:
                self.combo_psu_ip.addItem(ip)
                self.combo_psu_ip.setCurrentText(ip)
        elif port == 5025 or "RTB" in idn:
            if self.combo_scope_ip.findText(ip) == -1:
                self.combo_scope_ip.addItem(ip)
                self.combo_scope_ip.setCurrentText(ip)

    def _on_scan_completed(self, found: list):
        self.btn_scan.setEnabled(True)
        self.status_bar.showMessage(f"Scan complete. Found {len(found)} devices.")

    # -------------------------------------------------------------------------
    # THEME TOGGLE
    # -------------------------------------------------------------------------
    def _toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        if self.is_dark_mode:
            self.setStyleSheet(MODERN_DARK_STYLESHEET)
            self.btn_theme_toggle.setText("☀️ LIGHT MODE")
        else:
            self.setStyleSheet(MODERN_LIGHT_STYLESHEET)
            self.btn_theme_toggle.setText("🌙 DARK MODE")

        self.tab_psu.set_theme(self.is_dark_mode)
        self.tab_scope.set_theme(self.is_dark_mode)
        self.tab_plots.set_theme(self.is_dark_mode)
        self.tab_soa.set_theme(self.is_dark_mode)

    # -------------------------------------------------------------------------
    # TICK TIMER
    # -------------------------------------------------------------------------
    def _on_ui_tick(self):
        # Update clock
        clk_str = self.session_clock.formatted_time()
        self.tab_session.update_clock(clk_str)

        # Update logger stats if active
        if self.session and self.session.is_running:
            psu_logger = self.session.loggers.get("labhp_41000")
            scope_logger = self.session.loggers.get("rtb2000")
            psu_pts = psu_logger.row_count if psu_logger else 0
            scope_pts = scope_logger.row_count if scope_logger else 0
            self.tab_session.update_instrument_stats(0, "Logging", psu_pts)
            self.tab_session.update_instrument_stats(1, "Logging", scope_pts)

    def closeEvent(self, event):
        # Graceful cleanup
        if self.session and self.session.is_running:
            self.session.stop()
        if self.telemetry_worker:
            self.telemetry_worker.stop()
        if self.scope_worker:
            self.scope_worker.stop()
        if self.psu_instrument.connected:
            self.psu_instrument.disconnect()
        if self.scope_instrument.connected:
            self.scope_instrument.disconnect()
        event.accept()
