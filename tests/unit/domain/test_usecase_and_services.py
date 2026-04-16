import unittest
from pathlib import Path

from src.domain.entities.upscale_job import UpscaleJob
from src.domain.ports.image_storage_port import ImageStoragePort
from src.domain.ports.upscale_engine_port import UpscaleEnginePort
from src.domain.services.output_path_service import build_default_output_path
from src.domain.usecase.run_upscale_batch_usecase import (
    RunUpscaleBatchCommand,
    RunUpscaleBatchUseCase,
)
from src.domain.usecase.run_upscale_usecase import (
    RunUpscaleCommand,
    RunUpscaleUseCase,
)
from src.domain.exceptions import UnsupportedImageFormatError
from src.domain.value_objects.denoise_level import DenoiseLevel
from src.domain.value_objects.image_path import InputImagePath, OutputImagePath
from src.domain.value_objects.scale_factor import ScaleFactor


class FakeUpscaleEngine(UpscaleEnginePort):
    def __init__(self, fail_input_paths: set[Path] | None = None) -> None:
        self.calls: list[tuple[Path, int, int, Path]] = []
        self.fail_input_paths = fail_input_paths or set()

    def upscale(self, job: UpscaleJob) -> bytes:
        self.calls.append(
            (
                job.input_image.value,
                job.scale_factor.value,
                job.denoise_level.value,
                job.output_image.value,
            )
        )
        if job.input_image.value in self.fail_input_paths:
            raise RuntimeError("failed to upscale")
        return b"upscaled-image"


class FakeImageStorage(ImageStoragePort):
    def __init__(self) -> None:
        self.calls: list[tuple[bytes, Path]] = []

    def save(self, image_bytes: bytes, output_image: OutputImagePath) -> None:
        self.calls.append((image_bytes, output_image.value))


class TestDomainServicesAndUseCase(unittest.TestCase):
    def test_build_default_output_path_appends_denoise_and_scale_suffix(self) -> None:
        # Arrange
        input_image = InputImagePath(Path("C:/images/cat.webp"))
        scale_factor = ScaleFactor(4)
        denoise_level = DenoiseLevel(2)

        # Act
        output = build_default_output_path(input_image, scale_factor, denoise_level)

        # Assert
        self.assertEqual(output.value, Path("C:/images/cat-denoise(2)x-up(4)x.webp"))

    def test_build_default_output_path_normalizes_uppercase_extension_to_lowercase(self) -> None:
        # Arrange
        input_image = InputImagePath(Path("C:/images/cat.JPG"))
        scale_factor = ScaleFactor(3)
        denoise_level = DenoiseLevel(1)

        # Act
        output = build_default_output_path(input_image, scale_factor, denoise_level)

        # Assert
        self.assertEqual(output.value, Path("C:/images/cat-denoise(1)x-up(3)x.jpg"))

    def test_run_upscale_usecase_runs_engine_and_saves_output(self) -> None:
        # Arrange
        fake_engine = FakeUpscaleEngine()
        fake_storage = FakeImageStorage()
        usecase = RunUpscaleUseCase(upscale_engine=fake_engine, image_storage=fake_storage)

        # Act
        result = usecase.execute(
            RunUpscaleCommand(
                input_image_path=Path("C:/images/input.png"),
                output_image_path=Path("C:/images/output.png"),
                scale_factor=2,
                denoise_level=1,
            )
        )

        # Assert
        self.assertEqual(
            fake_engine.calls,
            [(Path("C:/images/input.png"), 2, 1, Path("C:/images/output.png"))],
        )
        self.assertEqual(fake_storage.calls, [(b"upscaled-image", Path("C:/images/output.png"))])
        self.assertEqual(result.scale_factor.value, 2)
        self.assertEqual(result.denoise_level.value, 1)
        self.assertEqual(result.output_image_path.value, Path("C:/images/output.png"))

    def test_run_upscale_batch_usecase_continues_when_one_item_fails(self) -> None:
        # Arrange
        input_paths = [
            Path("C:/images/ok.png"),
            Path("C:/images/fail.png"),
            Path("C:/images/ok2.webp"),
        ]
        fake_engine = FakeUpscaleEngine(fail_input_paths={Path("C:/images/fail.png")})
        fake_storage = FakeImageStorage()
        usecase = RunUpscaleBatchUseCase(upscale_engine=fake_engine, image_storage=fake_storage)
        progress_events: list[tuple[Path, bool, int, int]] = []

        def progress_callback(item_result, processed_count: int, total_count: int) -> None:
            progress_events.append(
                (
                    item_result.input_image_path,
                    item_result.is_success,
                    processed_count,
                    total_count,
                )
            )

        # Act
        result = usecase.execute(
            RunUpscaleBatchCommand(
                input_image_paths=input_paths,
                scale_factor=2,
                denoise_level=3,
            ),
            progress_callback=progress_callback,
        )

        # Assert
        self.assertEqual(result.total_count, 3)
        self.assertEqual(result.processed_count, 3)
        self.assertEqual(result.success_count, 2)
        self.assertEqual(result.failure_count, 1)

        self.assertEqual(
            [item.output_image_path for item in result.items],
            [
                Path("C:/images/ok-denoise(3)x-up(2)x.png"),
                Path("C:/images/fail-denoise(3)x-up(2)x.png"),
                Path("C:/images/ok2-denoise(3)x-up(2)x.webp"),
            ],
        )
        self.assertTrue(result.items[0].is_success)
        self.assertFalse(result.items[1].is_success)
        self.assertIsInstance(result.items[1].error, RuntimeError)
        self.assertTrue(result.items[2].is_success)

        self.assertEqual(
            fake_engine.calls,
            [
                (
                    Path("C:/images/ok.png"),
                    2,
                    3,
                    Path("C:/images/ok-denoise(3)x-up(2)x.png"),
                ),
                (
                    Path("C:/images/fail.png"),
                    2,
                    3,
                    Path("C:/images/fail-denoise(3)x-up(2)x.png"),
                ),
                (
                    Path("C:/images/ok2.webp"),
                    2,
                    3,
                    Path("C:/images/ok2-denoise(3)x-up(2)x.webp"),
                ),
            ],
        )
        self.assertEqual(
            fake_storage.calls,
            [
                (b"upscaled-image", Path("C:/images/ok-denoise(3)x-up(2)x.png")),
                (b"upscaled-image", Path("C:/images/ok2-denoise(3)x-up(2)x.webp")),
            ],
        )
        self.assertEqual(
            progress_events,
            [
                (Path("C:/images/ok.png"), True, 1, 3),
                (Path("C:/images/fail.png"), False, 2, 3),
                (Path("C:/images/ok2.webp"), True, 3, 3),
            ],
        )

    def test_run_upscale_batch_usecase_validates_output_path_count(self) -> None:
        # Arrange
        fake_engine = FakeUpscaleEngine()
        fake_storage = FakeImageStorage()
        usecase = RunUpscaleBatchUseCase(upscale_engine=fake_engine, image_storage=fake_storage)

        # Act / Assert
        with self.assertRaises(ValueError):
            usecase.execute(
                RunUpscaleBatchCommand(
                    input_image_paths=[Path("C:/images/one.png"), Path("C:/images/two.png")],
                    output_image_paths=[Path("C:/images/out.png")],
                    scale_factor=2,
                    denoise_level=0,
                )
            )

    def test_run_upscale_batch_usecase_treats_empty_output_path_as_invalid(self) -> None:
        # Arrange
        fake_engine = FakeUpscaleEngine()
        fake_storage = FakeImageStorage()
        usecase = RunUpscaleBatchUseCase(upscale_engine=fake_engine, image_storage=fake_storage)

        # Act
        result = usecase.execute(
            RunUpscaleBatchCommand(
                input_image_paths=[Path("C:/images/one.png")],
                output_image_paths=[""],
                scale_factor=2,
                denoise_level=0,
            )
        )

        # Assert
        self.assertEqual(result.failure_count, 1)
        self.assertFalse(result.items[0].is_success)
        self.assertIsInstance(result.items[0].error, UnsupportedImageFormatError)


if __name__ == "__main__":
    unittest.main()
