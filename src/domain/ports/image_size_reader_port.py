from typing import Protocol

from src.domain.value_objects.image_path import InputImagePath
from src.domain.value_objects.image_size import ImageSize


class ImageSizeReaderPort(Protocol):
    """Boundary for reading image dimensions from input files."""

    def read_size(self, input_image: InputImagePath) -> ImageSize:
        """Read width and height for the provided input image."""
