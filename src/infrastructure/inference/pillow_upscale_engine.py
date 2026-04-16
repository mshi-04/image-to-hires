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
            denoised_image = self._apply_denoise_filter(
                normalized_image,
                denoise_level=job.denoise_level.value,
            )

            output_width = denoised_image.width * job.scale_factor.value
            output_height = denoised_image.height * job.scale_factor.value
            upscaled_image = denoised_image.resize((output_width, output_height), Image.Resampling.LANCZOS)
            output_format = self._resolve_output_format(Path(job.output_image.value).suffix.lower())

            if output_format == "JPEG":
                upscaled_image = self._prepare_for_jpeg(upscaled_image)

            buffer = BytesIO()
            upscaled_image.save(buffer, format=output_format)
            return buffer.getvalue()

    @staticmethod
    def _resolve_output_format(extension: str) -> str:
        if extension in {".jpg", ".jpeg"}:
            return "JPEG"
        if extension == ".png":
            return "PNG"
        if extension == ".webp":
            return "WEBP"
        raise ValueError(f"Unsupported output extension for PillowUpscaleEngine: {extension}")

    @staticmethod
    def _apply_denoise_filter(image, denoise_level: int):
        from PIL import ImageFilter

        median_filter_sizes = {1: 3, 2: 5, 3: 7}
        filter_size = median_filter_sizes.get(denoise_level)
        if filter_size is None:
            return image
        return image.filter(ImageFilter.MedianFilter(size=filter_size))

    @staticmethod
    def _prepare_for_jpeg(image):
        if image.mode in ("RGBA", "LA"):
            return PillowUpscaleEngine._composite_on_white_background(image.convert("RGBA"))

        if image.mode == "P":
            if "transparency" in image.info:
                return PillowUpscaleEngine._composite_on_white_background(
                    image.convert("RGBA"),
                )
            return image.convert("RGB")

        if image.mode != "RGB":
            return image.convert("RGB")

        return image

    @staticmethod
    def _composite_on_white_background(image_rgba):
        from PIL import Image

        white_background = Image.new("RGBA", image_rgba.size, (255, 255, 255, 255))
        composited = Image.alpha_composite(white_background, image_rgba)
        return composited.convert("RGB")
