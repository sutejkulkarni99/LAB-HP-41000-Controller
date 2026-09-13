import os
import sys
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonType
from PySide6.QtCore import QUrl
from pathlib import Path

try:
    from v7.instruments import (
        LabhpDriver,
        Rtb2000Driver,
        KeysightEdu33212ADriver,
        TektronixMso2004BDriver
    )
    from v7.clock import SessionClock
    from v7.session import LoggingSession
    from v7.bridge import (
        InstrumentsBridge,
        SessionBridge,
        ArchiveBridge,
        ThemeBridge
    )
except ImportError:
    from instruments import (
        LabhpDriver,
        Rtb2000Driver,
        KeysightEdu33212ADriver,
        TektronixMso2004BDriver
    )
    from clock import SessionClock
    from session import LoggingSession
    from bridge import (
        InstrumentsBridge,
        SessionBridge,
        ArchiveBridge,
        ThemeBridge
    )

instruments_bridge = None
session_bridge = None
archive_bridge = None
theme_bridge = None

def main():
    global instruments_bridge, session_bridge, archive_bridge, theme_bridge
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

    qml_dir = Path(__file__).parent / "qml"
    qmlRegisterSingletonType(
        QUrl.fromLocalFile(str(qml_dir / "Theme.qml")),
        "v7.qml", 1, 0, "Theme"
    )

    # QML Engine setup
    engine = QQmlApplicationEngine()

    root_context = engine.rootContext()
    root_context.setContextProperty("instrumentsBridge", instruments_bridge)
    root_context.setContextProperty("sessionBridge", session_bridge)
    root_context.setContextProperty("archiveBridge", archive_bridge)
    root_context.setContextProperty("themeBridge", theme_bridge)

    engine.addImportPath(str(qml_dir))
    engine.addImportPath(str(qml_dir / "components"))

    engine.load(QUrl.fromLocalFile(str(qml_dir / "Main.qml")))

    if not engine.rootObjects():
        sys.exit(-1)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
