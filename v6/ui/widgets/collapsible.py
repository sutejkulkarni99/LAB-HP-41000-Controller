"""CollapsibleSection — Clean progressive disclosure accordion widget for UI panels."""
from ..qt_compat import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSizePolicy, Qt, pyqtSignal


class CollapsibleSection(QWidget):
    """
    Collapsible container with a clickable header bar showing [▸/▾] [Title] [Status].
    Provides progressive disclosure without animation for robust, instant toggling.
    """

    toggled = pyqtSignal(bool)

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("collapsible_section")
        self._expanded = False
        self._title_text = title
        self._status_text = ""
        self._content_widget: QWidget = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header Bar
        self.header_frame = QFrame()
        self.header_frame.setObjectName("collapsible_header")
        self.header_frame.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header_frame.setFixedHeight(28)

        h_layout = QHBoxLayout(self.header_frame)
        h_layout.setContentsMargins(8, 2, 8, 2)
        h_layout.setSpacing(6)

        self.lbl_arrow = QLabel("▸")
        self.lbl_arrow.setObjectName("collapsible_arrow")
        self.lbl_arrow.setStyleSheet("font-size: 8pt; font-weight: bold;")
        h_layout.addWidget(self.lbl_arrow)

        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("collapsible_title")
        h_layout.addWidget(self.lbl_title)

        h_layout.addStretch()

        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("collapsible_status")
        h_layout.addWidget(self.lbl_status)

        main_layout.addWidget(self.header_frame)

        # Content Container
        self.content_container = QWidget()
        self.content_container.setObjectName("collapsible_content")
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(8, 8, 8, 8)
        self.content_layout.setSpacing(6)
        self.content_container.setVisible(False)

        main_layout.addWidget(self.content_container)

    def mousePressEvent(self, event):
        # Click header to toggle
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        if self.header_frame.geometry().contains(pos):
            self.setExpanded(not self._expanded)
            event.accept()
            return
        super().mousePressEvent(event)

    def setExpanded(self, expanded: bool):
        self._expanded = expanded
        self.lbl_arrow.setText("▾" if expanded else "▸")
        self.content_container.setVisible(expanded)
        self.toggled.emit(expanded)

    def isExpanded(self) -> bool:
        return self._expanded

    def setTitle(self, title: str):
        self._title_text = title
        self.lbl_title.setText(title)

    def setStatus(self, status: str):
        self._status_text = status
        self.lbl_status.setText(status)

    def setContentWidget(self, widget: QWidget):
        # Clear existing content widget
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self._content_widget = widget
        if widget:
            self.content_layout.addWidget(widget)
