import os
import sys
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QUrl

from .instruments import (
    LabhpDriver,
    Rtb2000Driver,
    KeysightEdu33212ADriver,
    TektronixMso2004BDriver
)
from .clock import SessionClock
from .session import LoggingSession
from .bridge import (
    InstrumentsBridge,
    SessionBridge,
    ArchiveBridge,
    ThemeBridge
)

def main():
    app = QGuiApplication(sys.argv)
    app.setOrganizationName("LabOrchestrator")
    app.setApplicationName("LabBenchOrchestratorV7")

    # Instantiate hardware drivers
    instruments = {
        "labhp_41000": LabhpDriver(),
        "rtb2000": Rtb2000Driver(),
        "fg_edu33212a": KeysightEdu33212ADriver(),
        "mso2004b": TektronixMso2004BDriver()
    }

    # Core synchronization and logging
    clock = SessionClock()
    session = LoggingSession(clock)

    # Exposed bridges
    instruments_bridge = InstrumentsBridge(instruments)
    session_bridge = SessionBridge(session, clock, instruments)
    archive_bridge = ArchiveBridge()
    theme_bridge = ThemeBridge()

    # QML Engine setup
    engine = QQmlApplicationEngine()

    root_context = engine.rootContext()
    root_context.setContextProperty("instrumentsBridge", instruments_bridge)
    root_context.setContextProperty("sessionBridge", session_bridge)
    root_context.setContextProperty("archiveBridge", archive_bridge)
    root_context.setContextProperty("themeBridge", theme_bridge)

    qml_dir = os.path.join(os.path.dirname(__file__), "qml")
    engine.addImportPath(qml_dir)
    engine.addImportPath(os.path.join(qml_dir, "components"))

    main_qml = os.path.join(qml_dir, "Main.qml")
    engine.load(QUrl.fromLocalFile(main_qml))

    if not engine.rootObjects():
        sys.exit(-1)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
