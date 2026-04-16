import unittest

from src.domain.exceptions import UnsupportedScaleFactorError
from src.domain.value_objects.scale_factor import ScaleFactor


class TestScaleFactor(unittest.TestCase):
    def test_scale_factor_accepts_supported_values(self) -> None:
        self.assertEqual(ScaleFactor(2).value, 2)
        self.assertEqual(ScaleFactor(3).value, 3)
        self.assertEqual(ScaleFactor(4).value, 4)

    def test_scale_factor_rejects_unsupported_value(self) -> None:
        with self.assertRaises(UnsupportedScaleFactorError):
            ScaleFactor(5)


if __name__ == "__main__":
    unittest.main()
