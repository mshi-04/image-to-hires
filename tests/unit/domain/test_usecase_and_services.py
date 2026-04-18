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
    def __init__(
        self,
        fail_input_paths: set[Path] | None = None,
        runtime_error: Exception | None = None,
    ) -> None:
        self.calls: list[tuple[Path, int, int, Path]] = []
        self.fail_input_paths = fail_input_paths or set()
        self.runtime_error = runtime_error
        self.ready_calls = 0

    def ensure_runtime_ready(self) -> None:
        self.ready_calls += 1
        if self.runtime_error is not None:
            raise self.runtime_error

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
        self.assertEqual(output.value, Path("C:/images/cat-denoise2x-up4x.webp"))

    def test_build_default_output_path_normalizes_uppercase_extension_to_lowercase(self) -> None:
        # Arrange
        input_image = InputImagePath(Path("C:/images/cat.JPG"))
        scale_factor = ScaleFactor(3)
        denoise_level = DenoiseLevel(1)

        # Act
        output = build_default_output_path(input_image, scale_factor, denoise_level)

        # Assert
        self.assertEqual(output.value, Path("C:/images/cat-denoise1x-up3x.jpg"))

    def test_build_default_output_path_forces_webp_extension_when_requested(self) -> None:
        # Arrange
        input_image = InputImagePath(Path("C:/images/cat.jpg"))
        scale_factor = ScaleFactor(4)
        denoise_level = DenoiseLevel(2)

        # Act
        output = build_default_output_path(
            input_image,
            scale_factor,
            denoise_level,
            "webp_lossless",
        )

        # Assert
        self.assertEqual(output.value, Path("C:/images/cat-denoise2x-up4x.webp"))

    def test_build_default_output_path_uses_minus_one_label_when_denoise_is_minus_one(self) -> None:
        # Arrange
        input_image = InputImagePath(Path("C:/images/cat.png"))
        scale_factor = ScaleFactor(2)
        denoise_level = DenoiseLevel(-1)

        # Act
        output = build_default_output_path(input_image, scale_factor, denoise_level)

        # Assert
        self.assertEqual(output.value, Path("C:/images/cat-denoise-1x-up2x.png"))

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
        self.assertEqual(fake_engine.ready_calls, 0)
        self.assertEqual(fake_storage.calls, [(b"upscaled-image", Path("C:/images/output.png"))])
        self.assertEqual(result.scale_factor.value, 2)
        self.assertEqual(result.denoise_level.value, 1)
        self.assertEqual(result.output_image_path.value, Path("C:/images/output.png"))

    def test_run_upscale_usecase_uses_webp_lossless_default_output_when_mode_is_webp_lossless(self) -> None:
        # Arrange
        fake_engine = FakeUpscaleEngine()
        fake_storage = FakeImageStorage()
        usecase = RunUpscaleUseCase(upscale_engine=fake_engine, image_storage=fake_storage)

        # Act
        result = usecase.execute(
            RunUpscaleCommand(
                input_image_path=Path("C:/images/input.jpg"),
                scale_factor=3,
                denoise_level=0,
                output_format_mode="webp_lossless",
            )
        )

        # Assert
        self.assertEqual(
            fake_engine.calls,
            [(Path("C:/images/input.jpg"), 3, 0, Path("C:/images/input-denoise0x-up3x.webp"))],
        )
        self.assertEqual(
            fake_storage.calls,
            [(b"upscaled-image", Path("C:/images/input-denoise0x-up3x.webp"))],
        )
        self.assertEqual(result.output_image_path.value, Path("C:/images/input-denoise0x-up3x.webp"))

    def test_run_upscale_usecase_forces_explicit_output_to_webp_when_mode_is_webp_lossless(self) -> None:
        # Arrange
        fake_engine = FakeUpscaleEngine()
        fake_storage = FakeImageStorage()
        usecase = RunUpscaleUseCase(upscale_engine=fake_engine, image_storage=fake_storage)

        # Act
        result = usecase.execute(
            RunUpscaleCommand(
                input_image_path=Path("C:/images/input.jpg"),
                output_image_path=Path("C:/images/custom-output.png"),
                scale_factor=2,
                denoise_level=0,
                output_format_mode="webp_lossless",
            )
        )

        # Assert
        self.assertEqual(
            fake_engine.calls,
            [(Path("C:/images/input.jpg"), 2, 0, Path("C:/images/custom-output.webp"))],
        )
        self.assertEqual(
            fake_storage.calls,
            [(b"upscaled-image", Path("C:/images/custom-output.webp"))],
        )
        self.assertEqual(result.output_image_path.value, Path("C:/images/custom-output.webp"))

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

        item_started_events: list[tuple[Path, int, int]] = []

        def item_started_callback(input_path: Path, processed_count: int, total_count: int) -> None:
            item_started_events.append((input_path, processed_count, total_count))

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
            item_started_callback=item_started_callback,
            progress_callback=progress_callback,
        )

        # Assert
        self.assertEqual(result.total_count, 3)
        self.assertEqual(result.processed_count, 3)
        self.assertEqual(result.success_count, 2)
        self.assertEqual(result.failure_count, 1)
        self.assertEqual(fake_engine.ready_calls, 1)

        self.assertEqual(
            [item.output_image_path for item in result.items],
            [
                Path("C:/images/ok-denoise3x-up2x.png"),
                Path("C:/images/fail-denoise3x-up2x.png"),
                Path("C:/images/ok2-denoise3x-up2x.webp"),
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
                    Path("C:/images/ok-denoise3x-up2x.png"),
                ),
                (
                    Path("C:/images/fail.png"),
                    2,
                    3,
                    Path("C:/images/fail-denoise3x-up2x.png"),
                ),
                (
                    Path("C:/images/ok2.webp"),
                    2,
                    3,
                    Path("C:/images/ok2-denoise3x-up2x.webp"),
                ),
            ],
        )
        self.assertEqual(
            fake_storage.calls,
            [
                (b"upscaled-image", Path("C:/images/ok-denoise3x-up2x.png")),
                (b"upscaled-image", Path("C:/images/ok2-denoise3x-up2x.webp")),
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
        self.assertEqual(
            item_started_events,
            [
                (Path("C:/images/ok.png"), 1, 3),
                (Path("C:/images/fail.png"), 2, 3),
                (Path("C:/images/ok2.webp"), 3, 3),
            ],
        )

    def test_run_upscale_batch_usecase_forces_webp_output_for_all_items_when_requested(self) -> None:
        # Arrange
        input_paths = [
            Path("C:/images/ok.png"),
            Path("C:/images/fail.jpg"),
            Path("C:/images/ok2.webp"),
        ]
        fake_engine = FakeUpscaleEngine(fail_input_paths={Path("C:/images/fail.jpg")})
        fake_storage = FakeImageStorage()
        usecase = RunUpscaleBatchUseCase(upscale_engine=fake_engine, image_storage=fake_storage)

        # Act
        result = usecase.execute(
            RunUpscaleBatchCommand(
                input_image_paths=input_paths,
                scale_factor=2,
                denoise_level=3,
                output_format_mode="webp_lossless",
            )
        )

        # Assert
        self.assertEqual(result.total_count, 3)
        self.assertEqual(result.processed_count, 3)
        self.assertEqual(result.success_count, 2)
        self.assertEqual(result.failure_count, 1)
        self.assertEqual(fake_engine.ready_calls, 1)
        self.assertEqual(
            [item.output_image_path for item in result.items],
            [
                Path("C:/images/ok-denoise3x-up2x.webp"),
                Path("C:/images/fail-denoise3x-up2x.webp"),
                Path("C:/images/ok2-denoise3x-up2x.webp"),
            ],
        )
        self.assertEqual(
            fake_engine.calls,
            [
                (
                    Path("C:/images/ok.png"),
                    2,
                    3,
                    Path("C:/images/ok-denoise3x-up2x.webp"),
                ),
                (
                    Path("C:/images/fail.jpg"),
                    2,
                    3,
                    Path("C:/images/fail-denoise3x-up2x.webp"),
                ),
                (
                    Path("C:/images/ok2.webp"),
                    2,
                    3,
                    Path("C:/images/ok2-denoise3x-up2x.webp"),
                ),
            ],
        )
        self.assertEqual(
            fake_storage.calls,
            [
                (b"upscaled-image", Path("C:/images/ok-denoise3x-up2x.webp")),
                (b"upscaled-image", Path("C:/images/ok2-denoise3x-up2x.webp")),
            ],
        )

    def test_run_upscale_batch_usecase_forces_explicit_outputs_to_webp_when_mode_is_webp_lossless(self) -> None:
        # Arrange
        fake_engine = FakeUpscaleEngine()
        fake_storage = FakeImageStorage()
        usecase = RunUpscaleBatchUseCase(upscale_engine=fake_engine, image_storage=fake_storage)

        # Act
        result = usecase.execute(
            RunUpscaleBatchCommand(
                input_image_paths=[Path("C:/images/a.png"), Path("C:/images/b.jpg")],
                output_image_paths=[Path("C:/out/a.png"), Path("C:/out/b.jpeg")],
                scale_factor=2,
                denoise_level=1,
                output_format_mode="webp_lossless",
            )
        )

        # Assert
        self.assertEqual(result.success_count, 2)
        self.assertEqual(
            [item.output_image_path for item in result.items],
            [Path("C:/out/a.webp"), Path("C:/out/b.webp")],
        )
        self.assertEqual(
            fake_engine.calls,
            [
                (Path("C:/images/a.png"), 2, 1, Path("C:/out/a.webp")),
                (Path("C:/images/b.jpg"), 2, 1, Path("C:/out/b.webp")),
            ],
        )

    def test_run_upscale_batch_usecase_stops_before_queue_when_runtime_is_not_ready(self) -> None:
        # Arrange
        fake_engine = FakeUpscaleEngine(runtime_error=RuntimeError("runtime missing"))
        fake_storage = FakeImageStorage()
        usecase = RunUpscaleBatchUseCase(upscale_engine=fake_engine, image_storage=fake_storage)

        # Act / Assert
        with self.assertRaisesRegex(RuntimeError, "runtime missing"):
            usecase.execute(
                RunUpscaleBatchCommand(
                    input_image_paths=[Path("C:/images/one.png"), Path("C:/images/two.png")],
                    scale_factor=2,
                    denoise_level=0,
                )
            )

        self.assertEqual(fake_engine.ready_calls, 1)
        self.assertEqual(fake_engine.calls, [])
        self.assertEqual(fake_storage.calls, [])

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
