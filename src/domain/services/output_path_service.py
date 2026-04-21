from pathlib import Path

from src.domain.value_objects.denoise_level import DenoiseLevel
from src.domain.value_objects.image_path import InputImagePath, OutputImagePath
from src.domain.value_objects.scale_factor import ScaleFactor

GEMINI_GENERATED_IMAGE_PREFIX = "Gemini_Generated_Image_"


def _resolve_output_stem(input_image: InputImagePath) -> str:
    original_stem = input_image.value.stem
    if not original_stem.startswith(GEMINI_GENERATED_IMAGE_PREFIX):
        return original_stem

    trimmed_stem = original_stem.removeprefix(GEMINI_GENERATED_IMAGE_PREFIX)
    return trimmed_stem or original_stem


def _paths_conflict(first_path: Path, second_path: Path) -> bool:
    return (
        str(first_path.parent).casefold() == str(second_path.parent).casefold()
        and first_path.name.casefold() == second_path.name.casefold()
    )


def build_default_output_path(
    input_image: InputImagePath,
    scale_factor: ScaleFactor,
    denoise_level: DenoiseLevel,
    append_output_suffix: bool = True,
) -> OutputImagePath:
    """Build a deterministic output file path for a single upscale job."""

    stem = _resolve_output_stem(input_image)
    parent = input_image.value.parent
    suffix = input_image.value.suffix.lower()
    denoise_label = str(denoise_level.value)
    suffix_path = parent / f"{stem}-denoise{denoise_label}x-up{scale_factor.value}x{suffix}"

    if not append_output_suffix:
        plain_path = parent / f"{stem}{suffix}"
        output_path = plain_path if not _paths_conflict(input_image.value, plain_path) else suffix_path
    else:
        output_path = suffix_path

    return OutputImagePath(Path(output_path))


def resolve_output_image_path(
    input_image: InputImagePath,
    scale_factor: ScaleFactor,
    denoise_level: DenoiseLevel,
    append_output_suffix: bool,
    output_image_path: Path | str | None,  # noqa: ARG001
) -> OutputImagePath:
    """Resolve output path using the default filename contract."""

    return build_default_output_path(
        input_image,
        scale_factor,
        denoise_level,
        append_output_suffix=append_output_suffix,
    )
