import unittest
from pathlib import Path

from src.domain.entities.generated_image_artifact import GeneratedImageArtifact
from src.domain.entities.upscale_job import UpscaleJob
from src.domain.ports.image_size_reader_port import ImageSizeReaderPort
from src.domain.ports.image_storage_port import ImageStoragePort
from src.domain.ports.upscale_engine_port import UpscaleEnginePort
from src.domain.services.auto_scale_service import resolve_scale_factor_for_image
from src.domain.services.output_path_service import build_default_output_path
from src.domain.usecase.run_upscale_batch_usecase import RunUpscaleBatchCommand, RunUpscaleBatchUseCase
from src.domain.usecase.run_upscale_usecase import RunUpscaleCommand, RunUpscaleUseCase
from src.domain.value_objects.denoise_level import DenoiseLevel
from src.domain.value_objects.image_path import InputImagePath, OutputImagePath
from src.domain.value_objects.image_size import ImageSize
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


class FakeImageSizeReader(ImageSizeReaderPort):
    def __init__(
        self,
        size_by_path: dict[Path, ImageSize] | None = None,
        fail_input_paths: set[Path] | None = None,
    ) -> None:
        self.size_by_path = size_by_path or {}
        self.fail_input_paths = fail_input_paths or set()

    def read_size(self, input_image: InputImagePath) -> ImageSize:
        if input_image.value in self.fail_input_paths:
            raise RuntimeError("failed to read image size")
        return self.size_by_path.get(input_image.value, ImageSize(width=1000, height=1000))


class TestDomainServicesAndUseCase(unittest.TestCase):
    @staticmethod
    def _build_usecase(
        image_size_reader: FakeImageSizeReader | None = None,
    ) -> tuple[RunUpscaleUseCase, FakeUpscaleEngine, FakeImageStorage]:
        fake_engine = FakeUpscaleEngine()
        fake_storage = FakeImageStorage()
        return (
            RunUpscaleUseCase(fake_engine, fake_storage, image_size_reader=image_size_reader),
            fake_engine,
            fake_storage,
        )

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

    def test_build_default_output_path_trims_gemini_prefix_before_applying_rules(self) -> None:
        # Arrange
        input_path = InputImagePath(Path("C:/images/Gemini_Generated_Image_re0bwkre0bwkre0b.png"))

        # Act
        output_without_suffix = build_default_output_path(
            input_path,
            ScaleFactor(4),
            DenoiseLevel(2),
            append_output_suffix=False,
        )
        output_with_suffix = build_default_output_path(
            input_path,
            ScaleFactor(4),
            DenoiseLevel(2),
            append_output_suffix=True,
        )

        # Assert
        self.assertEqual(output_without_suffix.value, Path("C:/images/re0bwkre0bwkre0b.png"))
        self.assertEqual(
            output_with_suffix.value,
            Path("C:/images/re0bwkre0bwkre0b-denoise2x-up4x.png"),
        )

    def test_build_default_output_path_falls_back_to_suffix_when_disabled_name_would_conflict(self) -> None:
        # Arrange
        input_path = InputImagePath(Path("C:/images/cat.png"))

        # Act
        output = build_default_output_path(
            input_path,
            ScaleFactor(2),
            DenoiseLevel(0),
            append_output_suffix=False,
        )

        # Assert
        self.assertEqual(output.value, Path("C:/images/cat-denoise0x-up2x.png"))

    def test_auto_scale_service_uses_exact_matches_and_otherwise_falls_back(self) -> None:
        # Arrange
        fallback = ScaleFactor(4)
        cases = [
            (ImageSize(width=2752, height=1536), 2),
            (ImageSize(width=1376, height=768), 3),
            (ImageSize(width=1600, height=900), 4),
        ]

        for image_size, expected in cases:
            with self.subTest(image_size=image_size):
                # Act
                actual = resolve_scale_factor_for_image(image_size, fallback)

                # Assert
                self.assertEqual(actual.value, expected)

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
        self.assertEqual(fake_engine.calls, [(Path("C:/images/input.jpg"), 2, 0, expected_output)])
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

    def test_run_upscale_usecase_uses_auto_sizing_exact_match_for_output_naming(self) -> None:
        # Arrange
        input_path = Path("C:/images/input.png")
        image_size_reader = FakeImageSizeReader(
            size_by_path={input_path: ImageSize(width=1376, height=768)},
        )
        usecase, fake_engine, fake_storage = self._build_usecase(image_size_reader=image_size_reader)

        # Act
        result = usecase.execute(
            RunUpscaleCommand(
                input_image_path=input_path,
                scale_factor=4,
                denoise_level=0,
                auto_sizing_enabled=True,
            )
        )

        # Assert
        expected_output = Path("C:/images/input-denoise0x-up3x.png")
        self.assertEqual(fake_engine.calls, [(input_path, 3, 0, expected_output)])
        self.assertEqual(fake_storage.calls, [expected_output])
        self.assertEqual(result.scale_factor.value, 3)

    def test_run_upscale_usecase_falls_back_to_manual_scale_when_auto_size_does_not_match(self) -> None:
        # Arrange
        input_path = Path("C:/images/input.png")
        image_size_reader = FakeImageSizeReader(
            size_by_path={input_path: ImageSize(width=1600, height=900)},
        )
        usecase, fake_engine, fake_storage = self._build_usecase(image_size_reader=image_size_reader)

        # Act
        result = usecase.execute(
            RunUpscaleCommand(
                input_image_path=input_path,
                scale_factor=4,
                denoise_level=-1,
                auto_sizing_enabled=True,
            )
        )

        # Assert
        expected_output = Path("C:/images/input-denoise-1x-up4x.png")
        self.assertEqual(fake_engine.calls, [(input_path, 4, -1, expected_output)])
        self.assertEqual(fake_storage.calls, [expected_output])
        self.assertEqual(result.scale_factor.value, 4)

    def test_run_upscale_usecase_trims_gemini_prefix_when_suffix_is_disabled(self) -> None:
        # Arrange
        usecase, fake_engine, fake_storage = self._build_usecase()
        input_path = Path("C:/images/Gemini_Generated_Image_re0bwkre0bwkre0b.png")

        # Act
        result = usecase.execute(
            RunUpscaleCommand(
                input_image_path=input_path,
                scale_factor=4,
                denoise_level=2,
                append_output_suffix=False,
            )
        )

        # Assert
        expected_output = Path("C:/images/re0bwkre0bwkre0b.png")
        self.assertEqual(fake_engine.calls, [(input_path, 4, 2, expected_output)])
        self.assertEqual(fake_storage.calls, [expected_output])
        self.assertEqual(result.output_image_path.value, expected_output)

    def test_run_upscale_usecase_falls_back_to_suffix_when_suffix_disabled_would_overwrite_input(self) -> None:
        # Arrange
        usecase, fake_engine, fake_storage = self._build_usecase()
        input_path = Path("C:/images/sample.png")

        # Act
        result = usecase.execute(
            RunUpscaleCommand(
                input_image_path=input_path,
                scale_factor=2,
                denoise_level=1,
                append_output_suffix=False,
            )
        )

        # Assert
        expected_output = Path("C:/images/sample-denoise1x-up2x.png")
        self.assertEqual(fake_engine.calls, [(input_path, 2, 1, expected_output)])
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

    def test_run_upscale_batch_usecase_uses_per_item_auto_sizing(self) -> None:
        # Arrange
        input_paths = [
            Path("C:/images/two_x.png"),
            Path("C:/images/three_x.png"),
            Path("C:/images/manual.png"),
        ]
        fake_engine = FakeUpscaleEngine()
        fake_storage = FakeImageStorage()
        image_size_reader = FakeImageSizeReader(
            size_by_path={
                input_paths[0]: ImageSize(width=2752, height=1536),
                input_paths[1]: ImageSize(width=1376, height=768),
                input_paths[2]: ImageSize(width=999, height=999),
            }
        )
        usecase = RunUpscaleBatchUseCase(
            upscale_engine=fake_engine,
            image_storage=fake_storage,
            image_size_reader=image_size_reader,
        )

        # Act
        result = usecase.execute(
            RunUpscaleBatchCommand(
                input_image_paths=input_paths,
                scale_factor=4,
                denoise_level=1,
                auto_sizing_enabled=True,
            )
        )

        # Assert
        self.assertEqual(result.success_count, 3)
        self.assertEqual(
            fake_engine.calls,
            [
                (input_paths[0], 2, 1, Path("C:/images/two_x-denoise1x-up2x.png")),
                (input_paths[1], 3, 1, Path("C:/images/three_x-denoise1x-up3x.png")),
                (input_paths[2], 4, 1, Path("C:/images/manual-denoise1x-up4x.png")),
            ],
        )
        self.assertEqual(
            [item.output_image_path for item in result.items],
            [
                Path("C:/images/two_x-denoise1x-up2x.png"),
                Path("C:/images/three_x-denoise1x-up3x.png"),
                Path("C:/images/manual-denoise1x-up4x.png"),
            ],
        )
        self.assertEqual([item.scale_factor.value for item in result.items], [2, 3, 4])

    def test_run_upscale_batch_usecase_continues_when_image_size_read_fails(self) -> None:
        # Arrange
        input_paths = [Path("C:/images/ok.png"), Path("C:/images/bad.png")]
        fake_engine = FakeUpscaleEngine()
        fake_storage = FakeImageStorage()
        image_size_reader = FakeImageSizeReader(
            size_by_path={input_paths[0]: ImageSize(width=2752, height=1536)},
            fail_input_paths={input_paths[1]},
        )
        usecase = RunUpscaleBatchUseCase(
            upscale_engine=fake_engine,
            image_storage=fake_storage,
            image_size_reader=image_size_reader,
        )

        # Act
        result = usecase.execute(
            RunUpscaleBatchCommand(
                input_image_paths=input_paths,
                scale_factor=4,
                denoise_level=0,
                auto_sizing_enabled=True,
            )
        )

        # Assert
        self.assertEqual(result.success_count, 1)
        self.assertEqual(result.failure_count, 1)
        self.assertTrue(result.items[0].is_success)
        self.assertFalse(result.items[1].is_success)
        self.assertIsInstance(result.items[1].error, RuntimeError)
        self.assertEqual(str(result.items[1].error), "failed to read image size")
        self.assertEqual(result.items[1].input_image_path, input_paths[1])
        self.assertIsNone(result.items[1].output_image_path)
        self.assertEqual(fake_engine.calls, [(input_paths[0], 2, 0, Path("C:/images/ok-denoise0x-up2x.png"))])

    def test_run_upscale_batch_usecase_uses_same_resolved_name_for_failed_item_after_auto_sizing(self) -> None:
        # Arrange
        input_paths = [Path("C:/images/ok.png"), Path("C:/images/fail.png")]
        fake_engine = FakeUpscaleEngine(fail_input_paths={input_paths[1]})
        fake_storage = FakeImageStorage()
        image_size_reader = FakeImageSizeReader(
            size_by_path={
                input_paths[0]: ImageSize(width=2752, height=1536),
                input_paths[1]: ImageSize(width=1376, height=768),
            }
        )
        usecase = RunUpscaleBatchUseCase(
            upscale_engine=fake_engine,
            image_storage=fake_storage,
            image_size_reader=image_size_reader,
        )

        # Act
        result = usecase.execute(
            RunUpscaleBatchCommand(
                input_image_paths=input_paths,
                scale_factor=4,
                denoise_level=0,
                auto_sizing_enabled=True,
                append_output_suffix=True,
            )
        )

        # Assert
        self.assertEqual(
            [item.output_image_path for item in result.items],
            [
                Path("C:/images/ok-denoise0x-up2x.png"),
                Path("C:/images/fail-denoise0x-up3x.png"),
            ],
        )
        self.assertEqual(
            fake_engine.calls,
            [
                (input_paths[0], 2, 0, Path("C:/images/ok-denoise0x-up2x.png")),
                (input_paths[1], 3, 0, Path("C:/images/fail-denoise0x-up3x.png")),
            ],
        )
        self.assertEqual([item.scale_factor.value for item in result.items], [2, 3])

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
