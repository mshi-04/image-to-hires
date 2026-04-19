import unittest
from pathlib import Path

from src.domain.entities.generated_image_artifact import GeneratedImageArtifact
from src.domain.entities.upscale_job import UpscaleJob
from src.domain.ports.image_storage_port import ImageStoragePort
from src.domain.ports.upscale_engine_port import UpscaleEnginePort
from src.domain.services.output_path_service import build_default_output_path
from src.domain.usecase.run_upscale_batch_usecase import RunUpscaleBatchCommand, RunUpscaleBatchUseCase
from src.domain.usecase.run_upscale_usecase import RunUpscaleCommand, RunUpscaleUseCase
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

    def upscale(self, job: UpscaleJob) -> GeneratedImageArtifact:
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
        artifact_path = job.output_image.value.with_name(
            f"{job.output_image.value.stem}.generated{job.output_image.value.suffix}"
        )
        return GeneratedImageArtifact(temporary_path=artifact_path, cleanup=lambda: None)


class FakeImageStorage(ImageStoragePort):
    def __init__(self) -> None:
        self.calls: list[Path] = []

    def save(self, artifact: GeneratedImageArtifact, output_image: OutputImagePath) -> None:  # noqa: ARG002
        self.calls.append(output_image.value)


class TestDomainServicesAndUseCase(unittest.TestCase):
    @staticmethod
    def _build_usecase() -> tuple[RunUpscaleUseCase, FakeUpscaleEngine, FakeImageStorage]:
        fake_engine = FakeUpscaleEngine()
        fake_storage = FakeImageStorage()
        return RunUpscaleUseCase(fake_engine, fake_storage), fake_engine, fake_storage

    def test_build_default_output_path(self) -> None:
        # Arrange
        cases = [
            ("C:/images/cat.webp", 4, 2, "C:/images/cat-denoise2x-up4x.webp"),
            ("C:/images/cat.JPG", 3, 1, "C:/images/cat-denoise1x-up3x.jpg"),
            ("C:/images/cat.png", 2, -1, "C:/images/cat-denoise-1x-up2x.png"),
        ]

        for input_path, scale, denoise, expected in cases:
            with self.subTest(input_path=input_path, scale=scale, denoise=denoise):
                # Act
                output = build_default_output_path(
                    InputImagePath(Path(input_path)),
                    ScaleFactor(scale),
                    DenoiseLevel(denoise),
                )

                # Assert
                self.assertEqual(output.value, Path(expected))

    def test_run_upscale_usecase_ignores_explicit_output_path_and_uses_default_naming(self) -> None:
        # Arrange
        usecase, fake_engine, fake_storage = self._build_usecase()

        # Act
        result = usecase.execute(
            RunUpscaleCommand(
                input_image_path=Path("C:/images/input.jpg"),
                output_image_path=Path("C:/images/custom-output.png"),
                scale_factor=2,
                denoise_level=0,
            )
        )

        # Assert
        expected_output = Path("C:/images/input-denoise0x-up2x.jpg")
        self.assertEqual(
            fake_engine.calls,
            [(Path("C:/images/input.jpg"), 2, 0, expected_output)],
        )
        self.assertEqual(fake_storage.calls, [expected_output])
        self.assertEqual(result.output_image_path.value, expected_output)

    def test_run_upscale_usecase_builds_default_output_when_output_path_is_none(self) -> None:
        # Arrange
        usecase, fake_engine, fake_storage = self._build_usecase()

        # Act
        result = usecase.execute(
            RunUpscaleCommand(
                input_image_path=Path("C:/images/input.jpeg"),
                output_image_path=None,
                scale_factor=3,
                denoise_level=1,
            )
        )

        # Assert
        expected_output = Path("C:/images/input-denoise1x-up3x.jpeg")
        self.assertEqual(fake_engine.calls, [(Path("C:/images/input.jpeg"), 3, 1, expected_output)])
        self.assertEqual(fake_storage.calls, [expected_output])
        self.assertEqual(result.output_image_path.value, expected_output)

    def test_run_upscale_batch_usecase_continues_when_one_item_fails(self) -> None:
        # Arrange
        input_paths = [Path("C:/images/ok.png"), Path("C:/images/fail.png"), Path("C:/images/ok2.webp")]
        fake_engine = FakeUpscaleEngine(fail_input_paths={Path("C:/images/fail.png")})
        fake_storage = FakeImageStorage()
        usecase = RunUpscaleBatchUseCase(upscale_engine=fake_engine, image_storage=fake_storage)
        progress_events: list[tuple[Path, bool, int, int]] = []
        item_started_events: list[tuple[Path, int, int]] = []

        def item_started_callback(input_path: Path, processed_count: int, total_count: int) -> None:
            item_started_events.append((input_path, processed_count, total_count))

        def progress_callback(item_result, processed_count: int, total_count: int) -> None:  # noqa: ANN001
            progress_events.append(
                (item_result.input_image_path, item_result.is_success, processed_count, total_count)
            )

        # Act
        result = usecase.execute(
            RunUpscaleBatchCommand(input_image_paths=input_paths, scale_factor=2, denoise_level=3),
            item_started_callback=item_started_callback,
            progress_callback=progress_callback,
        )

        # Assert
        self.assertEqual((result.total_count, result.processed_count), (3, 3))
        self.assertEqual((result.success_count, result.failure_count), (2, 1))
        self.assertEqual(fake_engine.ready_calls, 1)
        self.assertEqual(
            [item.output_image_path for item in result.items],
            [
                Path("C:/images/ok-denoise3x-up2x.png"),
                Path("C:/images/fail-denoise3x-up2x.png"),
                Path("C:/images/ok2-denoise3x-up2x.webp"),
            ],
        )
        self.assertEqual(
            fake_storage.calls,
            [Path("C:/images/ok-denoise3x-up2x.png"), Path("C:/images/ok2-denoise3x-up2x.webp")],
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

    def test_run_upscale_batch_usecase_ignores_explicit_output_paths_and_uses_default_naming(self) -> None:
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
            )
        )

        # Assert
        self.assertEqual(result.success_count, 2)
        self.assertEqual(
            fake_engine.calls,
            [
                (Path("C:/images/a.png"), 2, 1, Path("C:/images/a-denoise1x-up2x.png")),
                (Path("C:/images/b.jpg"), 2, 1, Path("C:/images/b-denoise1x-up2x.jpg")),
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

        # Assert
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

    def test_run_upscale_batch_usecase_ignores_empty_output_path_and_uses_default_naming(self) -> None:
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
        self.assertEqual(result.success_count, 1)
        self.assertEqual(result.failure_count, 0)
        self.assertTrue(result.items[0].is_success)
        self.assertEqual(result.items[0].output_image_path, Path("C:/images/one-denoise0x-up2x.png"))

    def test_run_upscale_batch_usecase_skips_runtime_check_when_input_is_empty(self) -> None:
        # Arrange
        fake_engine = FakeUpscaleEngine(runtime_error=RuntimeError("runtime missing"))
        fake_storage = FakeImageStorage()
        usecase = RunUpscaleBatchUseCase(upscale_engine=fake_engine, image_storage=fake_storage)

        # Act
        result = usecase.execute(
            RunUpscaleBatchCommand(
                input_image_paths=[],
                output_image_paths=[],
                scale_factor=2,
                denoise_level=0,
            )
        )

        # Assert
        self.assertEqual(result.total_count, 0)
        self.assertEqual(result.processed_count, 0)
        self.assertEqual(result.success_count, 0)
        self.assertEqual(result.failure_count, 0)
        self.assertEqual(result.items, tuple())
        self.assertEqual(fake_engine.ready_calls, 0)
        self.assertEqual(fake_engine.calls, [])
        self.assertEqual(fake_storage.calls, [])


if __name__ == "__main__":
    unittest.main()
