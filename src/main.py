import sys

from PySide6.QtWidgets import QApplication

from src.domain.usecase.run_upscale_batch_usecase import RunUpscaleBatchUseCase
from src.infrastructure.image_io import FileImageStorage, PillowImageSizeReader
from src.infrastructure.inference.realcugan_upscale_engine import RealCuganUpscaleEngine
from src.infrastructure.settings import QtApplicationSettings
from src.ui.windows.main_window import MainWindow

def main() -> int:
    app = QApplication(sys.argv)
    batch_usecase = RunUpscaleBatchUseCase(
        upscale_engine=RealCuganUpscaleEngine(),
        image_storage=FileImageStorage(),
        image_size_reader=PillowImageSizeReader(),
    )
    window = MainWindow(
        batch_usecase=batch_usecase,
        app_settings=QtApplicationSettings(),
    )
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
