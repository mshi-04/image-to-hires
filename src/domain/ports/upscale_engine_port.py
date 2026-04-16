from typing import Protocol

from src.domain.entities.upscale_job import UpscaleJob


class UpscaleEnginePort(Protocol):
    """Boundary for image upscaling implementation."""

    def upscale(self, job: UpscaleJob) -> bytes:
        """Run upscaling and return encoded image bytes."""
