from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLabel, QWidget


class SettingsWidget(QWidget):
    """Component for configuring upscale parameters."""

    _AUTO_DENOISE_LEVEL = 3

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._denoise_level_before_auto_sizing = -1

        layout = QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        self.denoise_combo = self._build_combo_box([("なし", -1), ("0", 0), ("1", 1), ("2", 2), ("3", 3)])
        denoise_label = QLabel("デノイズ:")
        denoise_label.setObjectName("fieldLabel")
        layout.addRow(denoise_label, self.denoise_combo)

        self.scale_combo = self._build_combo_box([("2倍", 2), ("3倍", 3), ("4倍", 4)])
        scale_label = QLabel("拡大率:")
        scale_label.setObjectName("fieldLabel")
        layout.addRow(scale_label, self.scale_combo)

        self.auto_sizing_checkbox = QCheckBox("自動サイジング")
        self.auto_sizing_checkbox.toggled.connect(self._sync_scale_combo_state)

        self.append_output_suffix_checkbox = QCheckBox("サフィックスを付ける")
        self.append_output_suffix_checkbox.setChecked(True)

        options_row = QWidget()
        options_layout = QHBoxLayout(options_row)
        options_layout.setContentsMargins(0, 0, 0, 0)
        options_layout.setSpacing(16)
        options_layout.addWidget(self.auto_sizing_checkbox)
        options_layout.addWidget(self.append_output_suffix_checkbox)
        options_layout.addStretch()
        layout.addRow("", options_row)

        self._sync_scale_combo_state(self.auto_sizing_checkbox.isChecked())

    @staticmethod
    def _build_combo_box(values: list[tuple[str, object]]) -> QComboBox:
        combo = QComboBox()
        combo.setMinimumHeight(32)
        combo.setMinimumWidth(460)
        for label, data in values:
            combo.addItem(label, data)
        return combo

    def get_denoise_level(self) -> int:
        return int(self.denoise_combo.currentData())

    def get_scale_factor(self) -> int:
        return int(self.scale_combo.currentData())

    def is_auto_sizing_enabled(self) -> bool:
        return self.auto_sizing_checkbox.isChecked()

    def set_auto_sizing_enabled(self, enabled: bool) -> None:
        self.auto_sizing_checkbox.setChecked(enabled)

    def should_append_output_suffix(self) -> bool:
        return self.append_output_suffix_checkbox.isChecked()

    def set_append_output_suffix(self, enabled: bool) -> None:
        self.append_output_suffix_checkbox.setChecked(enabled)

    def set_inputs_enabled(self, enabled: bool) -> None:
        self.denoise_combo.setEnabled(enabled and not self.auto_sizing_checkbox.isChecked())
        self.auto_sizing_checkbox.setEnabled(enabled)
        self.append_output_suffix_checkbox.setEnabled(enabled)
        self.scale_combo.setEnabled(enabled and not self.auto_sizing_checkbox.isChecked())

    def _sync_scale_combo_state(self, auto_sizing_enabled: bool) -> None:
        self.scale_combo.setEnabled(not auto_sizing_enabled)
        if auto_sizing_enabled:
            self._denoise_level_before_auto_sizing = self.get_denoise_level()
            self._set_denoise_level(self._AUTO_DENOISE_LEVEL)
            self.denoise_combo.setEnabled(False)
            return

        self._set_denoise_level(self._denoise_level_before_auto_sizing)
        self.denoise_combo.setEnabled(True)

    def _set_denoise_level(self, value: int) -> None:
        index = self.denoise_combo.findData(value)
        if index >= 0:
            self.denoise_combo.setCurrentIndex(index)
