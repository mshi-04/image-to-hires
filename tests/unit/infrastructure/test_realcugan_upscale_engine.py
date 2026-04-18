import tempfile
import unittest
from io import BytesIO
from pathlib import Path
import subprocess
from unittest import mock

from src.domain.entities.upscale_job import UpscaleJob
from src.domain.value_objects.denoise_level import DenoiseLevel
from src.domain.value_objects.image_path import InputImagePath, OutputImagePath
from src.domain.value_objects.scale_factor import ScaleFactor
from src.infrastructure.inference.realcugan_upscale_engine import RealCuganUpscaleEngine

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ModuleNotFoundError:
    Image = None
    PIL_AVAILABLE = False


@unittest.skipUnless(PIL_AVAILABLE, "Pillow is required for RealCuganUpscaleEngine tests.")
class TestRealCuganUpscaleEngine(unittest.TestCase):
    # ---- helpers ----

    @staticmethod
    def _make_stub_runtime(tmp_path: Path) -> tuple[Path, Path]:
        """Create stub executable and models directory under tmp_path."""
        executable = tmp_path / "realcugan-ncnn-vulkan.exe"
        model_dir = tmp_path / "models"
        executable.write_bytes(b"stub")
        model_dir.mkdir(parents=True, exist_ok=True)
        return executable, model_dir

    @staticmethod
    def _make_engine_with_stub(tmp_path: Path) -> tuple["RealCuganUpscaleEngine", Path, Path]:
        """Return an engine pre-configured with stub runtime under tmp_path."""
        executable, model_dir = TestRealCuganUpscaleEngine._make_stub_runtime(tmp_path)
        engine = RealCuganUpscaleEngine(
            realcugan_executable=executable,
            realcugan_models_dir=model_dir,
        )
        return engine, executable, model_dir

    # ---- tests ----

    def test_ensure_runtime_ready_resolves_repo_root_paths(self) -> None:
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir) / "repo"
            repo_executable = repo_root / "bin" / "realcugan" / "realcugan-ncnn-vulkan.exe"
            repo_models_dir = repo_root / "models" / "realcugan" / "models-se"
            repo_executable.parent.mkdir(parents=True, exist_ok=True)
            repo_models_dir.mkdir(parents=True, exist_ok=True)
            repo_executable.write_bytes(b"stub")
            (repo_models_dir / "model.bin").write_bytes(b"stub")

            engine = RealCuganUpscaleEngine()

            with (
                mock.patch.object(engine, "_get_executable_parent", return_value=Path(tmp_dir) / "exe-parent"),
                mock.patch.object(engine, "_get_repo_root", return_value=repo_root),
                mock.patch.object(engine, "_get_current_working_directory", return_value=Path(tmp_dir) / "cwd"),
            ):
                # Act
                engine.ensure_runtime_ready()

            # Assert
            self.assertEqual(engine._realcugan_executable, repo_executable)
            self.assertEqual(engine._realcugan_models_dir, repo_models_dir)

    def test_ensure_work_directory_uses_project_tmp_folder(self) -> None:
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_path = Path(tmp_dir)
            engine = RealCuganUpscaleEngine(prefer_realcugan=False)

            with mock.patch.object(engine, "_get_current_working_directory", return_value=base_path):
                # Act
                work_directory = engine._ensure_work_directory()

            # Assert
            expected_root = (base_path / "tmp" / "realcugan-work").resolve(strict=False)
            self.assertEqual(work_directory.parent, expected_root)
            self.assertTrue(work_directory.is_dir())
            self.assertTrue(work_directory.name)

    def test_ensure_work_directory_isolated_per_engine_instance(self) -> None:
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_path = Path(tmp_dir)
            first = RealCuganUpscaleEngine(prefer_realcugan=False)
            second = RealCuganUpscaleEngine(prefer_realcugan=False)

            with (
                mock.patch.object(first, "_get_current_working_directory", return_value=base_path),
                mock.patch.object(second, "_get_current_working_directory", return_value=base_path),
            ):
                # Act
                first_dir = first._ensure_work_directory()
                second_dir = second._ensure_work_directory()

            # Assert
            expected_root = (base_path / "tmp" / "realcugan-work").resolve(strict=False)
            self.assertNotEqual(first_dir, second_dir)
            self.assertEqual(first_dir.parent, expected_root)
            self.assertEqual(second_dir.parent, expected_root)

    def test_ensure_runtime_ready_prefers_executable_parent_before_repo_root(self) -> None:
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            executable_parent = tmp_path / "dist" / "image-to-hires"
            exe_runtime = executable_parent / "bin" / "realcugan" / "realcugan-ncnn-vulkan.exe"
            exe_models_dir = executable_parent / "models" / "realcugan" / "models-se"
            repo_root = tmp_path / "repo"
            repo_runtime = repo_root / "bin" / "realcugan" / "realcugan-ncnn-vulkan.exe"
            repo_models = repo_root / "models" / "realcugan" / "models-se"

            exe_runtime.parent.mkdir(parents=True, exist_ok=True)
            exe_models_dir.mkdir(parents=True, exist_ok=True)
            repo_runtime.parent.mkdir(parents=True, exist_ok=True)
            repo_models.mkdir(parents=True, exist_ok=True)

            exe_runtime.write_bytes(b"exe-parent")
            repo_runtime.write_bytes(b"repo-root")
            (exe_models_dir / "model.bin").write_bytes(b"exe-parent")
            (repo_models / "model.bin").write_bytes(b"repo-root")

            engine = RealCuganUpscaleEngine()

            with (
                mock.patch.object(engine, "_get_executable_parent", return_value=executable_parent),
                mock.patch.object(engine, "_get_repo_root", return_value=repo_root),
                mock.patch.object(engine, "_get_current_working_directory", return_value=tmp_path / "cwd"),
            ):
                # Act
                engine.ensure_runtime_ready()

            # Assert
            self.assertEqual(engine._realcugan_executable, exe_runtime)
            self.assertEqual(engine._realcugan_models_dir, exe_models_dir)

    def test_ensure_runtime_ready_resolves_pyinstaller_internal_directory(self) -> None:
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            pyinstaller_root = tmp_path / "dist" / "image-to-hires" / "_internal"
            executable = pyinstaller_root / "bin" / "realcugan" / "realcugan-ncnn-vulkan.exe"
            models_dir = pyinstaller_root / "models" / "realcugan" / "models-se"
            executable.parent.mkdir(parents=True, exist_ok=True)
            models_dir.mkdir(parents=True, exist_ok=True)
            executable.write_bytes(b"stub")
            (models_dir / "model.bin").write_bytes(b"stub")

            engine = RealCuganUpscaleEngine()

            with (
                mock.patch.object(engine, "_get_executable_parent", return_value=tmp_path / "dist" / "image-to-hires"),
                mock.patch.object(engine, "_get_pyinstaller_contents_directory", return_value=pyinstaller_root),
                mock.patch.object(engine, "_get_repo_root", return_value=tmp_path / "repo"),
                mock.patch.object(engine, "_get_current_working_directory", return_value=tmp_path / "cwd"),
            ):
                # Act
                engine.ensure_runtime_ready()

            # Assert
            self.assertEqual(engine._realcugan_executable, executable)
            self.assertEqual(engine._realcugan_models_dir, models_dir)

    def test_upscale_returns_png_bytes_when_output_is_png(self) -> None:
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "input.png"
            Image.new("RGB", (3, 2), color=(0, 128, 255)).save(input_path, format="PNG")
            output_path = Path(tmp_dir) / "output.png"
            engine = RealCuganUpscaleEngine(prefer_realcugan=False)

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
            engine = RealCuganUpscaleEngine(prefer_realcugan=False)

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
            engine = RealCuganUpscaleEngine(prefer_realcugan=False)

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

    def test_upscale_saves_webp_lossless_when_output_is_webp(self) -> None:
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "input.png"
            Image.new("RGB", (3, 3), color=(20, 30, 40)).save(input_path, format="PNG")
            output_path = Path(tmp_dir) / "output.webp"
            engine = RealCuganUpscaleEngine(prefer_realcugan=False)
            captured_save_options: dict[str, object] = {}
            original_save = Image.Image.save

            def capture_save(image_self, fp, *args, **params):  # noqa: ANN001, ANN002, ANN003
                image_format = args[0] if args else params.get("format")
                save_params = params.copy()
                save_params.pop("format", None)
                if image_format == "WEBP":
                    captured_save_options["format"] = image_format
                    captured_save_options["params"] = save_params
                return original_save(image_self, fp, *args, **params)

            # Act
            with mock.patch.object(Image.Image, "save", new=capture_save):
                result_bytes = engine.upscale(
                    UpscaleJob(
                        input_image=InputImagePath(input_path),
                        output_image=OutputImagePath(output_path),
                        scale_factor=ScaleFactor(3),
                        denoise_level=DenoiseLevel(0),
                    )
                )

            # Assert
            self.assertEqual(captured_save_options["format"], "WEBP")
            self.assertEqual(captured_save_options["params"], {"lossless": True, "quality": 100})
            with Image.open(BytesIO(result_bytes)) as output_image:
                self.assertEqual(output_image.size, (9, 9))
                self.assertEqual(output_image.format, "WEBP")

    def test_upscale_raises_for_missing_input_path(self) -> None:
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing_path = Path(tmp_dir) / "missing.png"
            output_path = Path(tmp_dir) / "output.png"
            engine = RealCuganUpscaleEngine(prefer_realcugan=False)

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
            engine = RealCuganUpscaleEngine(prefer_realcugan=False)

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

    def test_upscale_raises_when_realcugan_runtime_is_missing(self) -> None:
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            input_path = tmp_path / "input.png"
            output_path = tmp_path / "output.png"
            Image.new("RGB", (2, 2), color=(100, 120, 140)).save(input_path, format="PNG")
            engine = RealCuganUpscaleEngine()

            with (
                mock.patch.object(engine, "_get_executable_parent", return_value=tmp_path / "exe-parent"),
                mock.patch.object(engine, "_get_repo_root", return_value=tmp_path / "repo-root"),
                mock.patch.object(engine, "_get_current_working_directory", return_value=tmp_path / "cwd"),
            ):
                # Act / Assert
                with self.assertRaisesRegex(RuntimeError, "Checked executable paths:"):
                    engine.upscale(
                        UpscaleJob(
                            input_image=InputImagePath(input_path),
                            output_image=OutputImagePath(output_path),
                            scale_factor=ScaleFactor(2),
                            denoise_level=DenoiseLevel(0),
                        )
                    )

                with self.assertRaisesRegex(RuntimeError, "models\\\\realcugan\\\\models-se"):
                    engine.ensure_runtime_ready()

    def test_ensure_runtime_ready_is_cached_after_success(self) -> None:
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir) / "repo"
            executable = repo_root / "bin" / "realcugan" / "realcugan-ncnn-vulkan.exe"
            models_dir = repo_root / "models" / "realcugan" / "models-se"
            executable.parent.mkdir(parents=True, exist_ok=True)
            models_dir.mkdir(parents=True, exist_ok=True)
            executable.write_bytes(b"stub")
            (models_dir / "model.bin").write_bytes(b"stub")

            engine = RealCuganUpscaleEngine()

            with (
                mock.patch.object(engine, "_get_executable_parent", return_value=Path(tmp_dir) / "exe-parent"),
                mock.patch.object(engine, "_get_repo_root", return_value=repo_root),
                mock.patch.object(engine, "_get_current_working_directory", return_value=Path(tmp_dir) / "cwd"),
            ):
                # Act
                engine.ensure_runtime_ready()
                executable.unlink()
                engine.ensure_runtime_ready()

            # Assert
            self.assertTrue(engine._runtime_ready)

    def test_upscale_uses_realcugan_runner_when_runtime_is_available(self) -> None:
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            input_path = tmp_path / "input.png"
            output_path = tmp_path / "output.png"
            Image.new("RGB", (2, 2), color=(100, 120, 140)).save(input_path, format="PNG")
            engine, _, _ = self._make_engine_with_stub(tmp_path)

            def fake_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
                output_file = Path(command[command.index("-o") + 1])
                Image.new("RGB", (4, 4), color=(10, 20, 30)).save(output_file, format="PNG")
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

            with mock.patch.object(engine, "_run_realcugan", side_effect=fake_runner) as runner:
                # Act
                result_bytes = engine.upscale(
                    UpscaleJob(
                        input_image=InputImagePath(input_path),
                        output_image=OutputImagePath(output_path),
                        scale_factor=ScaleFactor(2),
                        denoise_level=DenoiseLevel(-1),
                    )
                )

            # Assert
            runner.assert_called_once()
            command = runner.call_args.args[0]

            s_index = command.index("-s")
            self.assertEqual(command[s_index + 1], "2")

            n_index = command.index("-n")
            self.assertEqual(command[n_index + 1], "-1")

            j_index = command.index("-j")
            self.assertEqual(command[j_index + 1], "4:4:4")

            t_index = command.index("-t")
            self.assertEqual(command[t_index + 1], "0")

            with Image.open(BytesIO(result_bytes)) as output_image:
                self.assertEqual(output_image.size, (4, 4))
                self.assertEqual(output_image.format, "PNG")

    def test_upscale_uses_low_thread_config_for_large_image(self) -> None:
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            input_path = tmp_path / "input.png"
            output_path = tmp_path / "output.png"
            Image.new("RGB", (2000, 1000), color=(100, 120, 140)).save(input_path, format="PNG")
            engine, _, _ = self._make_engine_with_stub(tmp_path)

            def fake_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
                output_file = Path(command[command.index("-o") + 1])
                Image.new("RGB", (4000, 2000), color=(10, 20, 30)).save(output_file, format="PNG")
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

            # Act
            with mock.patch.object(engine, "_run_realcugan", side_effect=fake_runner) as runner:
                engine.upscale(
                    UpscaleJob(
                        input_image=InputImagePath(input_path),
                        output_image=OutputImagePath(output_path),
                        scale_factor=ScaleFactor(2),
                        denoise_level=DenoiseLevel(0),
                    )
                )

            # Assert
            command = runner.call_args.args[0]
            j_index = command.index("-j")
            self.assertEqual(command[j_index + 1], "2:2:2")

    def test_upscale_uses_small_thread_config_for_exact_boundary_image(self) -> None:
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            input_path = tmp_path / "input.png"
            output_path = tmp_path / "output.png"
            # 1024 x 1024 = 1,048,576 pixels (exactly the threshold)
            Image.new("RGB", (1024, 1024), color=(100, 120, 140)).save(input_path, format="PNG")
            engine, _, _ = self._make_engine_with_stub(tmp_path)

            def fake_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
                output_file = Path(command[command.index("-o") + 1])
                Image.new("RGB", (2048, 2048), color=(10, 20, 30)).save(output_file, format="PNG")
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

            # Act
            with mock.patch.object(engine, "_run_realcugan", side_effect=fake_runner) as runner:
                engine.upscale(
                    UpscaleJob(
                        input_image=InputImagePath(input_path),
                        output_image=OutputImagePath(output_path),
                        scale_factor=ScaleFactor(2),
                        denoise_level=DenoiseLevel(0),
                    )
                )

            # Assert
            command = runner.call_args.args[0]
            j_index = command.index("-j")
            self.assertEqual(command[j_index + 1], "4:4:4")

    def test_upscale_uses_low_thread_config_for_just_above_boundary_image(self) -> None:
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            input_path = tmp_path / "input.png"
            output_path = tmp_path / "output.png"
            # 1025 x 1024 = 1,049,600 pixels (just above the threshold)
            Image.new("RGB", (1025, 1024), color=(100, 120, 140)).save(input_path, format="PNG")
            engine, _, _ = self._make_engine_with_stub(tmp_path)

            def fake_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
                output_file = Path(command[command.index("-o") + 1])
                Image.new("RGB", (2050, 2048), color=(10, 20, 30)).save(output_file, format="PNG")
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

            # Act
            with mock.patch.object(engine, "_run_realcugan", side_effect=fake_runner) as runner:
                engine.upscale(
                    UpscaleJob(
                        input_image=InputImagePath(input_path),
                        output_image=OutputImagePath(output_path),
                        scale_factor=ScaleFactor(2),
                        denoise_level=DenoiseLevel(0),
                    )
                )

            # Assert
            command = runner.call_args.args[0]
            j_index = command.index("-j")
            self.assertEqual(command[j_index + 1], "2:2:2")

    def test_upscale_reuses_work_directory_and_cleans_intermediate_files(self) -> None:
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            input_path = tmp_path / "input.png"
            output_path = tmp_path / "output.png"
            Image.new("RGB", (2, 2), color=(100, 120, 140)).save(input_path, format="PNG")
            engine, _, _ = self._make_engine_with_stub(tmp_path)
            output_paths: list[Path] = []

            def fake_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
                output_file = Path(command[command.index("-o") + 1])
                output_paths.append(output_file)
                Image.new("RGB", (4, 4), color=(10, 20, 30)).save(output_file, format="PNG")
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

            # Act
            with mock.patch.object(engine, "_run_realcugan", side_effect=fake_runner):
                engine.upscale(
                    UpscaleJob(
                        input_image=InputImagePath(input_path),
                        output_image=OutputImagePath(output_path),
                        scale_factor=ScaleFactor(2),
                        denoise_level=DenoiseLevel(0),
                    )
                )
                engine.upscale(
                    UpscaleJob(
                        input_image=InputImagePath(input_path),
                        output_image=OutputImagePath(output_path),
                        scale_factor=ScaleFactor(2),
                        denoise_level=DenoiseLevel(0),
                    )
                )

            # Assert
            self.assertEqual(len(output_paths), 2)
            self.assertEqual(output_paths[0].parent, output_paths[1].parent)
            self.assertFalse((output_paths[0].parent / "input.png").exists())
            self.assertFalse((output_paths[0].parent / "output.png").exists())

    def test_upscale_accepts_cmyk_jpeg_input_for_realcugan_path(self) -> None:
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            input_path = tmp_path / "input.jpg"
            output_path = tmp_path / "output.png"
            Image.new("CMYK", (2, 2), color=(0, 128, 128, 0)).save(input_path, format="JPEG")
            engine, _, _ = self._make_engine_with_stub(tmp_path)

            def fake_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
                output_file = Path(command[command.index("-o") + 1])
                Image.new("RGB", (4, 4), color=(10, 20, 30)).save(output_file, format="PNG")
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

            # Act
            with mock.patch.object(engine, "_run_realcugan", side_effect=fake_runner):
                result_bytes = engine.upscale(
                    UpscaleJob(
                        input_image=InputImagePath(input_path),
                        output_image=OutputImagePath(output_path),
                        scale_factor=ScaleFactor(2),
                        denoise_level=DenoiseLevel(-1),
                    )
                )

            # Assert
            with Image.open(BytesIO(result_bytes)) as output_image:
                self.assertEqual(output_image.size, (4, 4))
                self.assertEqual(output_image.format, "PNG")

    def test_upscale_raises_when_realcugan_returns_non_zero(self) -> None:
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            input_path = tmp_path / "input.png"
            output_path = tmp_path / "output.png"
            Image.new("RGB", (2, 2), color=(100, 120, 140)).save(input_path, format="PNG")
            engine, _, _ = self._make_engine_with_stub(tmp_path)

            with mock.patch.object(
                engine,
                "_run_realcugan",
                return_value=subprocess.CompletedProcess(
                    args=["realcugan-ncnn-vulkan.exe"],
                    returncode=1,
                    stdout="",
                    stderr="mock execution error",
                ),
            ):
                # Act / Assert
                with self.assertRaisesRegex(RuntimeError, "Real-CUGAN execution failed"):
                    engine.upscale(
                        UpscaleJob(
                            input_image=InputImagePath(input_path),
                            output_image=OutputImagePath(output_path),
                            scale_factor=ScaleFactor(2),
                            denoise_level=DenoiseLevel(0),
                        )
                    )

    def test_upscale_raises_when_realcugan_finished_without_producing_output_image(self) -> None:
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            input_path = tmp_path / "input.png"
            output_path = tmp_path / "output.png"
            Image.new("RGB", (2, 2), color=(100, 120, 140)).save(input_path, format="PNG")
            engine, _, _ = self._make_engine_with_stub(tmp_path)

            def fake_runner_no_output(command: list[str]) -> subprocess.CompletedProcess[str]:
                # return success but do not create output file
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

            with mock.patch.object(engine, "_run_realcugan", side_effect=fake_runner_no_output):
                # Act / Assert
                with self.assertRaisesRegex(RuntimeError, "Real-CUGAN finished without producing output image."):
                    engine.upscale(
                        UpscaleJob(
                            input_image=InputImagePath(input_path),
                            output_image=OutputImagePath(output_path),
                            scale_factor=ScaleFactor(2),
                            denoise_level=DenoiseLevel(0),
                        )
                    )

    def test_upscale_raises_when_realcugan_timeout_expired(self) -> None:
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            input_path = tmp_path / "input.png"
            output_path = tmp_path / "output.png"
            Image.new("RGB", (2, 2), color=(100, 120, 140)).save(input_path, format="PNG")
            engine, _, _ = self._make_engine_with_stub(tmp_path)

            # _run_realcugan 内部で TimeoutExpired -> RuntimeError に変換するが、
            # _run_realcugan 自体をモックする場合は変換後の RuntimeError を直接 raise する。
            def fake_runner_timeout(command: list[str]) -> subprocess.CompletedProcess[str]:  # noqa: ARG001
                raise RuntimeError("Real-CUGAN execution timed out after 1800 seconds.")

            with mock.patch.object(engine, "_run_realcugan", side_effect=fake_runner_timeout):
                # Act / Assert
                with self.assertRaisesRegex(RuntimeError, "execution timed out after"):
                    engine.upscale(
                        UpscaleJob(
                            input_image=InputImagePath(input_path),
                            output_image=OutputImagePath(output_path),
                            scale_factor=ScaleFactor(2),
                            denoise_level=DenoiseLevel(0),
                        )
                    )

    def test_upscale_composites_alpha_to_white_for_jpeg_output(self) -> None:
        # Arrange
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "transparent.png"
            output_path = Path(tmp_dir) / "output.jpg"
            Image.new("RGBA", (2, 2), color=(0, 0, 0, 0)).save(input_path, format="PNG")
            engine = RealCuganUpscaleEngine(prefer_realcugan=False)

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
