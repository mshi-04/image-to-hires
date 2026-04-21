from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class FileMetadataPreservation:
    """Describe which source-file metadata should be copied to the final output."""

    source_path: Path | None = None
    preserve_creation_time: bool = False
    preserve_modified_time: bool = False

    @classmethod
    def preserve_timestamps_from(cls, source_path: Path) -> "FileMetadataPreservation":
        return cls(
            source_path=Path(source_path),
            preserve_creation_time=True,
            preserve_modified_time=True,
        )


@dataclass(frozen=True)
class GeneratedImageArtifact:
    """Temporary generated image file that can be promoted to the final destination."""

    temporary_path: Path
    cleanup: Callable[[], None]
    metadata_preservation: FileMetadataPreservation = field(default_factory=FileMetadataPreservation)
