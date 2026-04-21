import ctypes
import os
from pathlib import Path

from src.domain.entities.generated_image_artifact import FileMetadataPreservation, GeneratedImageArtifact
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
            self._apply_preserved_file_metadata(output_path, artifact.metadata_preservation)
        finally:
            artifact.cleanup()

    def _apply_preserved_file_metadata(
        self,
        output_path: Path,
        metadata_preservation: FileMetadataPreservation,
    ) -> None:
        source_path = metadata_preservation.source_path
        if source_path is None:
            return

        source_path = Path(source_path)
        if not source_path.exists():
            return

        if metadata_preservation.preserve_modified_time:
            self._copy_modified_time(source_path, output_path)

        if metadata_preservation.preserve_creation_time:
            self._copy_creation_time(source_path, output_path)

    @staticmethod
    def _copy_modified_time(source_path: Path, output_path: Path) -> None:
        source_stat = source_path.stat()
        output_stat = output_path.stat()
        os.utime(output_path, (output_stat.st_atime, source_stat.st_mtime))

    @staticmethod
    def _copy_creation_time(source_path: Path, output_path: Path) -> None:
        if os.name != "nt":
            return

        creation_timestamp = source_path.stat().st_ctime
        file_handle = FileImageStorage._open_file_handle_for_timestamp_write(output_path)
        try:
            filetime = FileImageStorage._timestamp_to_filetime(creation_timestamp)
            if not ctypes.windll.kernel32.SetFileTime(file_handle, ctypes.byref(filetime), None, None):
                raise OSError("Failed to copy file creation time.")
        finally:
            ctypes.windll.kernel32.CloseHandle(file_handle)

    @staticmethod
    def _open_file_handle_for_timestamp_write(path: Path) -> int:
        create_file = ctypes.windll.kernel32.CreateFileW
        create_file.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
        ]
        create_file.restype = ctypes.c_void_p
        handle = create_file(
            str(path),
            0x0100,  # FILE_WRITE_ATTRIBUTES
            0x00000001 | 0x00000002 | 0x00000004,  # FILE_SHARE_READ | WRITE | DELETE
            None,
            3,  # OPEN_EXISTING
            0x00000080,  # FILE_ATTRIBUTE_NORMAL
            None,
        )
        if handle == ctypes.c_void_p(-1).value:
            raise OSError(f"Failed to open file for timestamp update: {path}")
        return handle

    @staticmethod
    def _timestamp_to_filetime(timestamp: float) -> ctypes.Structure:
        class FILETIME(ctypes.Structure):
            _fields_ = [
                ("dwLowDateTime", ctypes.c_uint32),
                ("dwHighDateTime", ctypes.c_uint32),
            ]

        filetime_value = int(timestamp * 10_000_000) + 116_444_736_000_000_000
        return FILETIME(
            dwLowDateTime=filetime_value & 0xFFFFFFFF,
            dwHighDateTime=(filetime_value >> 32) & 0xFFFFFFFF,
        )
