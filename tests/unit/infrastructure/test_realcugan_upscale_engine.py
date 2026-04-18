import subprocess
import tempfile
import unittest
from pathlib import Path
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
    @staticmethod
    def _make_stub_runtime(tmp_path: Path) -> tuple[Path, Path]:
        executable = tmp_path / "realcugan-ncnn-vulkan.exe"
        model_dir = tmp_path / "models"
        executable.write_bytes(b"stub")
        model_dir.mkdir(parents=True, exist_ok=True)
        return executable, model_dir

    @staticmethod
    def _make_engine_with_stub(tmp_path: Path) -> tuple["RealCuganUpscaleEngine", Path, Path]:
        executable, model_dir = TestRealCuganUpscaleEngine._make_stub_runtime(tmp_path)
        engine = RealCuganUpscaleEngine(
            realcugan_executable=executable,
            realcugan_models_dir=model_dir,
        )
        return engine, executable, model_dir

    @staticmethod
    def _make_job(input_path: Path, output_path: Path, scale: int, denoise: int) -> UpscaleJob:
        return UpscaleJob(
            input_image=InputImagePath(input_path),
            output_image=OutputImagePath(output_path),
            scale_factor=ScaleFactor(scale),
            denoise_level=DenoiseLevel(denoise),
        )

    def _assert_artifact_image(
        self,
        artifact,
        expected_size: tuple[int, int],
        expected_format: str,
    ) -> None:
        try:
            with Image.open(artifact.temporary_path) as output_image:
                self.assertEqual(output_image.size, expected_size)
                self.assertEqual(output_image.format, expected_format)
        finally:
            artifact.cleanup()

    def test_ensure_runtime_ready_resolves_repo_root_paths(self) -> None:
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
                engine.ensure_runtime_ready()

            self.assertEqual(engine._realcugan_executable, repo_executable)
            self.assertEqual(engine._realcugan_models_dir, repo_models_dir)

    def test_ensure_work_directory_uses_output_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_path = Path(tmp_dir)
            engine = RealCuganUpscaleEngine(prefer_realcugan=False)
            output_path = base_path / "outputs" / "result.png"

            with mock.patch.object(engine, "_get_current_working_directory", return_value=base_path):
                work_directory = engine._ensure_work_directory(output_path)

            self.assertEqual(work_directory.parent, output_path.parent.resolve(strict=False))
            self.assertTrue(work_directory.name.startswith(".tmp-realcugan-"))
            self.assertTrue(work_directory.is_dir())

    def test_ensure_work_directory_isolated_per_engine_instance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_path = Path(tmp_dir)
            first = RealCuganUpscaleEngine(prefer_realcugan=False)
            second = RealCuganUpscaleEngine(prefer_realcugan=False)
            output_path = base_path / "outputs" / "result.png"

            with (
                mock.patch.object(first, "_get_current_working_directory", return_value=base_path),
                mock.patch.object(second, "_get_current_working_directory", return_value=base_path),
            ):
                first_dir = first._ensure_work_directory(output_path)
                second_dir = second._ensure_work_directory(output_path)

            self.assertNotEqual(first_dir, second_dir)
            self.assertEqual(first_dir.parent, output_path.parent.resolve(strict=False))
            self.assertEqual(second_dir.parent, output_path.parent.resolve(strict=False))

    def test_ensure_work_directory_falls_back_to_project_tmp_without_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_path = Path(tmp_dir)
            engine = RealCuganUpscaleEngine(prefer_realcugan=False)

            with mock.patch.object(engine, "_get_current_working_directory", return_value=base_path):
                work_directory = engine._ensure_work_directory()

            expected_root = (base_path / "tmp" / "realcugan-work").resolve(strict=False)
            self.assertEqual(work_directory.parent, expected_root)
            self.assertTrue(work_directory.is_dir())

    def test_ensure_work_directory_re_resolves_when_output_parent_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_path = Path(tmp_dir)
            engine = RealCuganUpscaleEngine(prefer_realcugan=False)
            first_output = base_path / "outputs-a" / "result.png"
            second_output = base_path / "outputs-b" / "result.png"

            first_dir = engine._ensure_work_directory(first_output)
            second_dir = engine._ensure_work_directory(second_output)

            self.assertNotEqual(first_dir, second_dir)
            self.assertEqual(second_dir.parent, second_output.parent.resolve(strict=False))
            self.assertTrue(second_dir.is_dir())

    def test_ensure_runtime_ready_prefers_executable_parent_before_repo_root(self) -> None:
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
                engine.ensure_runtime_ready()

            self.assertEqual(engine._realcugan_executable, exe_runtime)
            self.assertEqual(engine._realcugan_models_dir, exe_models_dir)

    def test_ensure_runtime_ready_resolves_pyinstaller_internal_directory(self) -> None:
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
                engine.ensure_runtime_ready()

            self.assertEqual(engine._realcugan_executable, executable)
            self.assertEqual(engine._realcugan_models_dir, models_dir)

    def test_upscale_returns_png_artifact_when_output_is_png(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "input.png"
            Image.new("RGB", (3, 2), color=(0, 128, 255)).save(input_path, format="PNG")
            output_path = Path(tmp_dir) / "output.png"
            engine = RealCuganUpscaleEngine(prefer_realcugan=False)

            artifact = engine.upscale(self._make_job(input_path, output_path, 4, 0))

            self._assert_artifact_image(artifact, (12, 8), "PNG")

    def test_upscale_returns_jpeg_artifact_when_output_is_jpg(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "input.png"
            Image.new("RGB", (2, 2), color=(255, 128, 0)).save(input_path, format="PNG")
            output_path = Path(tmp_dir) / "output.jpg"
            engine = RealCuganUpscaleEngine(prefer_realcugan=False)

            artifact = engine.upscale(self._make_job(input_path, output_path, 2, 0))

            self._assert_artifact_image(artifact, (4, 4), "JPEG")

    def test_upscale_returns_webp_artifact_when_output_is_webp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "input.png"
            Image.new("RGB", (3, 3), color=(20, 30, 40)).save(input_path, format="PNG")
            output_path = Path(tmp_dir) / "output.webp"
            engine = RealCuganUpscaleEngine(prefer_realcugan=False)

            artifact = engine.upscale(self._make_job(input_path, output_path, 3, 0))

            self._assert_artifact_image(artifact, (9, 9), "WEBP")

    def test_upscale_saves_webp_lossless_when_output_is_webp(self) -> None:
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

            with mock.patch.object(Image.Image, "save", new=capture_save):
                artifact = engine.upscale(self._make_job(input_path, output_path, 3, 0))

            self.assertEqual(captured_save_options["format"], "WEBP")
            self.assertEqual(captured_save_options["params"], {"lossless": True, "quality": 100})
            self._assert_artifact_image(artifact, (9, 9), "WEBP")

    def test_upscale_raises_for_missing_input_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing_path = Path(tmp_dir) / "missing.png"
            output_path = Path(tmp_dir) / "output.png"
            engine = RealCuganUpscaleEngine(prefer_realcugan=False)

            with self.assertRaises(FileNotFoundError):
                engine.upscale(self._make_job(missing_path, output_path, 2, 0))

    def test_upscale_applies_exif_orientation_before_resizing(self) -> None:
        if not hasattr(Image, "Exif"):
            self.skipTest("Current Pillow version does not support Image.Exif.")

        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "oriented.jpg"
            output_path = Path(tmp_dir) / "output.jpg"
            exif = Image.Exif()
            exif[274] = 6
            Image.new("RGB", (2, 3), color=(10, 20, 30)).save(input_path, format="JPEG", exif=exif)
            engine = RealCuganUpscaleEngine(prefer_realcugan=False)

            artifact = engine.upscale(self._make_job(input_path, output_path, 2, 0))

            self._assert_artifact_image(artifact, (6, 4), "JPEG")

    def test_upscale_raises_when_realcugan_runtime_is_missing(self) -> None:
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
                with self.assertRaisesRegex(RuntimeError, "Checked executable paths:"):
                    engine.upscale(self._make_job(input_path, output_path, 2, 0))

                with self.assertRaisesRegex(RuntimeError, "models\\\\realcugan\\\\models-se"):
                    engine.ensure_runtime_ready()

    def test_ensure_runtime_ready_is_cached_after_success(self) -> None:
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
                engine.ensure_runtime_ready()
                executable.unlink()
                engine.ensure_runtime_ready()

            self.assertTrue(engine._runtime_ready)

    def test_upscale_uses_realcugan_runner_when_runtime_is_available(self) -> None:
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
                artifact = engine.upscale(self._make_job(input_path, output_path, 2, -1))

            runner.assert_called_once()
            command = runner.call_args.args[0]
            self.assertEqual(command[command.index("-s") + 1], "2")
            self.assertEqual(command[command.index("-n") + 1], "-1")
            self.assertEqual(command[command.index("-j") + 1], "4:4:4")
            self.assertEqual(command[command.index("-t") + 1], "0")
            self._assert_artifact_image(artifact, (4, 4), "PNG")

    def test_upscale_uses_low_thread_config_for_large_image(self) -> None:
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

            with mock.patch.object(engine, "_run_realcugan", side_effect=fake_runner) as runner:
                artifact = engine.upscale(self._make_job(input_path, output_path, 2, 0))
            try:
                self.assertEqual(runner.call_args.args[0][runner.call_args.args[0].index("-j") + 1], "2:2:2")
            finally:
                artifact.cleanup()

    def test_upscale_uses_small_thread_config_for_exact_boundary_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            input_path = tmp_path / "input.png"
            output_path = tmp_path / "output.png"
            Image.new("RGB", (1024, 1024), color=(100, 120, 140)).save(input_path, format="PNG")
            engine, _, _ = self._make_engine_with_stub(tmp_path)

            def fake_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
                output_file = Path(command[command.index("-o") + 1])
                Image.new("RGB", (2048, 2048), color=(10, 20, 30)).save(output_file, format="PNG")
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

            with mock.patch.object(engine, "_run_realcugan", side_effect=fake_runner) as runner:
                artifact = engine.upscale(self._make_job(input_path, output_path, 2, 0))
            try:
                self.assertEqual(runner.call_args.args[0][runner.call_args.args[0].index("-j") + 1], "4:4:4")
            finally:
                artifact.cleanup()

    def test_upscale_uses_low_thread_config_for_just_above_boundary_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            input_path = tmp_path / "input.png"
            output_path = tmp_path / "output.png"
            Image.new("RGB", (1025, 1024), color=(100, 120, 140)).save(input_path, format="PNG")
            engine, _, _ = self._make_engine_with_stub(tmp_path)

            def fake_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
                output_file = Path(command[command.index("-o") + 1])
                Image.new("RGB", (2050, 2048), color=(10, 20, 30)).save(output_file, format="PNG")
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

            with mock.patch.object(engine, "_run_realcugan", side_effect=fake_runner) as runner:
                artifact = engine.upscale(self._make_job(input_path, output_path, 2, 0))
            try:
                self.assertEqual(runner.call_args.args[0][runner.call_args.args[0].index("-j") + 1], "2:2:2")
            finally:
                artifact.cleanup()

    def test_upscale_reuses_work_directory_and_cleans_intermediate_files(self) -> None:
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

            with mock.patch.object(engine, "_run_realcugan", side_effect=fake_runner):
                first_artifact = engine.upscale(self._make_job(input_path, output_path, 2, 0))
                first_artifact.cleanup()
                second_artifact = engine.upscale(self._make_job(input_path, output_path, 2, 0))
                second_artifact.cleanup()

            self.assertEqual(len(output_paths), 2)
            self.assertEqual(output_paths[0].parent, output_paths[1].parent)
            self.assertFalse(output_paths[0].exists())
            self.assertFalse(output_paths[1].exists())

    def test_upscale_accepts_cmyk_jpeg_input_for_realcugan_path(self) -> None:
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

            with mock.patch.object(engine, "_run_realcugan", side_effect=fake_runner):
                artifact = engine.upscale(self._make_job(input_path, output_path, 2, -1))

            self._assert_artifact_image(artifact, (4, 4), "PNG")

    def test_upscale_raises_when_realcugan_returns_non_zero(self) -> None:
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
                with self.assertRaisesRegex(RuntimeError, "Real-CUGAN execution failed"):
                    engine.upscale(self._make_job(input_path, output_path, 2, 0))

    def test_upscale_raises_when_realcugan_finished_without_producing_output_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            input_path = tmp_path / "input.png"
            output_path = tmp_path / "output.png"
            Image.new("RGB", (2, 2), color=(100, 120, 140)).save(input_path, format="PNG")
            engine, _, _ = self._make_engine_with_stub(tmp_path)

            def fake_runner_no_output(command: list[str]) -> subprocess.CompletedProcess[str]:
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

            with mock.patch.object(engine, "_run_realcugan", side_effect=fake_runner_no_output):
                with self.assertRaisesRegex(RuntimeError, "Real-CUGAN finished without producing output image."):
                    engine.upscale(self._make_job(input_path, output_path, 2, 0))

    def test_upscale_raises_when_realcugan_timeout_expired(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            input_path = tmp_path / "input.png"
            output_path = tmp_path / "output.png"
            Image.new("RGB", (2, 2), color=(100, 120, 140)).save(input_path, format="PNG")
            engine, _, _ = self._make_engine_with_stub(tmp_path)

            def fake_runner_timeout(command: list[str]) -> subprocess.CompletedProcess[str]:  # noqa: ARG001
                raise RuntimeError("Real-CUGAN execution timed out after 1800 seconds.")

            with mock.patch.object(engine, "_run_realcugan", side_effect=fake_runner_timeout):
                with self.assertRaisesRegex(RuntimeError, "execution timed out after"):
                    engine.upscale(self._make_job(input_path, output_path, 2, 0))

    def test_upscale_composites_alpha_to_white_for_jpeg_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "transparent.png"
            output_path = Path(tmp_dir) / "output.jpg"
            Image.new("RGBA", (2, 2), color=(0, 0, 0, 0)).save(input_path, format="PNG")
            engine = RealCuganUpscaleEngine(prefer_realcugan=False)

            artifact = engine.upscale(self._make_job(input_path, output_path, 2, 0))
            try:
                with Image.open(artifact.temporary_path) as output_image:
                    self.assertEqual(output_image.format, "JPEG")
                    pixel = output_image.getpixel((0, 0))
                    self.assertGreaterEqual(pixel[0], 240)
                    self.assertGreaterEqual(pixel[1], 240)
                    self.assertGreaterEqual(pixel[2], 240)
            finally:
                artifact.cleanup()

    def test_upscale_realcugan_png_output_skips_post_encode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            input_path = tmp_path / "input.png"
            output_path = tmp_path / "output.png"
            Image.new("RGB", (2, 2), color=(1, 2, 3)).save(input_path, format="PNG")
            engine, _, _ = self._make_engine_with_stub(tmp_path)

            def fake_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
                output_file = Path(command[command.index("-o") + 1])
                Image.new("RGB", (4, 4), color=(10, 20, 30)).save(output_file, format="PNG")
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

            with (
                mock.patch.object(engine, "_run_realcugan", side_effect=fake_runner),
                mock.patch.object(engine, "_encode_image_to_temporary_path") as encode,
            ):
                artifact = engine.upscale(self._make_job(input_path, output_path, 2, 0))

            encode.assert_not_called()
            self._assert_artifact_image(artifact, (4, 4), "PNG")

    def test_upscale_realcugan_jpeg_output_encodes_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            input_path = tmp_path / "input.png"
            output_path = tmp_path / "output.jpg"
            Image.new("RGB", (2, 2), color=(1, 2, 3)).save(input_path, format="PNG")
            engine, _, _ = self._make_engine_with_stub(tmp_path)

            def fake_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
                output_file = Path(command[command.index("-o") + 1])
                Image.new("RGB", (4, 4), color=(10, 20, 30)).save(output_file, format="PNG")
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

            with (
                mock.patch.object(engine, "_run_realcugan", side_effect=fake_runner),
                mock.patch.object(
                    engine,
                    "_encode_image_to_temporary_path",
                    wraps=engine._encode_image_to_temporary_path,
                ) as encode,
            ):
                artifact = engine.upscale(self._make_job(input_path, output_path, 2, 0))

            encode.assert_called_once()
            self.assertEqual(encode.call_args.kwargs["output_format"], "JPEG")
            self._assert_artifact_image(artifact, (4, 4), "JPEG")

    def test_destructor_does_not_remove_returned_artifact_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "input.png"
            output_path = Path(tmp_dir) / "output.png"
            Image.new("RGB", (2, 2), color=(255, 0, 0)).save(input_path, format="PNG")
            engine = RealCuganUpscaleEngine(prefer_realcugan=False)

            artifact = engine.upscale(self._make_job(input_path, output_path, 2, 0))
            try:
                engine.__del__()
                self.assertTrue(Path(artifact.temporary_path).exists())
            finally:
                artifact.cleanup()


if __name__ == "__main__":
    unittest.main()
