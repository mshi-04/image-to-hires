from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from src.domain.ports.image_size_reader_port import ImageSizeReaderPort
from src.domain.ports.image_storage_port import ImageStoragePort
from src.domain.ports.upscale_engine_port import UpscaleEnginePort
from src.domain.usecase.run_upscale_usecase import RunUpscaleCommand, RunUpscaleUseCase
from src.domain.value_objects.denoise_level import DenoiseLevel
from src.domain.value_objects.scale_factor import ScaleFactor


@dataclass(frozen=True)
class RunUpscaleBatchCommand:
    """Input payload for batch upscaling."""

    input_image_paths: Sequence[Path | str]
    scale_factor: int
    denoise_level: int
    auto_sizing_enabled: bool = False
    append_output_suffix: bool = True
    output_image_paths: Sequence[Path | str | None] | None = None


@dataclass(frozen=True)
class UpscaleBatchItemResult:
    """Per-item result for batch upscaling."""

    input_image_path: Path
    output_image_path: Path | None
    scale_factor: ScaleFactor
    denoise_level: DenoiseLevel
    error: Exception | None = None

    @property
    def is_success(self) -> bool:
        return self.error is None


@dataclass(frozen=True)
class RunUpscaleBatchResult:
    """Aggregated result for batch upscaling."""

    items: tuple[UpscaleBatchItemResult, ...]
    processed_count: int
    success_count: int
    failure_count: int
    total_count: int


class RunUpscaleBatchUseCase:
    """Execute sequential upscaling for multiple images."""

    def __init__(
        self,
        upscale_engine: UpscaleEnginePort,
        image_storage: ImageStoragePort,
        image_size_reader: ImageSizeReaderPort | None = None,
    ) -> None:
        self._upscale_engine = upscale_engine
        self._image_storage = image_storage
        self._image_size_reader = image_size_reader

    def ensure_runtime_ready(self) -> None:
        self._upscale_engine.ensure_runtime_ready()

    def execute(
        self,
        command: RunUpscaleBatchCommand,
        item_started_callback: Callable[[Path, int, int], None] | None = None,
        progress_callback: Callable[[UpscaleBatchItemResult, int, int], None] | None = None,
    ) -> RunUpscaleBatchResult:
        scale_factor = ScaleFactor(command.scale_factor)
        denoise_level = DenoiseLevel(command.denoise_level)
        input_image_paths = list(command.input_image_paths)
        total_count = len(input_image_paths)
        if total_count == 0:
            return RunUpscaleBatchResult(
                items=tuple(),
                processed_count=0,
                success_count=0,
                failure_count=0,
                total_count=0,
            )

        self.ensure_runtime_ready()
        output_image_paths = self._resolve_output_image_paths(command.output_image_paths, total_count)
        single_usecase = RunUpscaleUseCase(
            self._upscale_engine,
            self._image_storage,
            image_size_reader=self._image_size_reader,
        )

        item_results: list[UpscaleBatchItemResult] = []
        success_count = 0
        failure_count = 0

        for index, input_image_path in enumerate(input_image_paths):
            current_input_path = Path(input_image_path)
            if item_started_callback is not None:
                item_started_callback(current_input_path, index + 1, total_count)
            job = None
            output_image_path: Path | None = None
            try:
                output_candidate = output_image_paths[index] if output_image_paths is not None else None
                job = single_usecase.prepare_job(
                    RunUpscaleCommand(
                        input_image_path=current_input_path,
                        output_image_path=output_candidate,
                        scale_factor=scale_factor.value,
                        denoise_level=denoise_level.value,
                        auto_sizing_enabled=command.auto_sizing_enabled,
                        append_output_suffix=command.append_output_suffix,
                    )
                )
                output_image_path = job.output_image.value
                result = single_usecase.execute_job(job)
                item_result = UpscaleBatchItemResult(
                    input_image_path=job.input_image.value,
                    output_image_path=result.output_image_path.value,
                    scale_factor=result.scale_factor,
                    denoise_level=result.denoise_level,
                )
                success_count += 1
            # Intentionally catch per-item errors so batch processing can continue.
            except Exception as exc:  # noqa: BLE001
                item_result = UpscaleBatchItemResult(
                    input_image_path=job.input_image.value if job is not None else current_input_path,
                    output_image_path=output_image_path,
                    scale_factor=job.scale_factor if job is not None else scale_factor,
                    denoise_level=job.denoise_level if job is not None else denoise_level,
                    error=exc,
                )
                failure_count += 1

            item_results.append(item_result)
            if progress_callback is not None:
                progress_callback(item_result, index + 1, total_count)

        return RunUpscaleBatchResult(
            items=tuple(item_results),
            processed_count=len(item_results),
            success_count=success_count,
            failure_count=failure_count,
            total_count=total_count,
        )

    @staticmethod
    def _resolve_output_image_paths(
        output_image_paths: Sequence[Path | str | None] | None,
        total_count: int,
    ) -> list[Path | str | None] | None:
        if output_image_paths is None:
            return None

        resolved_paths = list(output_image_paths)
        if len(resolved_paths) != total_count:
            raise ValueError(
                "output_image_paths length must match input_image_paths length in batch execution."
            )

        return resolved_paths
