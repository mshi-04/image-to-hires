import os
import tempfile
from pathlib import Path

from src.domain.ports.image_storage_port import ImageStoragePort
from src.domain.value_objects.image_path import OutputImagePath


class FileImageStorage(ImageStoragePort):
    """Persist encoded image bytes to the local file system."""

    def save(self, image_bytes: bytes, output_image: OutputImagePath) -> None:
        if not image_bytes:
            raise ValueError("image_bytes must not be empty.")

        output_path = Path(output_image.value)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        temp_path: str | None = None
        try:
            temp_fd, temp_path = tempfile.mkstemp(
                dir=str(output_path.parent),
                prefix=f".{output_path.name}.",
                suffix=".tmp",
            )

            with os.fdopen(temp_fd, "wb") as temp_file:
                temp_file.write(image_bytes)
                temp_file.flush()
                os.fsync(temp_file.fileno())

            os.replace(temp_path, output_path)
        except Exception:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
            raise
