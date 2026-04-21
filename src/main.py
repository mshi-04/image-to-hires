import sys

from PySide6.QtWidgets import QApplication

from src.app_metadata import APPLICATION_NAME, ORGANIZATION_NAME
from src.domain.usecase.run_upscale_batch_usecase import RunUpscaleBatchUseCase
from src.infrastructure.image_io import FileImageStorage, PillowImageSizeReader
from src.infrastructure.inference.realcugan_upscale_engine import RealCuganUpscaleEngine
from src.infrastructure.runtime import SingleInstanceGuard
from src.infrastructure.settings import QtApplicationSettings
from src.ui.windows.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setOrganizationName(ORGANIZATION_NAME)
    app.setApplicationName(APPLICATION_NAME)
    single_instance_guard = SingleInstanceGuard(parent=app)
    if not single_instance_guard.start_or_notify():
        return 0

    batch_usecase = RunUpscaleBatchUseCase(
        upscale_engine=RealCuganUpscaleEngine(),
        image_storage=FileImageStorage(),
        image_size_reader=PillowImageSizeReader(),
    )
    window = MainWindow(
        batch_usecase=batch_usecase,
        app_settings=QtApplicationSettings(),
    )
    single_instance_guard.activated.connect(window.activate_from_secondary_launch)
    app.aboutToQuit.connect(single_instance_guard.close)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
