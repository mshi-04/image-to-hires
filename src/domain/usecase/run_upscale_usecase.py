from dataclasses import dataclass
from pathlib import Path

from src.domain.entities.upscale_job import UpscaleJob
from src.domain.ports.image_storage_port import ImageStoragePort
from src.domain.ports.upscale_engine_port import UpscaleEnginePort
from src.domain.services.output_path_service import OutputFormatMode, build_default_output_path
from src.domain.value_objects.denoise_level import DenoiseLevel
from src.domain.value_objects.image_path import InputImagePath, OutputImagePath
from src.domain.value_objects.scale_factor import ScaleFactor


@dataclass(frozen=True)
class RunUpscaleCommand:
    """Input payload for the upscaling use case."""

    input_image_path: Path | str
    scale_factor: int
    denoise_level: int
    output_image_path: Path | str | None = None
    output_format_mode: OutputFormatMode = "keep_input"


@dataclass(frozen=True)
class RunUpscaleResult:
    """Output payload for the upscaling use case."""

    output_image_path: OutputImagePath
    scale_factor: ScaleFactor
    denoise_level: DenoiseLevel


class RunUpscaleUseCase:
    """Execute the upscaling flow for a single image."""

    def __init__(self, upscale_engine: UpscaleEnginePort, image_storage: ImageStoragePort) -> None:
        self._upscale_engine = upscale_engine
        self._image_storage = image_storage

    def execute(self, command: RunUpscaleCommand) -> RunUpscaleResult:
        input_image = InputImagePath(Path(command.input_image_path))
        scale_factor = ScaleFactor(command.scale_factor)
        denoise_level = DenoiseLevel(command.denoise_level)

        if command.output_image_path:
            output_path = Path(command.output_image_path)
            if command.output_format_mode == "webp_lossless":
                output_path = output_path.with_suffix(".webp")
            output_image = OutputImagePath(output_path)
        else:
            output_image = build_default_output_path(
                input_image,
                scale_factor,
                denoise_level,
                command.output_format_mode,
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
