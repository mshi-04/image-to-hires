from typing import Protocol

from src.domain.entities.upscale_job import UpscaleJob


class UpscaleEnginePort(Protocol):
    """Boundary for image upscaling implementation."""

    def ensure_runtime_ready(self) -> None:
        """Validate that the runtime dependencies required for upscaling are available."""

    def upscale(self, job: UpscaleJob) -> bytes:
        """Run upscaling and return encoded image bytes."""
