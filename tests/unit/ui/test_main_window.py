import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from PySide6.QtWidgets import QApplication

    from src.domain.usecase.run_upscale_batch_usecase import (
        RunUpscaleBatchResult,
        UpscaleBatchItemResult,
    )
    from src.domain.value_objects.denoise_level import DenoiseLevel
    from src.domain.value_objects.scale_factor import ScaleFactor
    from src.ui.windows.main_window import MainWindow

    PYSIDE_AVAILABLE = True
except ModuleNotFoundError:
    QApplication = None
    MainWindow = None
    PYSIDE_AVAILABLE = False


class FakeBatchUseCase:
    def __init__(self, runtime_error: Exception | None = None) -> None:
        self.runtime_error = runtime_error
        self.ready_calls = 0

    def ensure_runtime_ready(self) -> None:
        self.ready_calls += 1
        if self.runtime_error is not None:
            raise self.runtime_error

    def execute(self, command, item_started_callback=None, progress_callback=None):  # noqa: ANN001
        paths = [Path(p) for p in command.input_image_paths]
        scale = ScaleFactor(command.scale_factor)
        denoise = DenoiseLevel(command.denoise_level)
        items = []
        if paths:
            if item_started_callback:
                item_started_callback(paths[0], 1, len(paths))
            item = UpscaleBatchItemResult(
                input_image_path=paths[0],
                output_image_path=paths[0],
                scale_factor=scale,
                denoise_level=denoise,
            )
            items.append(item)
            if progress_callback:
                progress_callback(item, 1, len(paths))
        return RunUpscaleBatchResult(
            items=tuple(items),
            processed_count=len(paths),
            success_count=len(paths),
            failure_count=0,
            total_count=len(paths),
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
        base = Path.cwd() / "images"
        selected = [str(base / "a.png"), str(base / "b.png")]

        # Act
        with patch("src.ui.windows.main_window.QFileDialog.getOpenFileNames", return_value=(selected, "")):
            self.window._on_select_files_clicked()

        # Assert
        self.assertEqual(self.window.file_list_textbox.toPlainText(), "a.png\nb.png")
        self.assertEqual(self.window.output_format_display.text(), ".png")
        self.assertTrue(self.window.start_button.isEnabled())

    def test_file_selection_with_mixed_extensions_shows_mixed_label(self) -> None:
        # Arrange
        base = Path.cwd() / "images"
        selected = [str(base / "a.png"), str(base / "b.jpg"), str(base / "c.webp")]

        # Act
        with patch("src.ui.windows.main_window.QFileDialog.getOpenFileNames", return_value=(selected, "")):
            self.window._on_select_files_clicked()

        # Assert
        self.assertEqual(self.window.output_format_display.text(), "入力と同じ (.jpg, .png, .webp)")

    def test_start_button_disabled_while_running_and_enabled_after_finish(self) -> None:
        # Arrange
        self.window._selected_files = [Path.cwd() / "images" / "a.png"]
        self.window._update_start_button_state()

        # Act
        self.window._on_batch_started(1)
        self.window._update_start_button_state()
        running_state = self.window.start_button.isEnabled()

        self.window._on_batch_finished(1, 0)
        self.window._update_start_button_state()
        completed_state = self.window.start_button.isEnabled()

        # Assert
        self.assertFalse(running_state)
        self.assertTrue(completed_state)

    def test_start_click_shows_error_and_skips_worker_when_runtime_is_not_ready(self) -> None:
        # Arrange
        runtime_error = RuntimeError("Real-CUGAN runtime is not ready")
        self.window.close()
        self.window = MainWindow(batch_usecase=FakeBatchUseCase(runtime_error=runtime_error))
        self.window._set_selected_files([Path.cwd() / "images" / "a.png"])

        # Act
        with (
            patch.object(self.window, "_start_worker") as start_worker,
            patch("src.ui.windows.main_window.QMessageBox.critical") as critical,
        ):
            self.window._on_start_clicked()

        # Assert
        start_worker.assert_not_called()
        critical.assert_called_once()
        self.assertEqual(self.window.current_file_label.text(), "現在処理中: 開始前エラー")
        self.assertEqual(
            self.window.result_label.text(),
            "最終結果: 失敗 Real-CUGAN runtime is not ready",
        )


if __name__ == "__main__":
    unittest.main()
