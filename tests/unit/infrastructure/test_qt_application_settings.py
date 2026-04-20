import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QSettings

from src.infrastructure.settings.qt_application_settings import QtApplicationSettings


class TestQtApplicationSettings(unittest.TestCase):
    @staticmethod
    def _build_settings(settings_root: Path) -> QtApplicationSettings:
        settings_path = settings_root / "app-settings.ini"
        return QtApplicationSettings(QSettings(str(settings_path), QSettings.Format.IniFormat))

    def test_load_returns_false_when_setting_is_missing(self) -> None:
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_root = Path(tmpdir)

            # Act
            settings = self._build_settings(settings_root)

            # Assert
            self.assertFalse(settings.load_auto_sizing_enabled())

    def test_save_and_load_round_trip(self) -> None:
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_root = Path(tmpdir)

            # Act
            settings = self._build_settings(settings_root)
            settings.save_auto_sizing_enabled(True)
            reloaded = self._build_settings(settings_root)

            # Assert
            self.assertTrue(reloaded.load_auto_sizing_enabled())


if __name__ == "__main__":
    unittest.main()
