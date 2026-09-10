"""v6 Entry Point — Modular Multi-Instrument Laboratory Suite."""
import sys
import argparse
import threading
import time

try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
except ImportError:
    QApplication = None

from v6.ui.main_window import MainWindow
from v6.instruments.labhp_41000.simulator import LABHPSimulator
from v6.instruments.rtb2000.simulator import RTB2000Simulator


def parse_args():
    parser = argparse.ArgumentParser(description="Lab Suite v6 — Modular Multi-Instrument Laboratory Suite")
    parser.add_argument("--sim", action="store_true", help="Spin up background hardware simulators for testing")
    parser.add_argument("--psu-ip", default="127.0.0.1", help="Default PSU IP address")
    parser.add_argument("--psu-port", type=int, default=10001, help="Default PSU Port")
    parser.add_argument("--scope-ip", default="127.0.0.1", help="Default Scope IP address")
    parser.add_argument("--scope-port", type=int, default=5025, help="Default Scope Port")
    return parser.parse_args()


def main():
    args = parse_args()

    # If simulation mode requested, boot hardware simulators on localhost
    sim_psu = None
    sim_scope = None
    if args.sim:
        print("[v6 Runner] Booting ETPS LAB-HP 41000 ASCII Simulator on 127.0.0.1:10001...")
        sim_psu = LABHPSimulator("127.0.0.1", 10001)
        sim_psu.start()

        print("[v6 Runner] Booting Rohde & Schwarz RTB2000 SCPI Simulator on 127.0.0.1:5025...")
        sim_scope = RTB2000Simulator("127.0.0.1", 5025)
        sim_scope.start()

        time.sleep(0.3)

    if QApplication is None:
        print("PyQt6 is not installed in this environment. Simulators running. Exiting UI startup.")
        if sim_psu: sim_psu.stop()
        if sim_scope: sim_scope.stop()
        return

    # Enable High DPI scaling
    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("Lab Suite v6")
    app.setOrganizationName("Laboratory Instrumentation")

    window = MainWindow()
    if args.psu_ip:
        window.combo_psu_ip.setCurrentText(args.psu_ip)
    if args.scope_ip:
        window.combo_scope_ip.setCurrentText(args.scope_ip)

    window.show()

    exit_code = app.exec()

    if sim_psu:
        sim_psu.stop()
    if sim_scope:
        sim_scope.stop()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
