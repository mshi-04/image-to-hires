"""Image I/O adapters for the infrastructure layer."""

from src.infrastructure.image_io.file_image_storage import FileImageStorage
from src.infrastructure.image_io.pillow_image_size_reader import PillowImageSizeReader

__all__ = ["FileImageStorage", "PillowImageSizeReader"]

