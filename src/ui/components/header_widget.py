from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget


class HeaderWidget(QWidget):
    """Header component displaying the application title and version."""

    def __init__(self, title: str = "Image To Hires", version: str = "version 1.0.0", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("header")
        self.setFixedHeight(70)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)

        title_label = QLabel(title)
        title_label.setObjectName("headerTitle")

        version_label = QLabel(version)
        version_label.setObjectName("headerVersion")
        version_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(title_label)
        layout.addStretch()
        layout.addWidget(version_label)
