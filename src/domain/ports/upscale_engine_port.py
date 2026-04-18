from typing import Protocol

from src.domain.entities.generated_image_artifact import GeneratedImageArtifact
from src.domain.entities.upscale_job import UpscaleJob


class UpscaleEnginePort(Protocol):
    """Boundary for image upscaling implementation."""

    def ensure_runtime_ready(self) -> None:
        """Validate that the runtime dependencies required for upscaling are available."""

    def upscale(self, job: UpscaleJob) -> GeneratedImageArtifact:
        """Run upscaling and return a temporary image artifact."""
