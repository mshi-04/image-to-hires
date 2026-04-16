import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

try:
    from PySide6.QtWidgets import QApplication

    from src.ui.windows.main_window import MainWindow

    PYSIDE_AVAILABLE = True
except ModuleNotFoundError:
    QApplication = None
    MainWindow = None
    PYSIDE_AVAILABLE = False


class FakeBatchUseCase:
    def execute(self, command, item_started_callback=None, progress_callback=None):  # noqa: ANN001
        if item_started_callback and command.input_image_paths:
            item_started_callback(
                Path(command.input_image_paths[0]),
                1,
                len(command.input_image_paths),
            )
        if progress_callback and command.input_image_paths:
            progress_callback(
                SimpleNamespace(
                    input_image_path=Path(command.input_image_paths[0]),
                    output_image_path=Path(command.input_image_paths[0]),
                    is_success=True,
                    error=None,
                ),
                1,
                len(command.input_image_paths),
            )
        return SimpleNamespace(
            items=[],
            processed_count=len(command.input_image_paths),
            success_count=len(command.input_image_paths),
            failure_count=0,
            total_count=len(command.input_image_paths),
        )


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is required for UI tests.")
class TestMainWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        # Arrange
        self.window = MainWindow(batch_usecase=FakeBatchUseCase())

    def tearDown(self) -> None:
        self.window.close()

    def test_initial_state_disables_start_button(self) -> None:
        # Arrange
        window = self.window

        # Act
        is_enabled = window.start_button.isEnabled()

        # Assert
        self.assertFalse(is_enabled)
        self.assertEqual(window.output_format_display.text(), "未選択")

    def test_file_selection_updates_file_list_and_format(self) -> None:
        # Arrange
        selected = [r"C:\images\a.png", r"C:\images\b.png"]

        # Act
        with patch("src.ui.windows.main_window.QFileDialog.getOpenFileNames", return_value=(selected, "")):
            self.window._on_select_files_clicked()

        # Assert
        self.assertEqual(self.window.file_list_textbox.toPlainText(), "a.png\nb.png")
        self.assertEqual(self.window.output_format_display.text(), ".png")
        self.assertTrue(self.window.start_button.isEnabled())

    def test_file_selection_with_mixed_extensions_shows_mixed_label(self) -> None:
        # Arrange
        selected = [r"C:\images\a.png", r"C:\images\b.jpg", r"C:\images\c.webp"]

        # Act
        with patch("src.ui.windows.main_window.QFileDialog.getOpenFileNames", return_value=(selected, "")):
            self.window._on_select_files_clicked()

        # Assert
        self.assertEqual(self.window.output_format_display.text(), "入力と同じ (.jpg, .png, .webp)")

    def test_start_button_disabled_while_running_and_enabled_after_finish(self) -> None:
        # Arrange
        self.window._selected_files = [Path(r"C:\images\a.png")]
        self.window._update_start_button_state()

        # Act
        self.window._on_batch_started(1)
        self.window._is_running = True
        self.window._update_start_button_state()
        running_state = self.window.start_button.isEnabled()

        self.window._on_batch_finished(1, 0)
        completed_state = self.window.start_button.isEnabled()

        # Assert
        self.assertFalse(running_state)
        self.assertTrue(completed_state)


if __name__ == "__main__":
    unittest.main()
