import logging

from PySide6.QtCore import QSettings

from src.app_metadata import APPLICATION_NAME, ORGANIZATION_NAME
from src.domain.ports.application_settings_port import ApplicationSettingsPort


_LOGGER = logging.getLogger(__name__)


class QtApplicationSettings(ApplicationSettingsPort):
    """Persist small UI preferences using the platform-native Qt settings store."""

    _ORGANIZATION = ORGANIZATION_NAME
    _APPLICATION = APPLICATION_NAME
    _AUTO_SIZING_KEY = "ui/auto_sizing_enabled"
    _APPEND_OUTPUT_SUFFIX_KEY = "ui/append_output_suffix"
    _LAST_SELECTED_DIRECTORY_KEY = "ui/last_selected_directory"

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

    def load_append_output_suffix(self) -> bool:
        value = self._settings.value(self._APPEND_OUTPUT_SUFFIX_KEY, True, type=bool)
        if self._settings.status() != QSettings.Status.NoError:
            _LOGGER.warning(
                "Failed to load setting '%s': status=%s",
                self._APPEND_OUTPUT_SUFFIX_KEY,
                self._settings.status().name,
            )
            return True
        return bool(value)

    def save_append_output_suffix(self, enabled: bool) -> None:
        self._settings.setValue(self._APPEND_OUTPUT_SUFFIX_KEY, bool(enabled))
        self._settings.sync()
        if self._settings.status() != QSettings.Status.NoError:
            _LOGGER.warning(
                "Failed to save setting '%s'=%s: status=%s",
                self._APPEND_OUTPUT_SUFFIX_KEY,
                bool(enabled),
                self._settings.status().name,
            )

    def load_last_selected_directory(self) -> str | None:
        value = self._settings.value(self._LAST_SELECTED_DIRECTORY_KEY, "", type=str)
        if self._settings.status() != QSettings.Status.NoError:
            _LOGGER.warning(
                "Failed to load setting '%s': status=%s",
                self._LAST_SELECTED_DIRECTORY_KEY,
                self._settings.status().name,
            )
            return None
        normalized = str(value).strip()
        return normalized or None

    def save_last_selected_directory(self, directory: str) -> None:
        normalized = str(directory).strip()
        self._settings.setValue(self._LAST_SELECTED_DIRECTORY_KEY, normalized)
        self._settings.sync()
        if self._settings.status() != QSettings.Status.NoError:
            _LOGGER.warning(
                "Failed to save setting '%s'=%s: status=%s",
                self._LAST_SELECTED_DIRECTORY_KEY,
                normalized,
                self._settings.status().name,
            )
