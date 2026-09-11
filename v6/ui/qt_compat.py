"""
qt_compat.py — Centralized PyQt6 compatibility and headless mock bridge.
Provides seamless import of PyQt6 widgets when available, and provides
robust headless mocks when running in automated headless CI / test environments.
"""

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
        QDoubleSpinBox, QSpinBox, QPushButton, QToolButton, QCheckBox, QRadioButton,
        QButtonGroup, QProgressBar, QFrame, QSplitter, QScrollArea, QTabWidget,
        QMainWindow, QStatusBar, QMessageBox, QApplication, QStyle, QMenu,
        QSizePolicy, QGroupBox, QSlider, QDialog, QFileDialog, QComboBox,
        QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
        QListWidget, QDialogButtonBox, QAbstractItemView
    )
    from PyQt6.QtGui import (
        QKeySequence, QShortcut, QGuiApplication, QAction, QColor, QFont,
        QPalette, QIcon, QPainter, QPen, QBrush, QImage, QPixmap, QPdfWriter,
        QPageSize, QPageLayout
    )
    from PyQt6.QtCore import (
        Qt, QTimer, pyqtSignal, QObject, QThread, QPointF, QRectF, QSize
    )
    HAVE_PYQT6 = True

except ImportError:
    HAVE_PYQT6 = False

    class MockQtBase:
        def __init__(self, *args, **kwargs):
            self.clicked = self._make_sig()
            self.toggled = self._make_sig()
            self.valueChanged = self._make_sig()
            self.textChanged = self._make_sig()
            self.currentIndexChanged = self._make_sig()
            self.currentChanged = self._make_sig()
            self.timeout = self._make_sig()
            self.triggered = self._make_sig()
            self.activated = self._make_sig()
            self.stateChanged = self._make_sig()
            self.returnPressed = self._make_sig()

        def _make_sig(self):
            class _Sig:
                def connect(self, *a, **k): pass
                def emit(self, *a, **k): pass
                def disconnect(self, *a, **k): pass
            return _Sig()

        def __getattr__(self, name):
            if name in ("count", "length", "size"):
                return lambda *args, **kwargs: 0
            if name in ("takeAt", "itemAt", "widget"):
                return lambda *args, **kwargs: None
            if (name.endswith("Changed") or name.endswith("requested") or 
                name.endswith("clicked") or name.endswith("selected") or
                name.endswith("Pressed") or
                name in ("triggered", "activated", "clicked", "toggled", "stateChanged", "timeout", "returnPressed")):
                return self._make_sig()
            def _noop(*args, **kwargs):
                return self
            return _noop

        def count(self): return 0
        def takeAt(self, i): return None
        def itemAt(self, i): return None
        def value(self): return 0.0
        def text(self): return ""
        def isChecked(self): return False
        def currentText(self): return ""
        def currentIndex(self): return 0
        def width(self): return 800
        def height(self): return 600

    class QWidget(MockQtBase): pass
    class QVBoxLayout(MockQtBase): pass
    class QHBoxLayout(MockQtBase): pass
    class QGridLayout(MockQtBase): pass
    class QGroupBox(MockQtBase): pass
    class QLabel(MockQtBase): pass
    class QLineEdit(MockQtBase): pass
    class QComboBox(MockQtBase): pass
    class QDoubleSpinBox(MockQtBase): pass
    class QSpinBox(MockQtBase): pass
    class QPushButton(MockQtBase): pass
    class QToolButton(MockQtBase):
        class ToolButtonPopupMode:
            DelayedPopup = 0
            MenuButtonPopup = 1
            InstantPopup = 2
    class QCheckBox(MockQtBase): pass
    class QRadioButton(MockQtBase): pass
    class QButtonGroup(MockQtBase): pass
    class QProgressBar(MockQtBase): pass
    class QTabWidget(MockQtBase): pass
    class QMainWindow(MockQtBase): pass
    class QStatusBar(MockQtBase): pass
    class QMessageBox(MockQtBase): pass
    class QApplication(MockQtBase): pass
    class QMenu(MockQtBase): pass
    class QSlider(MockQtBase): pass
    class QTextEdit(MockQtBase): pass
    class QTableWidget(MockQtBase): pass
    class QTableWidgetItem(MockQtBase): pass
    class QHeaderView(MockQtBase):
        class ResizeMode:
            Stretch = 1
            Fixed = 2
            Interactive = 0
            ResizeToContents = 3
    class QDialog(MockQtBase): pass
    class QFileDialog(MockQtBase): pass
    class QListWidget(MockQtBase): pass
    class QDialogButtonBox(MockQtBase):
        class StandardButton:
            Ok = 1
            Cancel = 2
            Apply = 4
    class QAbstractItemView(MockQtBase): pass

    class QFrame(MockQtBase):
        class Shape:
            NoFrame = 0
            Box = 1
            Panel = 2
            StyledPanel = 6
            HLine = 4
            VLine = 5

    class QSplitter(MockQtBase): pass
    class QScrollArea(MockQtBase): pass

    class QSizePolicy:
        class Policy:
            Preferred = 0
            Expanding = 1
            Minimum = 2
            Maximum = 3
            Fixed = 4

    class QStyle:
        class StandardPixmap:
            SP_BrowserReload = 1
            SP_DialogSaveButton = 2
            SP_MediaPlay = 3
            SP_MediaStop = 4

    class Qt:
        class Orientation:
            Horizontal = 1
            Vertical = 2
        class AlignmentFlag:
            AlignCenter = 4
            AlignLeft = 1
            AlignRight = 2
            AlignVCenter = 8
            AlignTop = 16
            AlignBottom = 32
        class PenStyle:
            SolidLine = 1
            DashLine = 2
            DotLine = 3
        class CursorShape:
            PointingHandCursor = 13
            ArrowCursor = 0
            CrossCursor = 2
            WaitCursor = 3
        class CheckState:
            Unchecked = 0
            PartiallyChecked = 1
            Checked = 2
        class WindowType:
            Window = 1
        class Key:
            Key_E = 69
            Key_Space = 32

    class QKeySequence:
        def __init__(self, *args): pass

    class QShortcut(MockQtBase): pass
    class QGuiApplication(MockQtBase): pass
    class QAction(MockQtBase): pass
    class QColor(MockQtBase): pass
    class QFont(MockQtBase): pass
    class QPalette(MockQtBase): pass
    class QIcon(MockQtBase): pass
    class QPainter(MockQtBase): pass
    class QPen(MockQtBase): pass
    class QBrush(MockQtBase): pass
    class QImage(MockQtBase): pass
    class QPixmap(MockQtBase): pass
    class QPdfWriter(MockQtBase): pass
    class QPageSize(MockQtBase): pass
    class QPageLayout(MockQtBase): pass

    class QTimer(MockQtBase):
        def start(self, *args): pass
        def stop(self): pass

    def pyqtSignal(*args, **kwargs):
        class Sig:
            def connect(self, s): pass
            def emit(self, *a): pass
            def disconnect(self, *a): pass
        return Sig()

    class QObject(MockQtBase): pass
    class QThread(MockQtBase): pass
    class QPointF:
        def __init__(self, x=0.0, y=0.0):
            self.x, self.y = x, y
    class QRectF:
        def __init__(self, *args): pass
    class QSize:
        def __init__(self, w=0, h=0):
            self.w, self.h = w, h
