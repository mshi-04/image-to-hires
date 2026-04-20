from src.domain.value_objects.image_size import ImageSize
from src.domain.value_objects.scale_factor import ScaleFactor


_DOUBLE_SCALE_TARGET = ImageSize(width=2752, height=1536)
_TRIPLE_SCALE_TARGET = ImageSize(width=1376, height=768)


def resolve_scale_factor_for_image(image_size: ImageSize, fallback_scale_factor: ScaleFactor) -> ScaleFactor:
    """Resolve a scale factor from exact image-size matches, otherwise use the fallback."""

    if image_size == _DOUBLE_SCALE_TARGET:
        return ScaleFactor(2)

    if image_size == _TRIPLE_SCALE_TARGET:
        return ScaleFactor(3)

    return fallback_scale_factor
