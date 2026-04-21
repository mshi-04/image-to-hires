import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from PySide6.QtWidgets import QApplication
except ModuleNotFoundError:
    QApplication = None
    PYSIDE_AVAILABLE = False
else:
    PYSIDE_AVAILABLE = True

from src.domain.ports.application_settings_port import ApplicationSettingsPort
from src.domain.usecase.run_upscale_batch_usecase import RunUpscaleBatchResult, UpscaleBatchItemResult
from src.domain.value_objects.denoise_level import DenoiseLevel
from src.domain.value_objects.scale_factor import ScaleFactor
from src.ui.windows.main_window import MainWindow
from src.ui.workers.upscale_queue_worker import UpscaleQueueWorker


class FakeApplicationSettings(ApplicationSettingsPort):
    def __init__(
        self,
        auto_sizing_enabled: bool = False,
        append_output_suffix: bool = True,
        last_selected_directory: str | None = None,
    ) -> None:
        self.auto_sizing_enabled = auto_sizing_enabled
        self.append_output_suffix = append_output_suffix
        self.last_selected_directory = last_selected_directory
        self.saved_auto_sizing_values: list[bool] = []
        self.saved_append_output_suffix_values: list[bool] = []
        self.saved_last_selected_directory_values: list[str] = []

    def load_auto_sizing_enabled(self) -> bool:
        return self.auto_sizing_enabled

    def save_auto_sizing_enabled(self, enabled: bool) -> None:
        self.auto_sizing_enabled = enabled
        self.saved_auto_sizing_values.append(enabled)

    def load_append_output_suffix(self) -> bool:
        return self.append_output_suffix

    def save_append_output_suffix(self, enabled: bool) -> None:
        self.append_output_suffix = enabled
        self.saved_append_output_suffix_values.append(enabled)

    def load_last_selected_directory(self) -> str | None:
        return self.last_selected_directory

    def save_last_selected_directory(self, directory: str) -> None:
        self.last_selected_directory = directory
        self.saved_last_selected_directory_values.append(directory)


class FakeBatchUseCase:
    def __init__(self) -> None:
        self.last_command = None

    def execute(self, command, item_started_callback=None, progress_callback=None):  # noqa: ANN001
        self.last_command = command
        paths = [Path(path) for path in command.input_image_paths]
        items: list[UpscaleBatchItemResult] = []
        if paths:
            scale = ScaleFactor(command.scale_factor)
            denoise = DenoiseLevel(command.denoise_level)
            if item_started_callback is not None:
                item_started_callback(paths[0], 1, len(paths))
            item = UpscaleBatchItemResult(
                input_image_path=paths[0],
                output_image_path=paths[0],
                scale_factor=scale,
                denoise_level=denoise,
            )
            items.append(item)
            if progress_callback is not None:
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
        self.app_settings = FakeApplicationSettings()
        self.batch_usecase = FakeBatchUseCase()
        self.window = MainWindow(
            batch_usecase=self.batch_usecase,
            app_settings=self.app_settings,
        )

    def tearDown(self) -> None:
        self.window.close()

    def test_initial_state_disables_start_button_and_uses_saved_auto_sizing_default(self) -> None:
        # Arrange / Act

        # Assert
        self.assertFalse(self.window.start_button.isEnabled())
        self.assertFalse(self.window.settings_widget.is_auto_sizing_enabled())
        self.assertTrue(self.window.settings_widget.should_append_output_suffix())
        self.assertTrue(self.window.settings_widget.scale_combo.isEnabled())

    def test_load_persisted_settings_restores_checkbox_states(self) -> None:
        # Arrange
        self.window.close()
        persisted_settings = FakeApplicationSettings(
            auto_sizing_enabled=True,
            append_output_suffix=False,
            last_selected_directory="C:/images",
        )

        # Act
        window = MainWindow(batch_usecase=FakeBatchUseCase(), app_settings=persisted_settings)

        # Assert
        self.assertTrue(window.settings_widget.is_auto_sizing_enabled())
        self.assertFalse(window.settings_widget.should_append_output_suffix())
        self.assertEqual(window.settings_widget.get_denoise_level(), 3)
        self.assertFalse(window.settings_widget.denoise_combo.isEnabled())
        self.assertFalse(window.settings_widget.scale_combo.isEnabled())
        self.assertEqual(Path(window.input_area._initial_directory), Path("C:/images"))
        window.close()

    def test_loading_persisted_settings_does_not_re_save_values(self) -> None:
        # Arrange
        self.window.close()
        persisted_settings = FakeApplicationSettings(auto_sizing_enabled=True)

        # Act
        window = MainWindow(batch_usecase=FakeBatchUseCase(), app_settings=persisted_settings)

        # Assert
        self.assertEqual(persisted_settings.saved_auto_sizing_values, [])
        self.assertEqual(persisted_settings.saved_append_output_suffix_values, [])
        self.assertEqual(persisted_settings.saved_last_selected_directory_values, [])
        window.close()

    def test_last_selected_directory_is_persisted_when_notified(self) -> None:
        # Arrange / Act
        self.window._on_last_directory_selected("C:/images/last")

        # Assert
        self.assertEqual(self.app_settings.saved_last_selected_directory_values, ["C:/images/last"])

    def test_auto_sizing_toggle_persists_setting(self) -> None:
        # Arrange

        # Act
        self.window.settings_widget.set_auto_sizing_enabled(True)
        self.window.settings_widget.set_auto_sizing_enabled(False)

        # Assert
        self.assertEqual(self.app_settings.saved_auto_sizing_values[-2:], [True, False])

    def test_auto_sizing_locks_denoise_to_three_and_restores_previous_value(self) -> None:
        # Arrange
        self.window.settings_widget.denoise_combo.setCurrentIndex(
            self.window.settings_widget.denoise_combo.findData(1)
        )

        # Act
        self.window.settings_widget.set_auto_sizing_enabled(True)
        denoise_locked_value = self.window.settings_widget.get_denoise_level()
        denoise_locked_enabled = self.window.settings_widget.denoise_combo.isEnabled()
        self.window.settings_widget.set_auto_sizing_enabled(False)

        # Assert
        self.assertEqual(denoise_locked_value, 3)
        self.assertFalse(denoise_locked_enabled)
        self.assertEqual(self.window.settings_widget.get_denoise_level(), 1)
        self.assertTrue(self.window.settings_widget.denoise_combo.isEnabled())

    def test_append_output_suffix_toggle_persists_setting(self) -> None:
        # Arrange

        # Act
        self.window.settings_widget.set_append_output_suffix(False)
        self.window.settings_widget.set_append_output_suffix(True)

        # Assert
        self.assertEqual(self.app_settings.saved_append_output_suffix_values[-2:], [False, True])

    def test_on_files_selected_enables_start_button(self) -> None:
        # Arrange
        files = [Path("C:/images/a.png"), Path("C:/images/b.png")]

        # Act
        self.window._on_files_selected(files)

        # Assert
        self.assertTrue(self.window.start_button.isEnabled())

    def test_on_start_clicked_passes_auto_sizing_state_to_worker(self) -> None:
        # Arrange
        self.window._on_files_selected([Path("C:/images/a.png")])
        self.window.settings_widget.set_auto_sizing_enabled(True)
        self.window.settings_widget.set_append_output_suffix(False)

        # Act
        with patch.object(self.window, "_start_worker") as start_worker:
            self.window._on_start_clicked()

        # Assert
        start_worker.assert_called_once_with(3, 2, True, False)

    def test_worker_passes_auto_sizing_flag_to_command(self) -> None:
        # Arrange
        worker = UpscaleQueueWorker(
            batch_usecase=self.batch_usecase,
            input_files=[Path("C:/images/a.png")],
            denoise_level=1,
            scale_factor=4,
            auto_sizing_enabled=True,
            append_output_suffix=False,
        )

        # Act
        worker.run()

        # Assert
        self.assertIsNotNone(self.batch_usecase.last_command)
        self.assertEqual(self.batch_usecase.last_command.denoise_level, 1)
        self.assertEqual(self.batch_usecase.last_command.scale_factor, 4)
        self.assertTrue(self.batch_usecase.last_command.auto_sizing_enabled)
        self.assertFalse(self.batch_usecase.last_command.append_output_suffix)

    def test_activate_from_secondary_launch_restores_window_from_minimized_state(self) -> None:
        # Arrange
        self.window.show()
        self.window.showMinimized()
        self.__class__._app.processEvents()

        # Act
        self.window.activate_from_secondary_launch()
        self.__class__._app.processEvents()

        # Assert
        self.assertFalse(self.window.isMinimized())
        self.assertTrue(self.window.isVisible())

    def test_activate_from_secondary_launch_preserves_current_state(self) -> None:
        # Arrange
        selected_files = [Path("C:/images/a.png"), Path("C:/images/b.png")]
        self.window._on_files_selected(selected_files)
        self.window._is_running = True

        # Act
        self.window.activate_from_secondary_launch()

        # Assert
        self.assertTrue(self.window._is_running)
        self.assertEqual(self.window._selected_files, selected_files)
        self.assertEqual(self.window.queue_widget.file_list_widget.count(), len(selected_files))


if __name__ == "__main__":
    unittest.main()
