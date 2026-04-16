from pathlib import Path

from src.domain.value_objects.image_path import InputImagePath, OutputImagePath
from src.domain.value_objects.scale_factor import ScaleFactor


def build_default_output_path(input_image: InputImagePath, scale_factor: ScaleFactor) -> OutputImagePath:
    """Build a deterministic output file path for a single upscale job."""

    stem = input_image.value.stem
    parent = input_image.value.parent
    output_path = parent / f"{stem}_x{scale_factor.value}.png"
    return OutputImagePath(Path(output_path))
