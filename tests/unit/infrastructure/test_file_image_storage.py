import tempfile
import unittest
from unittest import mock
from pathlib import Path

from src.domain.entities.generated_image_artifact import GeneratedImageArtifact
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


if __name__ == "__main__":
    unittest.main()
