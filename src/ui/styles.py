# Define stylesheets here to keep UI code clean

MAIN_WINDOW_STYLESHEET = """
QMainWindow {
    background-color: #f4f8fc;
}
QWidget#centralWidget {
    background-color: #f4f8fc;
}
QWidget#contentArea {
    background-color: #f4f8fc;
}
QWidget#header {
    background-color: #f4f8fc;
    border-bottom: 1px solid #d8e2ee;
}
QLabel#headerTitle {
    color: #10233f;
    font-size: 20px;
    font-weight: bold;
    padding: 4px 6px;
    letter-spacing: 0.5px;
}
QLabel#headerVersion {
    color: #5f7490;
    font-size: 11px;
    font-weight: 600;
    padding-right: 6px;
}
QLineEdit,
QComboBox,
QListWidget {
    border: 1px solid #c9d6e4;
    border-radius: 10px;
    padding: 4px 8px;
    background-color: #ffffff;
    color: #10233f;
    font-size: 12px;
}
QLineEdit {
    selection-background-color: #d9eafe;
}
QLineEdit:focus,
QComboBox:focus,
QListWidget:focus {
    border: 2px solid #2f80ed;
}
QComboBox {
    padding-right: 28px;
    min-width: 180px;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 22px;
    border: none;
    margin: 3px 5px 3px 0;
    background-color: #eef4fb;
    border-radius: 6px;
}
QComboBox::down-arrow {
    image: none;
    width: 0;
    height: 0;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #47607c;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #10233f;
    border: 1px solid #c9d6e4;
    border-radius: 10px;
    padding: 3px;
    selection-background-color: #dbeafe;
    selection-color: #10233f;
    outline: 0;
}
QComboBox QAbstractItemView::item {
    min-height: 24px;
    padding: 3px 6px;
    border-radius: 6px;
}
QComboBox QAbstractItemView::item:hover {
    background-color: #eef5ff;
}
QListWidget {
    padding: 6px;
    background-color: #ffffff;
}
QListWidget::item {
    padding: 4px 6px;
    margin: 1px 0;
    border-radius: 6px;
    background-color: #f7faff;
}
QProgressBar {
    border: none;
    border-radius: 8px;
    background-color: #dfeaf5;
    min-height: 12px;
    color: #21415f;
    text-align: center;
    font-weight: 600;
    font-size: 11px;
}
QProgressBar::chunk {
    border-radius: 8px;
    background-color: #2f80ed;
}
QPushButton#actionButton {
    background-color: #2f80ed;
    color: #ffffff;
    border: none;
    border-radius: 10px;
    font-weight: bold;
    font-size: 12px;
    padding: 6px 12px;
}
QPushButton#actionButton:hover {
    background-color: #1c6ed8;
}
QPushButton#actionButton:disabled {
    background-color: #a8c9f3;
    color: #edf5ff;
}
QLabel#fieldLabel {
    font-size: 12px;
    color: #21415f;
    font-weight: 600;
}
QWidget#footer {
    background-color: #dcecfb;
    border-top: 1px solid #c4ddf4;
}
"""
