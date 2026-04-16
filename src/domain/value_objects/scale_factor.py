from dataclasses import dataclass

from src.domain.exceptions import UnsupportedScaleFactorError


SUPPORTED_SCALE_FACTORS = frozenset({2, 3, 4})


@dataclass(frozen=True)
class ScaleFactor:
    """Immutable scale factor for upscaling."""

    value: int

    def __post_init__(self) -> None:
        if self.value not in SUPPORTED_SCALE_FACTORS:
            supported_values = ", ".join(str(value) for value in sorted(SUPPORTED_SCALE_FACTORS))
            raise UnsupportedScaleFactorError(
                f"Unsupported scale factor: {self.value}. Supported values are {supported_values}."
            )
