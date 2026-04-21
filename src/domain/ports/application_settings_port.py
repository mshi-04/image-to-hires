from typing import Protocol


class ApplicationSettingsPort(Protocol):
    """Boundary for persisting lightweight application UI settings."""

    def load_auto_sizing_enabled(self) -> bool:
        """Return the persisted auto-sizing preference."""

    def save_auto_sizing_enabled(self, enabled: bool) -> None:
        """Persist the auto-sizing preference."""

    def load_append_output_suffix(self) -> bool:
        """Return the persisted output suffix preference."""

    def save_append_output_suffix(self, enabled: bool) -> None:
        """Persist the output suffix preference."""

    def load_last_selected_directory(self) -> str | None:
        """Return the previously selected input directory path."""

    def save_last_selected_directory(self, directory: str) -> None:
        """Persist the latest input directory path."""
