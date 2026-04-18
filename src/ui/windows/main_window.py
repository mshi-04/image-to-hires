from pathlib import Path

from PySide6.QtCore import QThread, Qt, Slot
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.domain.usecase.run_upscale_batch_usecase import RunUpscaleBatchUseCase
from src.ui.workers.upscale_queue_worker import UpscaleQueueWorker


class MainWindow(QMainWindow):
    """Main application window for image upscaling."""

    def __init__(self, batch_usecase: RunUpscaleBatchUseCase) -> None:
        super().__init__()
        self.setWindowTitle("Image To Hires")
        self.setMinimumSize(920, 720)

        self._selected_files: list[Path] = []
        self._is_running = False
        self._worker_thread: QThread | None = None
        self._worker: UpscaleQueueWorker | None = None

        self._batch_usecase = batch_usecase

        self._build_ui()
        self._bind_events()
        self._update_file_display()
        self._update_start_button_state()

    def _build_ui(self) -> None:
        root = QWidget(self)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(24, 20, 24, 20)
        root_layout.setSpacing(20)

        title_label = QLabel("Image To Hires")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        root_layout.addWidget(title_label)

        input_label = QLabel("拡大元の画像ファイル")
        root_layout.addWidget(input_label)

        input_row_layout = QHBoxLayout()
        input_row_layout.setSpacing(12)

        self.file_list_textbox = QPlainTextEdit()
        self.file_list_textbox.setReadOnly(True)
        self.file_list_textbox.setPlaceholderText("ファイルを選択してください")
        self.file_list_textbox.setFixedHeight(140)
        input_row_layout.addWidget(self.file_list_textbox, stretch=4)

        self.select_button = QPushButton("ファイルを選択")
        self.select_button.setFixedHeight(48)
        self.select_button.setMinimumWidth(180)
        input_row_layout.addWidget(self.select_button, stretch=1)

        root_layout.addLayout(input_row_layout)

        parameter_label = QLabel("パラメーター")
        root_layout.addWidget(parameter_label)

        form_layout = QFormLayout()
        form_layout.setSpacing(14)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)

        self.denoise_combo = self._build_combo_box(
            values=[("なし", -1), ("0", 0), ("1", 1), ("2", 2), ("3", 3)]
        )
        form_layout.addRow("デノイズ:", self.denoise_combo)

        self.scale_combo = self._build_combo_box(
            values=[("2x", 2), ("3x", 3), ("4x", 4)]
        )
        form_layout.addRow("拡大率:", self.scale_combo)

        root_layout.addLayout(form_layout)

        status_label = QLabel("状態")
        root_layout.addWidget(status_label)

        self.progress_label = QLabel("進行状況: 0/0")
        self.current_file_label = QLabel("現在処理中: なし")
        self.result_label = QLabel("最終結果: 未開始")
        root_layout.addWidget(self.progress_label)
        root_layout.addWidget(self.current_file_label)
        root_layout.addWidget(self.result_label)

        self.start_button = QPushButton("拡大開始")
        self.start_button.setFixedHeight(52)
        root_layout.addWidget(self.start_button)

        root_layout.addStretch(1)

        self.setCentralWidget(root)

    @staticmethod
    def _build_combo_box(values: list[tuple[str, object]]) -> QComboBox:
        combo = QComboBox()
        combo.setFixedHeight(42)
        for label, data in values:
            combo.addItem(label, data)
        return combo

    def _bind_events(self) -> None:
        self.select_button.clicked.connect(self._on_select_files_clicked)
        self.start_button.clicked.connect(self._on_start_clicked)

    @Slot()
    def _on_select_files_clicked(self) -> None:
        selected_files, _ = QFileDialog.getOpenFileNames(
            self,
            "拡大する画像を選択",
            "",
            "Image Files (*.png *.jpg *.jpeg *.webp)",
        )
        if not selected_files:
            return

        self._set_selected_files([Path(path) for path in selected_files])

    @Slot()
    def _on_start_clicked(self) -> None:
        if self._is_running or not self._selected_files:
            return

        denoise_level = int(self.denoise_combo.currentData())
        scale_factor = int(self.scale_combo.currentData())

        self._start_worker(
            denoise_level=denoise_level,
            scale_factor=scale_factor,
        )

    def _start_worker(self, denoise_level: int, scale_factor: int) -> None:
        # Guard against re-entry if the previous thread has not yet fully cleaned up.
        if self._worker_thread is not None:
            return

        self._is_running = True
        self._update_start_button_state()
        self.select_button.setEnabled(False)

        worker = UpscaleQueueWorker(
            batch_usecase=self._batch_usecase,
            input_files=list(self._selected_files),
            denoise_level=denoise_level,
            scale_factor=scale_factor,
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
        self._is_running = True
        self._update_start_button_state()
        self.progress_label.setText(f"進行状況: 0/{total_count}")
        self.current_file_label.setText("現在処理中: 開始")
        self.result_label.setText("最終結果: 処理中")

    @Slot(str, int, int)
    def _on_item_started(self, file_name: str, processed_count: int, total_count: int) -> None:
        # processed_count is the 1-based index of the item now starting.
        # Subtract 1 to show how many have *completed* so far.
        self.progress_label.setText(f"進行状況: {max(processed_count - 1, 0)}/{total_count}")
        self.current_file_label.setText(f"現在処理中: {file_name}")

    @Slot(str, int, int, bool, str)
    def _on_item_progress(
        self,
        file_name: str,
        processed_count: int,
        total_count: int,
        succeeded: bool,
        detail: str,
    ) -> None:
        self.progress_label.setText(f"進行状況: {processed_count}/{total_count}")
        self.current_file_label.setText(f"現在処理中: {file_name}")

        if succeeded:
            self.result_label.setText(f"最終結果: 直近成功 {file_name}")
            return

        summary = f"最終結果: 直近失敗 {file_name}"
        if detail:
            summary = f"{summary} ({detail})"
        self.result_label.setText(summary)

    @Slot(int, int)
    def _on_batch_finished(self, completed_count: int, failed_count: int) -> None:
        self._is_running = False
        self._update_start_button_state()
        self.current_file_label.setText("現在処理中: 完了")
        self.result_label.setText(
            f"最終結果: 完了 成功 {completed_count} 件 / 失敗 {failed_count} 件"
        )

    @Slot(str)
    def _on_batch_failed(self, message: str) -> None:
        self._is_running = False
        self._update_start_button_state()
        self.current_file_label.setText("現在処理中: 異常終了")
        self.result_label.setText(f"最終結果: 失敗 {message}")
        QMessageBox.critical(self, "処理失敗", message)

    @Slot()
    def _on_worker_thread_finished(self) -> None:
        self._worker = None
        self._worker_thread = None
        self.select_button.setEnabled(True)
        self._update_start_button_state()

    def _update_file_display(self) -> None:
        file_names = [path.name for path in self._selected_files]
        self.file_list_textbox.setPlainText("\n".join(file_names))

    def _update_start_button_state(self) -> None:
        can_start = bool(self._selected_files) and not self._is_running and self._worker_thread is None
        self.start_button.setEnabled(can_start)

    def _set_selected_files(self, files: list[Path]) -> None:
        self._selected_files = files
        self._update_file_display()
        self.result_label.setText("最終結果: 入力待機")
        self._update_start_button_state()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._worker_thread is not None and self._worker_thread.isRunning():
            QMessageBox.information(self, "処理中", "処理中はウィンドウを閉じられません。完了後に閉じてください。")
            event.ignore()
            return
        super().closeEvent(event)
