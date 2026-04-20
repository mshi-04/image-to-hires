from dataclasses import dataclass
from pathlib import Path

from src.domain.entities.upscale_job import UpscaleJob
from src.domain.ports.image_size_reader_port import ImageSizeReaderPort
from src.domain.ports.image_storage_port import ImageStoragePort
from src.domain.ports.upscale_engine_port import UpscaleEnginePort
from src.domain.services.auto_scale_service import resolve_scale_factor_for_image
from src.domain.services.output_path_service import resolve_output_image_path
from src.domain.value_objects.denoise_level import DenoiseLevel
from src.domain.value_objects.image_path import InputImagePath, OutputImagePath
from src.domain.value_objects.scale_factor import ScaleFactor


@dataclass(frozen=True)
class RunUpscaleCommand:
    """Input payload for the upscaling use case."""

    input_image_path: Path | str
    scale_factor: int
    denoise_level: int
    auto_sizing_enabled: bool = False
    output_image_path: Path | str | None = None


@dataclass(frozen=True)
class RunUpscaleResult:
    """Output payload for the upscaling use case."""

    output_image_path: OutputImagePath
    scale_factor: ScaleFactor
    denoise_level: DenoiseLevel


class RunUpscaleUseCase:
    """Execute the upscaling flow for a single image."""

    def __init__(
        self,
        upscale_engine: UpscaleEnginePort,
        image_storage: ImageStoragePort,
        image_size_reader: ImageSizeReaderPort | None = None,
    ) -> None:
        self._upscale_engine = upscale_engine
        self._image_storage = image_storage
        self._image_size_reader = image_size_reader

    def execute(self, command: RunUpscaleCommand) -> RunUpscaleResult:
        input_image = InputImagePath(Path(command.input_image_path))
        fallback_scale_factor = ScaleFactor(command.scale_factor)
        scale_factor = self._resolve_scale_factor(
            input_image=input_image,
            fallback_scale_factor=fallback_scale_factor,
            auto_sizing_enabled=command.auto_sizing_enabled,
        )
        denoise_level = DenoiseLevel(command.denoise_level)
        output_image = resolve_output_image_path(
            input_image=input_image,
            scale_factor=scale_factor,
            denoise_level=denoise_level,
            output_image_path=command.output_image_path,
        )

        job = UpscaleJob(
            input_image=input_image,
            output_image=output_image,
            scale_factor=scale_factor,
            denoise_level=denoise_level,
        )

        generated_artifact = self._upscale_engine.upscale(job)
        self._image_storage.save(generated_artifact, job.output_image)

        return RunUpscaleResult(
            output_image_path=job.output_image,
            scale_factor=job.scale_factor,
            denoise_level=job.denoise_level,
        )

    def _resolve_scale_factor(
        self,
        input_image: InputImagePath,
        fallback_scale_factor: ScaleFactor,
        auto_sizing_enabled: bool,
    ) -> ScaleFactor:
        if not auto_sizing_enabled:
            return fallback_scale_factor

        if self._image_size_reader is None:
            raise RuntimeError("Image size reader is required when auto sizing is enabled.")

        image_size = self._image_size_reader.read_size(input_image)
        return resolve_scale_factor_for_image(image_size, fallback_scale_factor)
