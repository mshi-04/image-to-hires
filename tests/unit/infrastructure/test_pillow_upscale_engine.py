import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from src.domain.value_objects.image_path import InputImagePath, OutputImagePath
from src.domain.value_objects.scale_factor import ScaleFactor
from src.domain.entities.upscale_job import UpscaleJob
from src.infrastructure.inference.pillow_upscale_engine import PillowUpscaleEngine

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ModuleNotFoundError:
    Image = None
    PIL_AVAILABLE = False


@unittest.skipUnless(PIL_AVAILABLE, "Pillow is required for PillowUpscaleEngine tests.")
class TestPillowUpscaleEngine(unittest.TestCase):
    def test_upscale_returns_png_bytes_when_output_is_png(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "input.png"
            Image.new("RGB", (3, 2), color=(0, 128, 255)).save(input_path, format="PNG")
            output_path = Path(tmp_dir) / "output.png"

            engine = PillowUpscaleEngine()
            result_bytes = engine.upscale(UpscaleJob(
                InputImagePath(input_path),
                OutputImagePath(output_path),
                ScaleFactor(4),
            ))

            self.assertTrue(result_bytes)
            with Image.open(BytesIO(result_bytes)) as output_image:
                self.assertEqual(output_image.size, (12, 8))
                self.assertEqual(output_image.format, "PNG")

    def test_upscale_returns_jpeg_bytes_when_output_is_jpg(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "input.png"
            Image.new("RGB", (2, 2), color=(255, 128, 0)).save(input_path, format="PNG")
            output_path = Path(tmp_dir) / "output.jpg"

            engine = PillowUpscaleEngine()
            result_bytes = engine.upscale(UpscaleJob(
                InputImagePath(input_path),
                OutputImagePath(output_path),
                ScaleFactor(2),
            ))

            with Image.open(BytesIO(result_bytes)) as output_image:
                self.assertEqual(output_image.size, (4, 4))
                self.assertEqual(output_image.format, "JPEG")

    def test_upscale_raises_for_missing_input_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing_path = Path(tmp_dir) / "missing.png"
            output_path = Path(tmp_dir) / "output.png"
            engine = PillowUpscaleEngine()

            with self.assertRaises(FileNotFoundError):
                engine.upscale(UpscaleJob(
                    InputImagePath(missing_path),
                    OutputImagePath(output_path),
                    ScaleFactor(2),
                ))

    def test_upscale_applies_exif_orientation_before_resizing(self) -> None:
        if not hasattr(Image, "Exif"):
            self.skipTest("Current Pillow version does not support Image.Exif.")

        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "oriented.jpg"
            output_path = Path(tmp_dir) / "output.jpg"

            exif = Image.Exif()
            exif[274] = 6
            Image.new("RGB", (2, 3), color=(10, 20, 30)).save(input_path, format="JPEG", exif=exif)

            engine = PillowUpscaleEngine()
            result_bytes = engine.upscale(UpscaleJob(
                InputImagePath(input_path),
                OutputImagePath(output_path),
                ScaleFactor(2),
            ))

            with Image.open(BytesIO(result_bytes)) as output_image:
                self.assertEqual(output_image.size, (6, 4))
                self.assertEqual(output_image.format, "JPEG")


if __name__ == "__main__":
    unittest.main()
