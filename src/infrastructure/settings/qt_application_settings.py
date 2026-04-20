import logging

from PySide6.QtCore import QSettings

from src.domain.ports.application_settings_port import ApplicationSettingsPort


_LOGGER = logging.getLogger(__name__)


class QtApplicationSettings(ApplicationSettingsPort):
    """Persist small UI preferences using the platform-native Qt settings store."""

    _ORGANIZATION = "image-to-hires"
    _APPLICATION = "image-to-hires"
    _AUTO_SIZING_KEY = "ui/auto_sizing_enabled"

    def __init__(self, settings: QSettings | None = None) -> None:
        self._settings = settings or QSettings(self._ORGANIZATION, self._APPLICATION)

    def load_auto_sizing_enabled(self) -> bool:
        value = self._settings.value(self._AUTO_SIZING_KEY, False, type=bool)
        if self._settings.status() != QSettings.Status.NoError:
            _LOGGER.warning(
                "Failed to load setting '%s': status=%s",
                self._AUTO_SIZING_KEY,
                self._settings.status().name,
            )
            return False
        return bool(value)

    def save_auto_sizing_enabled(self, enabled: bool) -> None:
        self._settings.setValue(self._AUTO_SIZING_KEY, bool(enabled))
        self._settings.sync()
        if self._settings.status() != QSettings.Status.NoError:
            _LOGGER.warning(
                "Failed to save setting '%s'=%s: status=%s",
                self._AUTO_SIZING_KEY,
                bool(enabled),
                self._settings.status().name,
            )
