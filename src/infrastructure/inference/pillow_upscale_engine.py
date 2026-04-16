from io import BytesIO
from pathlib import Path

from src.domain.entities.upscale_job import UpscaleJob
from src.domain.ports.upscale_engine_port import UpscaleEnginePort


class PillowUpscaleEngine(UpscaleEnginePort):
    """Simple image upscaler backed by Pillow."""

    def upscale(self, job: UpscaleJob) -> bytes:
        image_path = Path(job.input_image.value)
        if not image_path.exists():
            raise FileNotFoundError(f"Input image file was not found: {image_path}")

        try:
            from PIL import Image, ImageOps
        except ModuleNotFoundError as exc:
            raise RuntimeError("Pillow is required to run PillowUpscaleEngine.") from exc

        with Image.open(image_path) as source_image:
            normalized_image = ImageOps.exif_transpose(source_image)
            output_width = normalized_image.width * job.scale_factor.value
            output_height = normalized_image.height * job.scale_factor.value
            upscaled_image = normalized_image.resize((output_width, output_height), Image.Resampling.LANCZOS)
            output_format = self._resolve_output_format(Path(job.output_image.value).suffix.lower())

            if output_format == "JPEG" and upscaled_image.mode in ("RGBA", "LA", "P"):
                upscaled_image = upscaled_image.convert("RGB")

            buffer = BytesIO()
            upscaled_image.save(buffer, format=output_format)
            return buffer.getvalue()

    @staticmethod
    def _resolve_output_format(extension: str) -> str:
        if extension in {".jpg", ".jpeg"}:
            return "JPEG"
        if extension == ".png":
            return "PNG"
        raise ValueError(f"Unsupported output extension for PillowUpscaleEngine: {extension}")
