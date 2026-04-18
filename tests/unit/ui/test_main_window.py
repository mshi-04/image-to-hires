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
    from src.ui.workers.upscale_queue_worker import UpscaleQueueWorker

    PYSIDE_AVAILABLE = True
except ModuleNotFoundError:
    QApplication = None
    MainWindow = None
    PYSIDE_AVAILABLE = False


class FakeBatchUseCase:
    def __init__(self, runtime_error: Exception | None = None) -> None:
        self.runtime_error = runtime_error
        self.ready_calls = 0
        self.last_command = None

    def ensure_runtime_ready(self) -> None:
        self.ready_calls += 1
        if self.runtime_error is not None:
            raise self.runtime_error

    def execute(self, command, item_started_callback=None, progress_callback=None):  # noqa: ANN001
        self.ensure_runtime_ready()
        self.last_command = command
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
        self.assertEqual(window.output_format_combo.currentText(), "入力と同じ")
        self.assertEqual(window.output_format_combo.currentData(), "keep_input")

    def test_file_selection_updates_file_list_without_changing_output_format(self) -> None:
        # Arrange
        base = Path.cwd() / "images"
        selected = [str(base / "a.png"), str(base / "b.png")]
        self.window.output_format_combo.setCurrentIndex(1)

        # Act
        with patch("src.ui.windows.main_window.QFileDialog.getOpenFileNames", return_value=(selected, "")):
            self.window._on_select_files_clicked()

        # Assert
        self.assertEqual(self.window.file_list_textbox.toPlainText(), "a.png\nb.png")
        self.assertEqual(self.window.output_format_combo.currentText(), "WebP（ロスレス）")
        self.assertEqual(self.window.output_format_combo.currentData(), "webp_lossless")
        self.assertTrue(self.window.start_button.isEnabled())

    def test_output_format_combo_has_expected_options(self) -> None:
        # Arrange
        window = self.window

        # Act / Assert
        self.assertEqual(window.output_format_combo.count(), 2)
        self.assertEqual(window.output_format_combo.itemText(0), "入力と同じ")
        self.assertEqual(window.output_format_combo.itemData(0), "keep_input")
        self.assertEqual(window.output_format_combo.itemText(1), "WebP（ロスレス）")
        self.assertEqual(window.output_format_combo.itemData(1), "webp_lossless")

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

    def test_start_button_remains_disabled_until_worker_thread_cleanup(self) -> None:
        # Arrange
        self.window._selected_files = [Path.cwd() / "images" / "a.png"]
        self.window._worker_thread = object()  # type: ignore[assignment]
        self.window.select_button.setEnabled(False)
        self.window._update_start_button_state()

        # Act
        self.window._on_batch_finished(1, 0)
        state_before_cleanup = self.window.start_button.isEnabled()
        select_before_cleanup = self.window.select_button.isEnabled()

        self.window._on_worker_thread_finished()
        state_after_cleanup = self.window.start_button.isEnabled()
        select_after_cleanup = self.window.select_button.isEnabled()

        # Assert
        self.assertFalse(state_before_cleanup)
        self.assertFalse(select_before_cleanup)
        self.assertTrue(state_after_cleanup)
        self.assertTrue(select_after_cleanup)

    def test_worker_passes_selected_output_format_mode_to_command(self) -> None:
        # Arrange
        class CapturingCommand:
            def __init__(
                self,
                input_image_paths,
                scale_factor,
                denoise_level,
                output_format_mode=None,
                output_image_paths=None,
            ) -> None:
                self.input_image_paths = input_image_paths
                self.scale_factor = scale_factor
                self.denoise_level = denoise_level
                self.output_format_mode = output_format_mode
                self.output_image_paths = output_image_paths

        fake_usecase = FakeBatchUseCase()
        worker = UpscaleQueueWorker(
            batch_usecase=fake_usecase,
            input_files=[Path.cwd() / "images" / "a.png"],
            denoise_level=1,
            scale_factor=2,
            output_format_mode="webp_lossless",
        )

        # Act
        with patch("src.ui.workers.upscale_queue_worker.RunUpscaleBatchCommand", CapturingCommand):
            worker.run()

        # Assert
        self.assertIsNotNone(fake_usecase.last_command)
        self.assertEqual(fake_usecase.last_command.output_format_mode, "webp_lossless")

    def test_start_worker_does_not_check_runtime_before_thread_start(self) -> None:
        # Arrange
        batch_usecase = FakeBatchUseCase(runtime_error=RuntimeError("runtime missing"))
        window = MainWindow(batch_usecase=batch_usecase)
        window._set_selected_files([Path.cwd() / "images" / "a.png"])

        # Act
        with (
            patch("src.ui.windows.main_window.QMessageBox.critical") as critical,
            patch("src.ui.windows.main_window.QThread.start", autospec=True) as thread_start,
        ):
            window._on_start_clicked()

        # Assert
        self.assertEqual(batch_usecase.ready_calls, 0)
        self.assertTrue(window._is_running)
        self.assertIsNotNone(window._worker_thread)
        self.assertFalse(window.start_button.isEnabled())
        critical.assert_not_called()
        thread_start.assert_called_once()
        window._on_worker_thread_finished()
        window.close()

    def test_batch_failed_shows_critical_message_and_resets_state(self) -> None:
        # Arrange
        self.window._selected_files = [Path.cwd() / "images" / "a.png"]
        self.window._is_running = True
        self.window.progress_label.setText("進行状況: 1/1")

        # Act
        with patch("src.ui.windows.main_window.QMessageBox.critical") as critical:
            self.window._on_batch_failed("Runtime missing error test")

        # Assert
        self.assertEqual(self.window.result_label.text(), "最終結果: 失敗 Runtime missing error test")
        self.assertFalse(self.window._is_running)
        critical.assert_called_once_with(self.window, "処理失敗", "Runtime missing error test")


if __name__ == "__main__":
    unittest.main()
