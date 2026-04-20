from pathlib import Path

from PySide6.QtWidgets import QListWidget, QListWidgetItem, QProgressBar, QVBoxLayout, QWidget


class QueueWidget(QWidget):
    """Component for displaying the processing queue and overall progress."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.file_list_widget = QListWidget()
        self.file_list_widget.setMinimumHeight(96)
        self.file_list_widget.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        layout.addWidget(self.file_list_widget)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(14)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("進行状況: %p%")
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self._list_items_map: dict[str, QListWidgetItem] = {}

    def populate(self, files: list[Path]) -> None:
        """Clear list and add new files as pending items."""
        self.file_list_widget.clear()
        self._list_items_map.clear()
        self.progress_bar.setValue(0)
        self.progress_bar.setRange(0, len(files))

        for path in files:
            item = QListWidgetItem(f"{path.name}  -  待機中")
            self.file_list_widget.addItem(item)
            self._list_items_map[path.name] = item

    def update_item_status(self, filename: str, status_text: str) -> None:
        """Update the label of a specific item in the queue."""
        item = self._list_items_map.get(filename)
        if item:
            item.setText(f"{filename}  -  {status_text}")

    def reset_status_all(self, status_text: str = "待機中") -> None:
        """Reset text for all current items."""
        for filename, item in self._list_items_map.items():
            item.setText(f"{filename}  -  {status_text}")

    def update_progress(self, value: int, maximum: int | None = None) -> None:
        """Update overall progress bar."""
        if maximum is not None:
            self.progress_bar.setRange(0, maximum)
        self.progress_bar.setValue(value)
