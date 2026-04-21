from src.domain.ports.image_size_reader_port import ImageSizeReaderPort
from src.domain.value_objects.image_path import InputImagePath
from src.domain.value_objects.image_size import ImageSize


class PillowImageSizeReader(ImageSizeReaderPort):
    """Read image dimensions via Pillow without loading full domain logic into the UI."""

    def read_size(self, input_image: InputImagePath) -> ImageSize:
        try:
            from PIL import Image
        except ModuleNotFoundError as exc:
            raise RuntimeError("Pillow is required to read image sizes.") from exc

        with Image.open(input_image.value) as image:
            return ImageSize(width=image.width, height=image.height)
