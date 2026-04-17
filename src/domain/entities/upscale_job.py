from dataclasses import dataclass

from src.domain.value_objects.image_path import InputImagePath, OutputImagePath
from src.domain.value_objects.denoise_level import DenoiseLevel
from src.domain.value_objects.scale_factor import ScaleFactor


@dataclass(frozen=True)
class UpscaleJob:
    """A single upscale task handled by the domain layer."""

    input_image: InputImagePath
    output_image: OutputImagePath
    scale_factor: ScaleFactor
    denoise_level: DenoiseLevel
