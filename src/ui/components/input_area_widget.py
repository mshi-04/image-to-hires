from pathlib import Path

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QWidget, QFileDialog


class InputAreaWidget(QWidget):
    """Component for selecting input image files."""

    files_selected = Signal(list)  # Emits list[Path]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.input_path_edit = QLineEdit()
        self.input_path_edit.setPlaceholderText("拡大元の画像ファイル")
        self.input_path_edit.setReadOnly(True)
        self.input_path_edit.setMinimumHeight(34)

        self.select_button = QPushButton("ファイルを選択")
        self.select_button.setObjectName("actionButton")
        self.select_button.setMinimumHeight(34)
        self.select_button.clicked.connect(self._on_select_clicked)

        layout.addWidget(self.input_path_edit, stretch=1)
        layout.addWidget(self.select_button)

    @Slot()
    def _on_select_clicked(self) -> None:
        selected_files, _ = QFileDialog.getOpenFileNames(
            self,
            "拡大する画像を選択",
            "",
            "Image Files (*.png *.jpg *.jpeg *.webp)",
        )
        if not selected_files:
            return

        paths = [Path(p) for p in selected_files]
        self.update_display(len(paths))
        self.files_selected.emit(paths)

    def update_display(self, count: int) -> None:
        """Update the text field with the number of selected files."""
        if count > 0:
            self.input_path_edit.setText(f"{count} 件のファイルが選択されています")
        else:
            self.input_path_edit.clear()

    def set_select_enabled(self, enabled: bool) -> None:
        self.select_button.setEnabled(enabled)
