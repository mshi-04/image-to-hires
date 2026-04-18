import os
import subprocess
import sys
from pathlib import Path
from collections.abc import Callable
from typing import TYPE_CHECKING
from uuid import uuid4

from src.domain.entities.generated_image_artifact import GeneratedImageArtifact
from src.domain.entities.upscale_job import UpscaleJob
from src.domain.ports.upscale_engine_port import UpscaleEnginePort

if TYPE_CHECKING:
    from PIL import Image


class RealCuganUpscaleEngine(UpscaleEnginePort):
    """Upscaler with local Real-CUGAN path and Pillow fallback."""

    _EXECUTABLE_RELATIVE_PATH = Path("bin") / "realcugan" / "realcugan-ncnn-vulkan.exe"
    _MODELS_RELATIVE_PATH = Path("models") / "realcugan" / "models-se"
    # 1024x1024ピクセルを境界として、小さい画像はスレッドを多く(4:4:4)、大きい画像は少なく(2:2:2)割り当てる
    # 大きい画像でスレッド数を増やすとVRAM消費が増大し、並行処理によるオーバーヘッドも大きくなるための経験則
    _THREAD_CONFIG_PIXEL_THRESHOLD = 1_048_576  # 1024x1024 pixels
    _SMALL_IMAGE_THREAD_CONFIG = "4:4:4"
    _LARGE_IMAGE_THREAD_CONFIG = "2:2:2"
    _WORK_DIRECTORY_RELATIVE_PATH = Path("tmp") / "realcugan-work"

    def __init__(
        self,
        realcugan_executable: Path | str | None = None,
        realcugan_models_dir: Path | str | None = None,
        prefer_realcugan: bool = True,
    ) -> None:
        self._prefer_realcugan = prefer_realcugan
        self._configured_realcugan_executable = (
            Path(realcugan_executable) if realcugan_executable is not None else None
        )
        self._configured_realcugan_models_dir = (
            Path(realcugan_models_dir) if realcugan_models_dir is not None else None
        )
        self._realcugan_executable: Path | None = self._configured_realcugan_executable
        self._realcugan_models_dir: Path | None = self._configured_realcugan_models_dir
        self._runtime_ready = False
        self._work_directory: Path | None = None
        self._work_directory_id = f"{os.getpid()}-{uuid4().hex}"

    def ensure_runtime_ready(self) -> None:
        if not self._prefer_realcugan or self._runtime_ready:
            return

        executable_candidates = self._build_candidate_paths(
            configured_path=self._configured_realcugan_executable,
            relative_path=self._EXECUTABLE_RELATIVE_PATH,
        )
        models_candidates = self._build_candidate_paths(
            configured_path=self._configured_realcugan_models_dir,
            relative_path=self._MODELS_RELATIVE_PATH,
        )

        resolved_executable = self._find_first_existing_file(executable_candidates)
        resolved_models_dir = self._find_first_existing_directory(models_candidates)

        if resolved_executable is None or resolved_models_dir is None:
            raise RuntimeError(
                self._build_runtime_missing_message(
                    executable_candidates=executable_candidates,
                    models_candidates=models_candidates,
                )
            )

        self._realcugan_executable = resolved_executable
        self._realcugan_models_dir = resolved_models_dir
        self._runtime_ready = True

    def upscale(self, job: UpscaleJob) -> GeneratedImageArtifact:
        image_path = Path(job.input_image.value)
        if not image_path.exists():
            raise FileNotFoundError(f"Input image file was not found: {image_path}")

        try:
            from PIL import Image, ImageOps
        except ModuleNotFoundError as exc:
            raise RuntimeError("Pillow is required to run RealCuganUpscaleEngine.") from exc

        with Image.open(image_path) as source_image:
            normalized_image = ImageOps.exif_transpose(source_image)
            if job.scale_factor.value == 1:
                return self._convert_without_upscale(normalized_image, job)
            if self._should_use_realcugan():
                self.ensure_runtime_ready()
                return self._upscale_with_realcugan(normalized_image, job)
            return self._upscale_with_pillow(normalized_image, job)

    def _should_use_realcugan(self) -> bool:
        # 将来 GPU 可用性チェック等の判定を加える拡張点として残す。
        return self._prefer_realcugan

    def _build_candidate_paths(self, configured_path: Path | None, relative_path: Path) -> list[Path]:
        candidates: list[Path] = []
        if configured_path is not None:
            candidates.append(configured_path.resolve(strict=False))

        for root in self._get_runtime_search_roots():
            candidates.append((root / relative_path).resolve(strict=False))

        return self._deduplicate_paths(candidates)

    def _get_runtime_search_roots(self) -> list[Path]:
        return self._deduplicate_paths(
            [
                self._get_executable_parent(),
                self._get_pyinstaller_contents_directory(),
                self._get_repo_root(),
                self._get_current_working_directory(),
            ]
        )

    @staticmethod
    def _deduplicate_paths(paths: list[Path]) -> list[Path]:
        deduplicated: list[Path] = []
        seen: set[str] = set()
        for path in paths:
            normalized = str(path).lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            deduplicated.append(path)
        return deduplicated

    @staticmethod
    def _find_first_existing_file(candidates: list[Path]) -> Path | None:
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        return None

    @staticmethod
    def _find_first_existing_directory(candidates: list[Path]) -> Path | None:
        for candidate in candidates:
            if candidate.is_dir():
                return candidate
        return None

    @staticmethod
    def _build_runtime_missing_message(
        executable_candidates: list[Path],
        models_candidates: list[Path],
    ) -> str:
        executable_paths = ", ".join(str(path) for path in executable_candidates)
        model_paths = ", ".join(str(path) for path in models_candidates)
        return (
            "Real-CUGAN runtime is not ready. "
            "Place the executable under bin\\realcugan\\realcugan-ncnn-vulkan.exe "
            "and the models under models\\realcugan\\models-se\\. "
            f"Checked executable paths: {executable_paths}. "
            f"Checked models paths: {model_paths}."
        )

    @staticmethod
    def _get_executable_parent() -> Path:
        return Path(sys.executable).resolve(strict=False).parent

    @staticmethod
    def _get_pyinstaller_contents_directory() -> Path:
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass).resolve(strict=False)
        return Path(sys.executable).resolve(strict=False).parent / "_internal"

    @staticmethod
    def _get_repo_root() -> Path:
        return Path(__file__).resolve().parents[3]

    @staticmethod
    def _get_current_working_directory() -> Path:
        return Path.cwd().resolve(strict=False)

    def _upscale_with_realcugan(self, image: "Image.Image", job: UpscaleJob) -> GeneratedImageArtifact:
        from PIL import Image

        if self._realcugan_executable is None or self._realcugan_models_dir is None:
            raise RuntimeError("Real-CUGAN runtime paths are unresolved.")

        work_directory = self._ensure_work_directory(Path(job.output_image.value))
        operation_id = uuid4().hex
        input_png = work_directory / f"{operation_id}-input.png"
        realcugan_output_png = work_directory / f"{operation_id}-realcugan.png"
        output_extension = Path(job.output_image.value).suffix.lower()
        output_format = self._resolve_output_format(output_extension)
        encoded_output = work_directory / f"{operation_id}-encoded{output_extension}"

        try:
            prepared_input = self._prepare_for_realcugan_png(image)
            prepared_input.save(input_png, format="PNG")

            command = [
                str(self._realcugan_executable),
                "-i", str(input_png),
                "-o", str(realcugan_output_png),
                "-s", str(job.scale_factor.value),
                "-n", str(job.denoise_level.value),
                "-m", str(self._realcugan_models_dir),
                "-t", "0",  # タイルサイズを自動決定させる
                "-j", self._resolve_thread_config(prepared_input),
                "-f", "png",
                # "-x",  # TTAを有効にすると処理時間が数倍に延びるためMVPでは無効化する
            ]
            run_result = self._run_realcugan(command)
            if run_result.returncode != 0:
                stderr = (run_result.stderr or "").strip()
                stdout = (run_result.stdout or "").strip()
                details = stderr or stdout or "No stderr/stdout output."
                raise RuntimeError(f"Real-CUGAN execution failed: {details}")
            if not realcugan_output_png.exists():
                raise RuntimeError("Real-CUGAN finished without producing output image.")

            # keep_input + PNG の場合は Real-CUGAN 出力PNGをそのまま昇格する。
            if output_format == "PNG":
                return GeneratedImageArtifact(
                    temporary_path=realcugan_output_png,
                    cleanup=self._build_cleanup([input_png, realcugan_output_png]),
                )

            with Image.open(realcugan_output_png) as result_image:
                image_to_encode = result_image
                if output_format == "JPEG":
                    image_to_encode = self._prepare_for_jpeg(result_image)
                self._encode_image_to_temporary_path(
                    image=image_to_encode,
                    temporary_path=encoded_output,
                    output_format=output_format,
                )

            return GeneratedImageArtifact(
                temporary_path=encoded_output,
                cleanup=self._build_cleanup([input_png, realcugan_output_png, encoded_output]),
            )
        except Exception:
            self._cleanup_files([input_png, realcugan_output_png, encoded_output])
            raise

    def _upscale_with_pillow(self, image: "Image.Image", job: UpscaleJob) -> GeneratedImageArtifact:
        output_extension = Path(job.output_image.value).suffix.lower()
        output_format = self._resolve_output_format(output_extension)
        upscaled_image = self._resize_with_pillow(image, job.scale_factor.value)

        if output_format == "JPEG":
            upscaled_image = self._prepare_for_jpeg(upscaled_image)

        work_directory = self._ensure_work_directory(Path(job.output_image.value))
        operation_id = uuid4().hex
        encoded_output = work_directory / f"{operation_id}-encoded{output_extension}"
        try:
            self._encode_image_to_temporary_path(
                image=upscaled_image,
                temporary_path=encoded_output,
                output_format=output_format,
            )
            return GeneratedImageArtifact(
                temporary_path=encoded_output,
                cleanup=self._build_cleanup([encoded_output]),
            )
        except Exception:
            self._cleanup_files([encoded_output])
            raise

    def _convert_without_upscale(self, image: "Image.Image", job: UpscaleJob) -> GeneratedImageArtifact:
        output_extension = Path(job.output_image.value).suffix.lower()
        output_format = self._resolve_output_format(output_extension)

        image_to_encode = image
        if output_format == "JPEG":
            image_to_encode = self._prepare_for_jpeg(image)

        work_directory = self._ensure_work_directory(Path(job.output_image.value))
        operation_id = uuid4().hex
        encoded_output = work_directory / f"{operation_id}-encoded{output_extension}"
        try:
            self._encode_image_to_temporary_path(
                image=image_to_encode,
                temporary_path=encoded_output,
                output_format=output_format,
            )
            return GeneratedImageArtifact(
                temporary_path=encoded_output,
                cleanup=self._build_cleanup([encoded_output]),
            )
        except Exception:
            self._cleanup_files([encoded_output])
            raise

    def _ensure_work_directory(self, output_path: Path | None = None) -> Path:
        if output_path is not None:
            desired_work_directory = (
                output_path.parent / f".tmp-realcugan-{self._work_directory_id}"
            ).resolve(strict=False)
        else:
            desired_work_directory = (
                self._get_current_working_directory()
                / self._WORK_DIRECTORY_RELATIVE_PATH
                / self._work_directory_id
            ).resolve(strict=False)

        if (
            self._work_directory is not None
            and self._work_directory == desired_work_directory
            and self._work_directory.is_dir()
        ):
            return self._work_directory

        desired_work_directory.mkdir(parents=True, exist_ok=True)
        self._work_directory = desired_work_directory
        return desired_work_directory

    @staticmethod
    def _cleanup_files(files: list[Path]) -> None:
        for file_path in files:
            file_path.unlink(missing_ok=True)

    @classmethod
    def _build_cleanup(cls, files: list[Path]) -> Callable[[], None]:
        targets = tuple(files)

        def cleanup() -> None:
            cls._cleanup_files(list(targets))

        return cleanup

    def _resolve_thread_config(self, image: "Image.Image") -> str:
        pixel_count = image.width * image.height
        if pixel_count <= self._THREAD_CONFIG_PIXEL_THRESHOLD:
            return self._SMALL_IMAGE_THREAD_CONFIG
        return self._LARGE_IMAGE_THREAD_CONFIG

    def __del__(self) -> None:
        if self._work_directory is None:
            return

        # 返却済み artifact の temporary_path は呼び出し側が所有するため削除しない。
        self._remove_empty_directory_if_exists(self._work_directory)

    @staticmethod
    def _remove_empty_directory_if_exists(directory_path: Path) -> None:
        try:
            directory_path.rmdir()
        except OSError:
            # ファイル残存や他要因で削除不可でも、処理本体には影響しないため無視する。
            pass

    @staticmethod
    def _prepare_for_realcugan_png(image: "Image.Image") -> "Image.Image":
        if image.mode in {"RGB", "RGBA", "L", "LA"}:
            return image

        if image.mode == "P":
            if "transparency" in image.info:
                return image.convert("RGBA")
            return image.convert("RGB")

        # Real-CUGAN に渡す一時 PNG へ保存できないモード (例: CMYK) は RGB へ正規化する。
        return image.convert("RGB")

    @staticmethod
    def _run_realcugan(command: list[str]) -> subprocess.CompletedProcess[str]:
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            return subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=1800,  # コマンドの無限ハング防止のため30分のタイムアウトを設定
                creationflags=creation_flags,  # Windows GUIアプリでコンソールウィンドウが表示されないよう抑制
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Real-CUGAN execution timed out after 1800 seconds.") from exc

    @staticmethod
    def _resize_with_pillow(image: "Image.Image", scale_factor: int) -> "Image.Image":
        # Pillow の可用性は upscale() 冒頭で保証済みのためここでは再チェックしない。
        from PIL import Image

        output_width = image.width * scale_factor
        output_height = image.height * scale_factor
        return image.resize((output_width, output_height), Image.Resampling.LANCZOS)

    @staticmethod
    def _encode_image_to_temporary_path(
        image: "Image.Image",
        temporary_path: Path,
        output_format: str,
    ) -> None:
        save_options: dict[str, int | bool] = {}
        if output_format == "JPEG":
            save_options = {"quality": 100, "subsampling": 0}
        elif output_format == "WEBP":
            save_options = {"lossless": True, "quality": 100}

        image.save(temporary_path, format=output_format, **save_options)

    @staticmethod
    def _resolve_output_format(extension: str) -> str:
        if extension in {".jpg", ".jpeg"}:
            return "JPEG"
        if extension == ".png":
            return "PNG"
        if extension == ".webp":
            return "WEBP"
        raise ValueError(f"Unsupported output extension for RealCuganUpscaleEngine: {extension}")

    @staticmethod
    def _prepare_for_jpeg(image: "Image.Image") -> "Image.Image":
        if image.mode in ("RGBA", "LA"):
            return RealCuganUpscaleEngine._composite_on_white_background(image.convert("RGBA"))

        if image.mode == "P":
            if "transparency" in image.info:
                return RealCuganUpscaleEngine._composite_on_white_background(
                    image.convert("RGBA"),
                )
            return image.convert("RGB")

        if image.mode != "RGB":
            return image.convert("RGB")

        return image

    @staticmethod
    def _composite_on_white_background(image_rgba: "Image.Image") -> "Image.Image":
        from PIL import Image

        white_background = Image.new("RGBA", image_rgba.size, (255, 255, 255, 255))
        composited = Image.alpha_composite(white_background, image_rgba)
        return composited.convert("RGB")
