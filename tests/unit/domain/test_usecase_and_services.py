import unittest
from pathlib import Path

from src.domain.ports.image_storage_port import ImageStoragePort
from src.domain.ports.upscale_engine_port import UpscaleEnginePort
from src.domain.services.output_path_service import build_default_output_path
from src.domain.usecase.run_upscale_usecase import (
    RunUpscaleCommand,
    RunUpscaleUseCase,
)
from src.domain.entities.upscale_job import UpscaleJob
from src.domain.value_objects.image_path import InputImagePath, OutputImagePath
from src.domain.value_objects.scale_factor import ScaleFactor


class FakeUpscaleEngine(UpscaleEnginePort):
    def __init__(self) -> None:
        self.calls: list[tuple[Path, int, Path]] = []

    def upscale(self, job: UpscaleJob) -> bytes:
        self.calls.append((job.input_image.value, job.scale_factor.value, job.output_image.value))
        return b"upscaled-image"


class FakeImageStorage(ImageStoragePort):
    def __init__(self) -> None:
        self.calls: list[tuple[bytes, Path]] = []

    def save(self, image_bytes: bytes, output_image: OutputImagePath) -> None:
        self.calls.append((image_bytes, output_image.value))


class TestDomainServicesAndUseCase(unittest.TestCase):
    def test_build_default_output_path_appends_scale_suffix(self) -> None:
        output = build_default_output_path(
            InputImagePath(Path("C:/images/cat.png")),
            scale_factor=ScaleFactor(4),
        )
        self.assertEqual(output.value, Path("C:/images/cat_x4.png"))

    def test_run_upscale_usecase_runs_engine_and_saves_output(self) -> None:
        fake_engine = FakeUpscaleEngine()
        fake_storage = FakeImageStorage()
        usecase = RunUpscaleUseCase(upscale_engine=fake_engine, image_storage=fake_storage)

        result = usecase.execute(
            RunUpscaleCommand(
                input_image_path=Path("C:/images/input.png"),
                output_image_path=Path("C:/images/output.png"),
                scale_factor=2,
            )
        )

        self.assertEqual(
            fake_engine.calls,
            [(Path("C:/images/input.png"), 2, Path("C:/images/output.png"))],
        )
        self.assertEqual(fake_storage.calls, [(b"upscaled-image", Path("C:/images/output.png"))])
        self.assertEqual(result.scale_factor.value, 2)
        self.assertEqual(result.output_image_path.value, Path("C:/images/output.png"))


if __name__ == "__main__":
    unittest.main()
