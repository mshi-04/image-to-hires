from dataclasses import dataclass
from pathlib import Path

from src.domain.exceptions import UnsupportedImageFormatError


SUPPORTED_INPUT_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".webp"})
SUPPORTED_OUTPUT_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".webp"})


@dataclass(frozen=True)
class InputImagePath:
    """Validated input image path for a single-image upscale flow."""

    value: Path

    def __post_init__(self) -> None:
        path = Path(self.value)
        extension = path.suffix.lower()

        if not extension:
            raise UnsupportedImageFormatError("Input image path must include a file extension.")

        if extension not in SUPPORTED_INPUT_EXTENSIONS:
            supported_values = ", ".join(sorted(SUPPORTED_INPUT_EXTENSIONS))
            raise UnsupportedImageFormatError(
                f"Unsupported input image format: {extension}. Supported values are {supported_values}."
            )

        object.__setattr__(self, "value", path)


@dataclass(frozen=True)
class OutputImagePath:
    """Validated output image path for a single-image upscale flow."""

    value: Path

    def __post_init__(self) -> None:
        path = Path(self.value)
        extension = path.suffix.lower()

        if not extension:
            raise UnsupportedImageFormatError("Output image path must include a file extension.")

        if extension not in SUPPORTED_OUTPUT_EXTENSIONS:
            supported_values = ", ".join(sorted(SUPPORTED_OUTPUT_EXTENSIONS))
            raise UnsupportedImageFormatError(
                f"Unsupported output image format: {extension}. Supported values are {supported_values}."
            )

        object.__setattr__(self, "value", path)
