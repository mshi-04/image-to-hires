import unittest

from src.domain.exceptions import UnsupportedScaleFactorError
from src.domain.value_objects.scale_factor import ScaleFactor


class TestScaleFactor(unittest.TestCase):
    def test_scale_factor_accepts_supported_values(self) -> None:
        for value in [2, 3, 4]:
            with self.subTest(value=value):
                self.assertEqual(ScaleFactor(value).value, value)

    def test_scale_factor_rejects_unsupported_values(self) -> None:
        for value in [1, 5]:
            with self.subTest(value=value):
                with self.assertRaises(UnsupportedScaleFactorError):
                    ScaleFactor(value)

    def test_scale_factor_rejects_non_integer_number(self) -> None:
        with self.assertRaises(UnsupportedScaleFactorError):
            ScaleFactor(2.0)  # type: ignore[arg-type]

    def test_scale_factor_rejects_bool(self) -> None:
        with self.assertRaises(UnsupportedScaleFactorError):
            ScaleFactor(True)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
