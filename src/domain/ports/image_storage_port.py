from typing import Protocol

from src.domain.entities.generated_image_artifact import GeneratedImageArtifact
from src.domain.value_objects.image_path import OutputImagePath


class ImageStoragePort(Protocol):
    """Boundary for image persistence implementation."""

    def save(self, artifact: GeneratedImageArtifact, output_image: OutputImagePath) -> None:
        """Promote a temporary generated image artifact to the target output path."""
