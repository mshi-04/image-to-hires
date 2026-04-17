import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest import mock

from src.domain.entities.upscale_job import UpscaleJob
from src.domain.value_objects.denoise_level import DenoiseLevel
from src.domain.value_objects.image_path import InputImagePath, OutputImagePath
from src.domain.value_objects.scale_factor import ScaleFactor
from src.infrastructure.inference.pillow_upscale_engine import PillowUpscaleEngine

try:
    from PIL import Image, ImageFilter

    PIL_AVAILABLE = True
except ModuleNotFoundError:
    Image = None
    ImageFilter = None
    PIL_AVAILABLE = False


@unittest.skipUnless(PIL_AVAILABLE, "Pillow is required for PillowUpscaleEngine tests.")
class TestPillowUpscaleEngine(unittest.TestCase):
    def test_upscale_returns_png_bytes_when_output_is_png(self) -> None:
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "input.png"
            Image.new("RGB", (3, 2), color=(0, 128, 255)).save(input_path, format="PNG")
            output_path = Path(tmp_dir) / "output.png"
            engine = PillowUpscaleEngine()

            # Act
            result_bytes = engine.upscale(
                UpscaleJob(
                    input_image=InputImagePath(input_path),
                    output_image=OutputImagePath(output_path),
                    scale_factor=ScaleFactor(4),
                    denoise_level=DenoiseLevel(0),
                )
            )

            # Assert
            self.assertTrue(result_bytes)
            with Image.open(BytesIO(result_bytes)) as output_image:
                self.assertEqual(output_image.size, (12, 8))
                self.assertEqual(output_image.format, "PNG")

    def test_upscale_returns_jpeg_bytes_when_output_is_jpg(self) -> None:
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "input.png"
            Image.new("RGB", (2, 2), color=(255, 128, 0)).save(input_path, format="PNG")
            output_path = Path(tmp_dir) / "output.jpg"
            engine = PillowUpscaleEngine()

            # Act
            result_bytes = engine.upscale(
                UpscaleJob(
                    input_image=InputImagePath(input_path),
                    output_image=OutputImagePath(output_path),
                    scale_factor=ScaleFactor(2),
                    denoise_level=DenoiseLevel(0),
                )
            )

            # Assert
            with Image.open(BytesIO(result_bytes)) as output_image:
                self.assertEqual(output_image.size, (4, 4))
                self.assertEqual(output_image.format, "JPEG")

    def test_upscale_returns_webp_bytes_when_output_is_webp(self) -> None:
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "input.png"
            Image.new("RGB", (3, 3), color=(20, 30, 40)).save(input_path, format="PNG")
            output_path = Path(tmp_dir) / "output.webp"
            engine = PillowUpscaleEngine()

            # Act
            result_bytes = engine.upscale(
                UpscaleJob(
                    input_image=InputImagePath(input_path),
                    output_image=OutputImagePath(output_path),
                    scale_factor=ScaleFactor(3),
                    denoise_level=DenoiseLevel(0),
                )
            )

            # Assert
            with Image.open(BytesIO(result_bytes)) as output_image:
                self.assertEqual(output_image.size, (9, 9))
                self.assertEqual(output_image.format, "WEBP")

    def test_upscale_raises_for_missing_input_path(self) -> None:
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing_path = Path(tmp_dir) / "missing.png"
            output_path = Path(tmp_dir) / "output.png"
            engine = PillowUpscaleEngine()

            # Act / Assert
            with self.assertRaises(FileNotFoundError):
                engine.upscale(
                    UpscaleJob(
                        input_image=InputImagePath(missing_path),
                        output_image=OutputImagePath(output_path),
                        scale_factor=ScaleFactor(2),
                        denoise_level=DenoiseLevel(0),
                    )
                )

    def test_upscale_applies_exif_orientation_before_resizing(self) -> None:
        if not hasattr(Image, "Exif"):
            self.skipTest("Current Pillow version does not support Image.Exif.")

        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "oriented.jpg"
            output_path = Path(tmp_dir) / "output.jpg"
            exif = Image.Exif()
            exif[274] = 6
            Image.new("RGB", (2, 3), color=(10, 20, 30)).save(input_path, format="JPEG", exif=exif)
            engine = PillowUpscaleEngine()

            # Act
            result_bytes = engine.upscale(
                UpscaleJob(
                    input_image=InputImagePath(input_path),
                    output_image=OutputImagePath(output_path),
                    scale_factor=ScaleFactor(2),
                    denoise_level=DenoiseLevel(0),
                )
            )

            # Assert
            with Image.open(BytesIO(result_bytes)) as output_image:
                self.assertEqual(output_image.size, (6, 4))
                self.assertEqual(output_image.format, "JPEG")

    def test_upscale_applies_denoise_prefilter_when_level_is_non_zero(self) -> None:
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "input.png"
            output_path = Path(tmp_dir) / "output.png"
            Image.new("RGB", (2, 2), color=(100, 100, 100)).save(input_path, format="PNG")
            engine = PillowUpscaleEngine()

            with mock.patch("PIL.ImageFilter.MedianFilter", wraps=ImageFilter.MedianFilter) as median_filter:
                # Act
                engine.upscale(
                    UpscaleJob(
                        input_image=InputImagePath(input_path),
                        output_image=OutputImagePath(output_path),
                        scale_factor=ScaleFactor(2),
                        denoise_level=DenoiseLevel(2),
                    )
                )

            # Assert
            median_filter.assert_called_once_with(size=5)

    def test_upscale_skips_denoise_prefilter_when_level_is_zero(self) -> None:
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "input.png"
            output_path = Path(tmp_dir) / "output.png"
            Image.new("RGB", (2, 2), color=(100, 100, 100)).save(input_path, format="PNG")
            engine = PillowUpscaleEngine()

            with mock.patch("PIL.ImageFilter.MedianFilter", wraps=ImageFilter.MedianFilter) as median_filter:
                # Act
                engine.upscale(
                    UpscaleJob(
                        input_image=InputImagePath(input_path),
                        output_image=OutputImagePath(output_path),
                        scale_factor=ScaleFactor(2),
                        denoise_level=DenoiseLevel(0),
                    )
                )

            # Assert
            median_filter.assert_not_called()

    def test_upscale_composites_alpha_to_white_for_jpeg_output(self) -> None:
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "transparent.png"
            output_path = Path(tmp_dir) / "output.jpg"
            Image.new("RGBA", (2, 2), color=(0, 0, 0, 0)).save(input_path, format="PNG")
            engine = PillowUpscaleEngine()

            # Act
            result_bytes = engine.upscale(
                UpscaleJob(
                    input_image=InputImagePath(input_path),
                    output_image=OutputImagePath(output_path),
                    scale_factor=ScaleFactor(2),
                    denoise_level=DenoiseLevel(0),
                )
            )

            # Assert
            with Image.open(BytesIO(result_bytes)) as output_image:
                self.assertEqual(output_image.format, "JPEG")
                pixel = output_image.getpixel((0, 0))
                self.assertGreaterEqual(pixel[0], 240)
                self.assertGreaterEqual(pixel[1], 240)
                self.assertGreaterEqual(pixel[2], 240)


if __name__ == "__main__":
    unittest.main()
