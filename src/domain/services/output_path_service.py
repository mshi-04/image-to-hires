from pathlib import Path
from typing import Literal

from src.domain.value_objects.denoise_level import DenoiseLevel
from src.domain.value_objects.image_path import InputImagePath, OutputImagePath
from src.domain.value_objects.scale_factor import ScaleFactor

OutputFormatMode = Literal["keep_input", "webp_lossless"]


def build_default_output_path(
    input_image: InputImagePath,
    scale_factor: ScaleFactor,
    denoise_level: DenoiseLevel,
    output_format_mode: OutputFormatMode = "keep_input",
) -> OutputImagePath:
    """Build a deterministic output file path for a single upscale job."""

    stem = input_image.value.stem
    parent = input_image.value.parent
    suffix = _resolve_output_suffix(input_image, output_format_mode)
    denoise_label = str(denoise_level.value)
    output_path = parent / f"{stem}-denoise{denoise_label}x-up{scale_factor.value}x{suffix}"
    return OutputImagePath(Path(output_path))


def _resolve_output_suffix(input_image: InputImagePath, output_format_mode: OutputFormatMode) -> str:
    if output_format_mode == "keep_input":
        return input_image.value.suffix.lower()
    if output_format_mode == "webp_lossless":
        return ".webp"

    raise ValueError(f"Unsupported output format mode: {output_format_mode}")
