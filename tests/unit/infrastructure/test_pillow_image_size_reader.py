import tempfile
import unittest
from pathlib import Path

try:
    from PIL import Image
except ModuleNotFoundError:
    Image = None
    PIL_AVAILABLE = False
else:
    PIL_AVAILABLE = True

from src.domain.value_objects.image_path import InputImagePath
from src.infrastructure.image_io.pillow_image_size_reader import PillowImageSizeReader


@unittest.skipUnless(PIL_AVAILABLE, "Pillow is required for image size reader tests.")
class TestPillowImageSizeReader(unittest.TestCase):
    def test_read_size_returns_image_dimensions(self) -> None:
        # Arrange
        reader = PillowImageSizeReader()
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = Path(tmpdir) / "sample.png"
            Image.new("RGB", (640, 360), "white").save(image_path)

            # Act
            result = reader.read_size(InputImagePath(image_path))

        # Assert
        self.assertEqual((result.width, result.height), (640, 360))


if __name__ == "__main__":
    unittest.main()
