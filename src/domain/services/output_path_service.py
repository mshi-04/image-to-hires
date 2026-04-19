from pathlib import Path

from src.domain.value_objects.denoise_level import DenoiseLevel
from src.domain.value_objects.image_path import InputImagePath, OutputImagePath
from src.domain.value_objects.scale_factor import ScaleFactor


def build_default_output_path(
    input_image: InputImagePath,
    scale_factor: ScaleFactor,
    denoise_level: DenoiseLevel,
) -> OutputImagePath:
    """Build a deterministic output file path for a single upscale job."""

    stem = input_image.value.stem
    parent = input_image.value.parent
    suffix = input_image.value.suffix.lower()
    denoise_label = str(denoise_level.value)
    output_path = parent / f"{stem}-denoise{denoise_label}x-up{scale_factor.value}x{suffix}"
    return OutputImagePath(Path(output_path))


def resolve_output_image_path(
    input_image: InputImagePath,
    scale_factor: ScaleFactor,
    denoise_level: DenoiseLevel,
    output_image_path: Path | str | None,
) -> OutputImagePath:
    """Resolve output path with explicit path precedence."""

    if output_image_path is not None:
        requested_output_path = Path(output_image_path)
        if requested_output_path.suffix == "":
            return OutputImagePath(requested_output_path)
        normalized_output_path = requested_output_path.with_suffix(input_image.value.suffix.lower())
        return OutputImagePath(normalized_output_path)

    return build_default_output_path(input_image, scale_factor, denoise_level)
