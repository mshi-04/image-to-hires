import time
import unittest
import uuid
from unittest.mock import patch

try:
    from PySide6.QtWidgets import QApplication
except ModuleNotFoundError:
    QApplication = None
    PYSIDE_AVAILABLE = False
else:
    PYSIDE_AVAILABLE = True

from src.infrastructure.runtime.single_instance_guard import SingleInstanceGuard


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is required for single-instance tests.")
class TestSingleInstanceGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.server_name = f"image-to-hires-test-{uuid.uuid4().hex}"
        self.guards: list[SingleInstanceGuard] = []

    def tearDown(self) -> None:
        for guard in reversed(self.guards):
            guard.close()
        self._app.processEvents()

    def test_start_or_notify_marks_first_instance_as_primary(self) -> None:
        guard = self._create_guard()

        self.assertTrue(guard.start_or_notify())
        self.assertTrue(guard.is_primary_instance)

    def test_start_or_notify_notifies_existing_instance(self) -> None:
        primary_guard = self._create_guard()
        self.assertTrue(primary_guard.start_or_notify())

        activations: list[bool] = []
        primary_guard.activated.connect(lambda: activations.append(True))

        secondary_guard = self._create_guard()

        self.assertFalse(secondary_guard.start_or_notify())
        self._process_events_until(lambda: bool(activations))
        self.assertEqual(activations, [True])
        self.assertFalse(secondary_guard.is_primary_instance)

    def test_start_or_notify_removes_stale_server_before_listen(self) -> None:
        guard = self._create_guard()

        with patch("src.infrastructure.runtime.single_instance_guard.QLocalServer.removeServer") as remove_server:
            with patch.object(guard, "_notify_existing_instance", side_effect=[False]):
                self.assertTrue(guard.start_or_notify())

        remove_server.assert_called_once_with(self.server_name)

    def test_activation_message_emits_signal(self) -> None:
        guard = self._create_guard()
        received: list[bool] = []
        guard.activated.connect(lambda: received.append(True))

        self.assertTrue(guard.start_or_notify())
        secondary_guard = self._create_guard()
        self.assertFalse(secondary_guard.start_or_notify())

        self._process_events_until(lambda: bool(received))
        self.assertEqual(received, [True])

    def _create_guard(self) -> SingleInstanceGuard:
        guard = SingleInstanceGuard(server_name=self.server_name)
        self.guards.append(guard)
        return guard

    def _process_events_until(self, condition, timeout: float = 1.0) -> None:  # noqa: ANN001
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self._app.processEvents()
            if condition():
                return
            time.sleep(0.01)
        self._app.processEvents()


if __name__ == "__main__":
    unittest.main()
