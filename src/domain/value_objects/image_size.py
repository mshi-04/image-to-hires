from dataclasses import dataclass


@dataclass(frozen=True)
class ImageSize:
    """Immutable width/height pair for an input image."""

    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError(f"Image dimensions must be positive. Got: {self.width}x{self.height}.")
