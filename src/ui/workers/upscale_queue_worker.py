from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from src.domain.usecase.run_upscale_batch_usecase import (
    RunUpscaleBatchCommand,
    RunUpscaleBatchUseCase,
    UpscaleBatchItemResult,
)


class UpscaleQueueWorker(QObject):
    """Run sequential upscale jobs off the UI thread."""

    batch_started = Signal(int)
    item_started = Signal(str, int, int)
    item_progress = Signal(str, int, int, bool, str)
    batch_finished = Signal(int, int)
    batch_failed = Signal(str)
    finished = Signal()

    def __init__(
        self,
        batch_usecase: RunUpscaleBatchUseCase,
        input_files: list[Path],
        denoise_level: int,
        scale_factor: int,
        output_format_mode: str,
    ) -> None:
        super().__init__()
        self._batch_usecase = batch_usecase
        self._input_files = list(input_files)
        self._denoise_level = denoise_level
        self._scale_factor = scale_factor
        self._output_format_mode = output_format_mode

    @Slot()
    def run(self) -> None:
        self.batch_started.emit(len(self._input_files))

        try:
            command = RunUpscaleBatchCommand(
                input_image_paths=self._input_files,
                denoise_level=self._denoise_level,
                scale_factor=self._scale_factor,
                output_format_mode=self._output_format_mode,
            )
            result = self._batch_usecase.execute(
                command=command,
                item_started_callback=self._emit_item_started,
                progress_callback=self._emit_item_progress,
            )
            self.batch_finished.emit(result.success_count, result.failure_count)
        except Exception as exc:
            self.batch_failed.emit(str(exc))
        finally:
            self.finished.emit()

    def _emit_item_progress(
        self,
        item_result: UpscaleBatchItemResult,
        processed_count: int,
        total_count: int,
    ) -> None:
        detail = ""
        if item_result.is_success and item_result.output_image_path:
            detail = str(item_result.output_image_path)
        if not item_result.is_success and item_result.error is not None:
            detail = str(item_result.error)

        self.item_progress.emit(
            item_result.input_image_path.name,
            processed_count,
            total_count,
            item_result.is_success,
            detail,
        )

    def _emit_item_started(self, input_image_path: Path, processed_count: int, total_count: int) -> None:
        self.item_started.emit(input_image_path.name, processed_count, total_count)
