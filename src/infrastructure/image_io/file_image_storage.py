import os
from pathlib import Path

from src.domain.entities.generated_image_artifact import GeneratedImageArtifact
from src.domain.ports.image_storage_port import ImageStoragePort
from src.domain.value_objects.image_path import OutputImagePath


class FileImageStorage(ImageStoragePort):
    """Promote generated image artifacts to final files on local storage."""

    def save(self, artifact: GeneratedImageArtifact, output_image: OutputImagePath) -> None:
        try:
            temporary_path = Path(artifact.temporary_path)
            if not temporary_path.exists():
                raise FileNotFoundError(f"Generated temporary file was not found: {temporary_path}")

            output_path = Path(output_image.value)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            os.replace(temporary_path, output_path)
        finally:
            artifact.cleanup()
