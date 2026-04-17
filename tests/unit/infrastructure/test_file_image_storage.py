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

    def test_save_does_not_call_fsync(self) -> None:
        # technical-design.md の記述「保存時の fsync は使わず〜」に基づく実装であることの確認
        # もし将来的に fsync を復活させる方針に変更される場合は、このテストも修正・削除する
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "result.png"
            storage = FileImageStorage()

            with mock.patch("src.infrastructure.image_io.file_image_storage.os.fsync") as fsync:
                storage.save(b"encoded-image", OutputImagePath(output_path))

            fsync.assert_not_called()


if __name__ == "__main__":
    unittest.main()
