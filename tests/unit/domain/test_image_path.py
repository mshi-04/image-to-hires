import unittest
from pathlib import Path

from src.domain.exceptions import UnsupportedImageFormatError
from src.domain.value_objects.image_path import InputImagePath, OutputImagePath


class TestImagePath(unittest.TestCase):
    def test_input_image_path_accepts_supported_extension(self) -> None:
        image_path = InputImagePath(Path("C:/tmp/sample.JPG"))
        self.assertEqual(image_path.value.suffix, ".JPG")

    def test_input_image_path_rejects_unsupported_extension(self) -> None:
        with self.assertRaises(UnsupportedImageFormatError):
            InputImagePath(Path("C:/tmp/sample.bmp"))

    def test_output_image_path_accepts_webp(self) -> None:
        # Arrange
        path = Path("C:/tmp/output.webp")

        # Act
        output_path = OutputImagePath(path)

        # Assert
        self.assertEqual(output_path.value, path)

    def test_output_image_path_rejects_unsupported_extension(self) -> None:
        # Arrange
        unsupported_path = Path("C:/tmp/output.bmp")

        # Act / Assert
        with self.assertRaises(UnsupportedImageFormatError):
            OutputImagePath(unsupported_path)


if __name__ == "__main__":
    unittest.main()
