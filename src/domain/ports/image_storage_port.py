from typing import Protocol

from src.domain.value_objects.image_path import OutputImagePath


class ImageStoragePort(Protocol):
    """Boundary for image persistence implementation."""

    def save(self, image_bytes: bytes, output_image: OutputImagePath) -> None:
        """Save encoded image bytes to the target output path."""
