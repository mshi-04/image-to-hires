from dataclasses import dataclass

from src.domain.exceptions import UnsupportedDenoiseLevelError


SUPPORTED_DENOISE_LEVELS = frozenset({-1, 0, 1, 2, 3})


@dataclass(frozen=True)
class DenoiseLevel:
    """Immutable denoise level for upscaling."""

    value: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, int) or isinstance(self.value, bool):
            raise UnsupportedDenoiseLevelError(
                f"Denoise level must be an integer. Got: {self.value!r}."
            )

        if self.value not in SUPPORTED_DENOISE_LEVELS:
            supported_values = ", ".join(str(value) for value in sorted(SUPPORTED_DENOISE_LEVELS))
            raise UnsupportedDenoiseLevelError(
                f"Unsupported denoise level: {self.value}. Supported values are {supported_values}."
            )
