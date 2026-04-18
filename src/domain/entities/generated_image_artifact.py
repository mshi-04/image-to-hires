from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GeneratedImageArtifact:
    """Temporary generated image file that can be promoted to the final destination."""

    temporary_path: Path
    cleanup: Callable[[], None]
