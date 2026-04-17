import subprocess
import sys
import tempfile
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

from src.domain.entities.upscale_job import UpscaleJob
from src.domain.ports.upscale_engine_port import UpscaleEnginePort

if TYPE_CHECKING:
    from PIL import Image


class RealCuganUpscaleEngine(UpscaleEnginePort):
    """Upscaler with local Real-CUGAN path and Pillow fallback."""

    def __init__(
        self,
        realcugan_executable: Path | str | None = None,
        realcugan_models_dir: Path | str | None = None,
        prefer_realcugan: bool = True,
    ) -> None:
        self._prefer_realcugan = prefer_realcugan

        # 実行ファイルの位置からデフォルトパスを解決する
        base_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path.cwd()
        self._realcugan_executable = Path(realcugan_executable or base_dir / "bin" / "realcugan" / "realcugan-ncnn-vulkan.exe")
        self._realcugan_models_dir = Path(
            realcugan_models_dir or base_dir / "models" / "realcugan" / "models-se"
        )

    def upscale(self, job: UpscaleJob) -> bytes:
        image_path = Path(job.input_image.value)
        if not image_path.exists():
            raise FileNotFoundError(f"Input image file was not found: {image_path}")

        try:
            from PIL import Image, ImageOps
        except ModuleNotFoundError as exc:
            raise RuntimeError("Pillow is required to run RealCuganUpscaleEngine.") from exc

        with Image.open(image_path) as source_image:
            normalized_image = ImageOps.exif_transpose(source_image)
            if self._should_use_realcugan():
                self._assert_realcugan_runtime_is_ready()
                upscaled_image = self._upscale_with_realcugan(normalized_image, job)
            else:
                upscaled_image = self._upscale_with_pillow(normalized_image, job.scale_factor.value)
            
            output_format = self._resolve_output_format(Path(job.output_image.value).suffix.lower())

            if output_format == "JPEG":
                upscaled_image = self._prepare_for_jpeg(upscaled_image)

            buffer = BytesIO()
            save_options: dict[str, int | bool] = {}
            if output_format == "JPEG":
                save_options = {"quality": 100, "subsampling": 0}
            elif output_format == "WEBP":
                save_options = {"lossless": True, "quality": 100}
            
            upscaled_image.save(buffer, format=output_format, **save_options)
            return buffer.getvalue()

    def _should_use_realcugan(self) -> bool:
        return self._prefer_realcugan

    def _assert_realcugan_runtime_is_ready(self) -> None:
        missing_reasons: list[str] = []
        if not self._realcugan_executable.is_file():
            missing_reasons.append(f"executable not found: {self._realcugan_executable}")
        if not self._realcugan_models_dir.is_dir():
            missing_reasons.append(f"models directory not found: {self._realcugan_models_dir}")
        if missing_reasons:
            details = "; ".join(missing_reasons)
            raise RuntimeError(f"Real-CUGAN runtime is not ready: {details}")

    def _upscale_with_realcugan(self, image: "Image.Image", job: UpscaleJob) -> "Image.Image":
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir_path = Path(tmp_dir)
            input_png = tmp_dir_path / "input.png"
            output_png = tmp_dir_path / "output.png"
            image.save(input_png, format="PNG")

            command = [
                str(self._realcugan_executable),
                "-i", str(input_png),
                "-o", str(output_png),
                "-s", str(job.scale_factor.value),
                "-n", str(job.denoise_level.value),
                "-m", str(self._realcugan_models_dir),
                "-f", "png",
                # "-x",  # TTAを有効にすると処理時間が数倍に延びるためMVPでは無効化する
            ]
            run_result = self._run_realcugan(command)
            if run_result.returncode != 0:
                stderr = (run_result.stderr or "").strip()
                stdout = (run_result.stdout or "").strip()
                details = stderr or stdout or "No stderr/stdout output."
                raise RuntimeError(f"Real-CUGAN execution failed: {details}")
            if not output_png.exists():
                raise RuntimeError("Real-CUGAN finished without producing output image.")

            with Image.open(output_png) as result_image:
                return result_image.copy()

    @staticmethod
    def _run_realcugan(command: list[str]) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=1800,  # コマンドの無限ハング防止のため30分のタイムアウトを設定
                creationflags=subprocess.CREATE_NO_WINDOW,  # Windows GUIアプリでコンソールウィンドウが表示されないよう抑制
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Real-CUGAN execution timed out after 1800 seconds.") from exc

    @staticmethod
    def _upscale_with_pillow(image: "Image.Image", scale_factor: int) -> "Image.Image":
        try:
            from PIL import Image
        except ModuleNotFoundError as exc:
            raise RuntimeError("Pillow is required to run RealCuganUpscaleEngine.") from exc

        output_width = image.width * scale_factor
        output_height = image.height * scale_factor
        return image.resize((output_width, output_height), Image.Resampling.LANCZOS)

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
