from typing import Protocol


class ApplicationSettingsPort(Protocol):
    """Boundary for persisting lightweight application UI settings."""

    def load_auto_sizing_enabled(self) -> bool:
        """Return the persisted auto-sizing preference."""

    def save_auto_sizing_enabled(self, enabled: bool) -> None:
        """Persist the auto-sizing preference."""
