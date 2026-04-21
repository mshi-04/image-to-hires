from pathlib import Path

from PySide6.QtCore import QThread, Slot
from PySide6.QtGui import QCloseEvent, Qt
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QMessageBox, QPushButton, QVBoxLayout, QWidget

from src.domain.ports.application_settings_port import ApplicationSettingsPort
from src.domain.usecase.run_upscale_batch_usecase import RunUpscaleBatchUseCase
from src.ui.workers.upscale_queue_worker import UpscaleQueueWorker
from src.ui.styles import MAIN_WINDOW_STYLESHEET

from src.ui.components.header_widget import HeaderWidget
from src.ui.components.input_area_widget import InputAreaWidget
from src.ui.components.settings_widget import SettingsWidget
from src.ui.components.queue_widget import QueueWidget


class MainWindow(QMainWindow):
    """Refactored main controller window, orchestrating extracted child components."""

    def __init__(
        self,
        batch_usecase: RunUpscaleBatchUseCase,
        app_settings: ApplicationSettingsPort,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Image To Hires")
        self.setMinimumSize(850, 700)

        self._selected_files: list[Path] = []
        self._is_running = False
        self._worker_thread: QThread | None = None
        self._worker: UpscaleQueueWorker | None = None

        self._batch_usecase = batch_usecase
        self._app_settings = app_settings

        self._build_ui()
        self._load_persisted_settings()
        self._bind_events()
        self._update_start_button_state()

    def _build_ui(self) -> None:
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.setStyleSheet(MAIN_WINDOW_STYLESHEET)

        # Header
        self.header_widget = HeaderWidget()
        main_layout.addWidget(self.header_widget)

        # Content Area
        content = QWidget()
        content.setObjectName("contentArea")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(40, 30, 40, 30)
        content_layout.setSpacing(25)

        self.input_area = InputAreaWidget()
        content_layout.addWidget(self.input_area)

        self.queue_widget = QueueWidget()
        content_layout.addWidget(self.queue_widget)

        self.settings_widget = SettingsWidget()
        content_layout.addWidget(self.settings_widget)

        # Start Button
        start_btn_layout = QHBoxLayout()
        start_btn_layout.addStretch()
        self.start_button = QPushButton("拡大開始")
        self.start_button.setObjectName("actionButton")
        self.start_button.setMinimumHeight(60)
        self.start_button.setMinimumWidth(250)
        start_btn_layout.addWidget(self.start_button)
        start_btn_layout.addStretch()
        
        content_layout.addLayout(start_btn_layout)
        
        main_layout.addWidget(content, stretch=1)

        # Footer
        footer = QWidget()
        footer.setObjectName("footer")
        footer.setFixedHeight(25)
        main_layout.addWidget(footer)

    def _bind_events(self) -> None:
        self.input_area.files_selected.connect(self._on_files_selected)
        self.input_area.last_directory_selected.connect(self._on_last_directory_selected)
        self.start_button.clicked.connect(self._on_start_clicked)
        self.settings_widget.auto_sizing_checkbox.toggled.connect(self._on_auto_sizing_toggled)
        self.settings_widget.append_output_suffix_checkbox.toggled.connect(self._on_append_output_suffix_toggled)

    @Slot(list)
    def _on_files_selected(self, files: list[Path]) -> None:
        self._selected_files = files
        self.queue_widget.populate(files)
        self._update_start_button_state()

    @Slot()
    def _on_start_clicked(self) -> None:
        if self._is_running or not self._selected_files:
            return

        denoise_level = self.settings_widget.get_denoise_level()
        scale_factor = self.settings_widget.get_scale_factor()
        auto_sizing_enabled = self.settings_widget.is_auto_sizing_enabled()
        append_output_suffix = self.settings_widget.should_append_output_suffix()

        self._start_worker(denoise_level, scale_factor, auto_sizing_enabled, append_output_suffix)

    def _start_worker(
        self,
        denoise_level: int,
        scale_factor: int,
        auto_sizing_enabled: bool,
        append_output_suffix: bool,
    ) -> None:
        if self._worker_thread is not None:
            return

        self._is_running = True
        self._update_start_button_state()
        
        self.input_area.set_select_enabled(False)
        self.settings_widget.set_inputs_enabled(False)

        worker = UpscaleQueueWorker(
            batch_usecase=self._batch_usecase,
            input_files=list(self._selected_files),
            denoise_level=denoise_level,
            scale_factor=scale_factor,
            auto_sizing_enabled=auto_sizing_enabled,
            append_output_suffix=append_output_suffix,
        )
        thread = QThread(self)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.batch_started.connect(self._on_batch_started)
        worker.item_started.connect(self._on_item_started)
        worker.item_progress.connect(self._on_item_progress)
        worker.batch_finished.connect(self._on_batch_finished)
        worker.batch_failed.connect(self._on_batch_failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_worker_thread_finished)

        self._worker = worker
        self._worker_thread = thread
        thread.start()

    @Slot(int)
    def _on_batch_started(self, total_count: int) -> None:
        self.queue_widget.reset_status_all("待機中")
        self.queue_widget.update_progress(0, total_count)

    @Slot(str, int, int)
    def _on_item_started(self, file_name: str, processed_count: int, total_count: int) -> None:
        self.queue_widget.update_item_status(file_name, "処理中...")
        completed = max(processed_count - 1, 0)
        self.queue_widget.update_progress(completed)

    @Slot(str, int, int, bool, str)
    def _on_item_progress(
        self,
        file_name: str,
        processed_count: int,
        total_count: int,
        succeeded: bool,
        detail: str,
    ) -> None:
        self.queue_widget.update_progress(processed_count)
        status = "✓ 完了" if succeeded else f"✗ 失敗 ({detail})"
        self.queue_widget.update_item_status(file_name, status)

    @Slot(int, int)
    def _on_batch_finished(self, completed_count: int, failed_count: int) -> None:
        self._is_running = False

    @Slot(str)
    def _on_batch_failed(self, message: str) -> None:
        self._is_running = False
        QMessageBox.critical(self, "処理失敗", f"バッチ処理が異常終了しました:\n{message}")

    @Slot()
    def _on_worker_thread_finished(self) -> None:
        self._worker = None
        self._worker_thread = None
        self.input_area.set_select_enabled(True)
        self.settings_widget.set_inputs_enabled(True)
        self._update_start_button_state()

    def _update_start_button_state(self) -> None:
        can_start = bool(self._selected_files) and not self._is_running and self._worker_thread is None
        self.start_button.setEnabled(can_start)

    @Slot(bool)
    def _on_auto_sizing_toggled(self, enabled: bool) -> None:
        self._app_settings.save_auto_sizing_enabled(enabled)

    @Slot(bool)
    def _on_append_output_suffix_toggled(self, enabled: bool) -> None:
        self._app_settings.save_append_output_suffix(enabled)

    @Slot(str)
    def _on_last_directory_selected(self, directory: str) -> None:
        self._app_settings.save_last_selected_directory(directory)

    def _load_persisted_settings(self) -> None:
        self.settings_widget.set_auto_sizing_enabled(self._app_settings.load_auto_sizing_enabled())
        self.settings_widget.set_append_output_suffix(self._app_settings.load_append_output_suffix())
        self.input_area.set_initial_directory(self._app_settings.load_last_selected_directory())

    @Slot()
    def activate_from_secondary_launch(self) -> None:
        if self.windowState() & Qt.WindowState.WindowMinimized:
            self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._worker_thread is not None and self._worker_thread.isRunning():
            QMessageBox.information(self, "処理中", "処理中はウィンドウを閉じられません。完了後に閉じてください。")
            event.ignore()
            return
        super().closeEvent(event)
