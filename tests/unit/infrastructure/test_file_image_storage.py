import tempfile
import unittest
from unittest import mock
from pathlib import Path

from src.domain.value_objects.image_path import OutputImagePath
from src.infrastructure.image_io.file_image_storage import FileImageStorage


class TestFileImageStorage(unittest.TestCase):
    def test_save_writes_bytes_to_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "nested" / "result.png"
            storage = FileImageStorage()

            storage.save(b"encoded-image", OutputImagePath(output_path))

            self.assertTrue(output_path.exists())
            self.assertEqual(output_path.read_bytes(), b"encoded-image")

    def test_save_raises_for_empty_image_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "result.png"
            storage = FileImageStorage()

            with self.assertRaises(ValueError):
                storage.save(b"", OutputImagePath(output_path))

    def test_save_keeps_existing_file_when_replace_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "result.png"
            output_path.write_bytes(b"old-image")
            storage = FileImageStorage()

            with mock.patch(
                "src.infrastructure.image_io.file_image_storage.os.replace",
                side_effect=OSError("replace failed"),
            ):
                with self.assertRaises(OSError):
                    storage.save(b"new-image", OutputImagePath(output_path))

            self.assertEqual(output_path.read_bytes(), b"old-image")
            temp_files = list(output_path.parent.glob(f".{output_path.name}.*.tmp"))
            self.assertEqual(temp_files, [])


if __name__ == "__main__":
    unittest.main()
