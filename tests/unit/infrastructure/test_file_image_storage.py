import ctypes
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from src.domain.entities.generated_image_artifact import FileMetadataPreservation, GeneratedImageArtifact
from src.domain.value_objects.image_path import OutputImagePath
from src.infrastructure.image_io.file_image_storage import FileImageStorage


class TestFileImageStorage(unittest.TestCase):
    def test_save_promotes_artifact_to_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_source = Path(tmp_dir) / "work" / "generated.png"
            temp_source.parent.mkdir(parents=True, exist_ok=True)
            temp_source.write_bytes(b"encoded-image")
            output_path = Path(tmp_dir) / "nested" / "result.png"
            storage = FileImageStorage()

            artifact = GeneratedImageArtifact(
                temporary_path=temp_source,
                cleanup=lambda: None,
            )
            storage.save(artifact, OutputImagePath(output_path))

            self.assertTrue(output_path.exists())
            self.assertEqual(output_path.read_bytes(), b"encoded-image")
            self.assertFalse(temp_source.exists())

    def test_save_applies_requested_metadata_preservation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            source_path = Path(tmp_dir) / "input.png"
            source_path.write_bytes(b"source")
            temp_source = Path(tmp_dir) / "work" / "generated.png"
            temp_source.parent.mkdir(parents=True, exist_ok=True)
            temp_source.write_bytes(b"encoded-image")
            output_path = Path(tmp_dir) / "nested" / "result.png"
            storage = FileImageStorage()
            artifact = GeneratedImageArtifact(
                temporary_path=temp_source,
                cleanup=lambda: None,
                metadata_preservation=FileMetadataPreservation(
                    source_path=source_path,
                    preserve_creation_time=True,
                    preserve_modified_time=True,
                ),
            )

            with mock.patch.object(storage, "_apply_preserved_file_metadata") as apply_metadata:
                storage.save(artifact, OutputImagePath(output_path))

            apply_metadata.assert_called_once_with(output_path, artifact.metadata_preservation)

    def test_save_raises_for_missing_artifact_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing_source = Path(tmp_dir) / "work" / "missing.png"
            output_path = Path(tmp_dir) / "result.png"
            storage = FileImageStorage()
            cleanup = mock.Mock()
            artifact = GeneratedImageArtifact(
                temporary_path=missing_source,
                cleanup=cleanup,
            )

            with self.assertRaises(FileNotFoundError):
                storage.save(artifact, OutputImagePath(output_path))

            cleanup.assert_called_once()

    def test_save_keeps_existing_file_when_replace_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_source = Path(tmp_dir) / "work" / "generated.png"
            temp_source.parent.mkdir(parents=True, exist_ok=True)
            temp_source.write_bytes(b"new-image")
            output_path = Path(tmp_dir) / "result.png"
            output_path.write_bytes(b"old-image")
            storage = FileImageStorage()
            cleanup = mock.Mock()
            artifact = GeneratedImageArtifact(
                temporary_path=temp_source,
                cleanup=cleanup,
            )

            with mock.patch(
                "src.infrastructure.image_io.file_image_storage.os.replace",
                side_effect=OSError("replace failed"),
            ):
                with self.assertRaises(OSError):
                    storage.save(artifact, OutputImagePath(output_path))

            self.assertEqual(output_path.read_bytes(), b"old-image")
            cleanup.assert_called_once()

    def test_save_calls_cleanup_after_successful_promote(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_source = Path(tmp_dir) / "work" / "generated.png"
            temp_source.parent.mkdir(parents=True, exist_ok=True)
            temp_source.write_bytes(b"encoded-image")
            output_path = Path(tmp_dir) / "result.png"
            storage = FileImageStorage()
            cleanup = mock.Mock()
            artifact = GeneratedImageArtifact(
                temporary_path=temp_source,
                cleanup=cleanup,
            )

            storage.save(artifact, OutputImagePath(output_path))

            cleanup.assert_called_once()

    def test_save_logs_warning_when_metadata_preservation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_source = Path(tmp_dir) / "work" / "generated.png"
            temp_source.parent.mkdir(parents=True, exist_ok=True)
            temp_source.write_bytes(b"encoded-image")
            output_path = Path(tmp_dir) / "result.png"
            storage = FileImageStorage()
            cleanup = mock.Mock()
            artifact = GeneratedImageArtifact(
                temporary_path=temp_source,
                cleanup=cleanup,
            )

            with self.assertLogs("src.infrastructure.image_io.file_image_storage", level="WARNING") as logs:
                with mock.patch.object(
                    storage,
                    "_apply_preserved_file_metadata",
                    side_effect=OSError("metadata failed"),
                ):
                    storage.save(artifact, OutputImagePath(output_path))

            self.assertTrue(output_path.exists())
            cleanup.assert_called_once()
            self.assertIn("Failed to preserve file metadata", logs.output[0])

    def test_open_file_handle_configures_timestamp_functions(self) -> None:
        storage = FileImageStorage()
        set_file_time = mock.Mock()
        close_handle = mock.Mock()
        create_file = mock.Mock(return_value=ctypes.c_void_p(1234))
        kernel32 = mock.Mock(CreateFileW=create_file, SetFileTime=set_file_time, CloseHandle=close_handle)

        with mock.patch("src.infrastructure.image_io.file_image_storage.ctypes.windll", mock.Mock(kernel32=kernel32), create=True):
            handle = storage._open_file_handle_for_timestamp_write(Path("C:/tmp/output.png"))

        self.assertEqual(handle.value, 1234)
        self.assertIsNotNone(create_file.argtypes)
        self.assertEqual(create_file.restype, ctypes.c_void_p)
        self.assertEqual(len(set_file_time.argtypes), 4)
        self.assertEqual(close_handle.argtypes, [ctypes.c_void_p])


if __name__ == "__main__":
    unittest.main()
