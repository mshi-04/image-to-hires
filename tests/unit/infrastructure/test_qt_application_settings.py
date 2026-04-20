import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

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

    def test_load_returns_default_and_logs_when_qsettings_reports_error(self) -> None:
        # Arrange
        settings = MagicMock(spec=QSettings)
        settings.value.return_value = True
        settings.status.return_value = QSettings.Status.FormatError
        subject = QtApplicationSettings(settings)

        # Act / Assert
        with patch("src.infrastructure.settings.qt_application_settings._LOGGER") as logger:
            self.assertFalse(subject.load_auto_sizing_enabled())
            logger.warning.assert_called_once()

    def test_save_logs_when_qsettings_reports_error(self) -> None:
        # Arrange
        settings = MagicMock(spec=QSettings)
        settings.status.return_value = QSettings.Status.AccessError
        subject = QtApplicationSettings(settings)

        # Act
        with patch("src.infrastructure.settings.qt_application_settings._LOGGER") as logger:
            subject.save_auto_sizing_enabled(False)

        # Assert
        settings.setValue.assert_called_once_with("ui/auto_sizing_enabled", False)
        settings.sync.assert_called_once_with()
        logger.warning.assert_called_once()


if __name__ == "__main__":
    unittest.main()
