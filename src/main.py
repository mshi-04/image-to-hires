import sys

from PySide6.QtWidgets import QApplication

from src.domain.usecase.run_upscale_batch_usecase import RunUpscaleBatchUseCase
from src.infrastructure.image_io.file_image_storage import FileImageStorage
from src.infrastructure.inference.pillow_upscale_engine import PillowUpscaleEngine
from src.ui.windows.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    batch_usecase = RunUpscaleBatchUseCase(
        upscale_engine=PillowUpscaleEngine(),
        image_storage=FileImageStorage(),
    )
    window = MainWindow(batch_usecase=batch_usecase)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
