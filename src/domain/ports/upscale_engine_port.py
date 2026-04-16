from typing import Protocol

from src.domain.value_objects.image_path import InputImagePath, OutputImagePath
from src.domain.value_objects.scale_factor import ScaleFactor


class UpscaleEnginePort(Protocol):
    """Boundary for image upscaling implementation."""

    def upscale(
        self,
        input_image: InputImagePath,
        scale_factor: ScaleFactor,
        output_image: OutputImagePath,
    ) -> bytes:
        """Run upscaling and return encoded image bytes."""
