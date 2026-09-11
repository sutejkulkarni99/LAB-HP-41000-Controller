"""v6 Entry Point — Modular Multi-Instrument Laboratory Suite."""
import sys
import argparse

try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
except ImportError:
    QApplication = None

from v6.ui.main_window import MainWindow


def parse_args():
    parser = argparse.ArgumentParser(description="Lab Suite v6 — Modular Multi-Instrument Laboratory Suite")
    parser.add_argument("--psu-ip", default="127.0.0.1", help="Default PSU IP address")
    parser.add_argument("--psu-port", type=int, default=10001, help="Default PSU Port")
    parser.add_argument("--scope-ip", default="127.0.0.1", help="Default Scope IP address")
    parser.add_argument("--scope-port", type=int, default=5025, help="Default Scope Port")
    return parser.parse_args()


def main():
    args = parse_args()

    if QApplication is None:
        print("PyQt6 is not installed in this environment. Exiting UI startup.")
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

    if args.psu_ip and hasattr(window, "txt_psu_ip"):
        window.txt_psu_ip.setText(args.psu_ip)
    if args.psu_port and hasattr(window, "spin_psu_port"):
        window.spin_psu_port.setValue(args.psu_port)

    if args.scope_ip and hasattr(window, "txt_scope_ip"):
        window.txt_scope_ip.setText(args.scope_ip)
    if args.scope_port and hasattr(window, "spin_scope_port"):
        window.spin_scope_port.setValue(args.scope_port)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
