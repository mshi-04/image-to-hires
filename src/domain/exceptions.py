"""Domain-specific exceptions."""


class DomainError(ValueError):
    """Base error for domain validation issues."""


class UnsupportedScaleFactorError(DomainError):
    """Raised when an unsupported scale factor is requested."""


class UnsupportedImageFormatError(DomainError):
    """Raised when an unsupported image format is requested."""


class UnsupportedDenoiseLevelError(DomainError):
    """Raised when an unsupported denoise level is requested."""
