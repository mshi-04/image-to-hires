import unittest

from src.domain.exceptions import UnsupportedDenoiseLevelError
from src.domain.value_objects.denoise_level import DenoiseLevel


class TestDenoiseLevel(unittest.TestCase):
    def test_denoise_level_accepts_supported_values(self) -> None:
        for value in [0, 1, 2, 3]:
            with self.subTest(value=value):
                # Arrange / Act
                denoise_level = DenoiseLevel(value)

                # Assert
                self.assertEqual(denoise_level.value, value)

    def test_denoise_level_rejects_unsupported_value(self) -> None:
        # Arrange / Act / Assert
        with self.assertRaises(UnsupportedDenoiseLevelError):
            DenoiseLevel(4)

    def test_denoise_level_rejects_negative_value(self) -> None:
        # Arrange / Act / Assert
        with self.assertRaises(UnsupportedDenoiseLevelError):
            DenoiseLevel(-1)

    def test_denoise_level_rejects_non_integer_number(self) -> None:
        # Arrange / Act / Assert
        with self.assertRaises(UnsupportedDenoiseLevelError):
            DenoiseLevel(1.5)  # type: ignore[arg-type]

    def test_denoise_level_rejects_non_number(self) -> None:
        # Arrange / Act / Assert
        with self.assertRaises(UnsupportedDenoiseLevelError):
            DenoiseLevel(None)  # type: ignore[arg-type]

        with self.assertRaises(UnsupportedDenoiseLevelError):
            DenoiseLevel("1")  # type: ignore[arg-type]

    def test_denoise_level_rejects_bool(self) -> None:
        # Arrange / Act / Assert
        with self.assertRaises(UnsupportedDenoiseLevelError):
            DenoiseLevel(False)  # type: ignore[arg-type]

        with self.assertRaises(UnsupportedDenoiseLevelError):
            DenoiseLevel(True)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
