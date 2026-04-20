from PySide6.QtCore import QSettings

from src.domain.ports.application_settings_port import ApplicationSettingsPort


class QtApplicationSettings(ApplicationSettingsPort):
    """Persist small UI preferences using the platform-native Qt settings store."""

    _ORGANIZATION = "image-to-hires"
    _APPLICATION = "image-to-hires"
    _AUTO_SIZING_KEY = "ui/auto_sizing_enabled"
    _APPEND_OUTPUT_SUFFIX_KEY = "ui/append_output_suffix"

    def __init__(self, settings: QSettings | None = None) -> None:
        self._settings = settings or QSettings(self._ORGANIZATION, self._APPLICATION)

    def load_auto_sizing_enabled(self) -> bool:
        try:
            value = self._settings.value(self._AUTO_SIZING_KEY, False, type=bool)
        except Exception:
            return False
        return bool(value)

    def save_auto_sizing_enabled(self, enabled: bool) -> None:
        try:
            self._settings.setValue(self._AUTO_SIZING_KEY, bool(enabled))
            self._settings.sync()
        except Exception:
            return

    def load_append_output_suffix(self) -> bool:
        try:
            value = self._settings.value(self._APPEND_OUTPUT_SUFFIX_KEY, True, type=bool)
        except Exception:
            return True
        return bool(value)

    def save_append_output_suffix(self, enabled: bool) -> None:
        try:
            self._settings.setValue(self._APPEND_OUTPUT_SUFFIX_KEY, bool(enabled))
            self._settings.sync()
        except Exception:
            return
