from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QCoreApplication, QIODeviceBase, Signal, Slot
from PySide6.QtNetwork import QLocalServer, QLocalSocket


class SingleInstanceGuard(QObject):
    """Keep a single app instance alive and notify it on secondary launches."""

    activated = Signal()

    _CONNECT_TIMEOUT_MS = 500
    _READ_TIMEOUT_MS = 500
    _MESSAGE = b"activate"

    def __init__(
        self,
        server_name: str | None = None,
        *,
        server: QLocalServer | None = None,
        socket_factory: Callable[[], QLocalSocket] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._server_name = server_name or self._build_server_name()
        self._server = server or QLocalServer(self)
        self._socket_factory = socket_factory or QLocalSocket
        self._is_primary_instance = False

    @property
    def is_primary_instance(self) -> bool:
        return self._is_primary_instance

    @property
    def server_name(self) -> str:
        return self._server_name

    def start_or_notify(self) -> bool:
        if self._notify_existing_instance():
            self._is_primary_instance = False
            return False

        if self._server.listen(self._server_name):
            self._server.newConnection.connect(self._on_new_connection)
            self._is_primary_instance = True
            return True

        if self._notify_existing_instance():
            self._is_primary_instance = False
            return False

        QLocalServer.removeServer(self._server_name)

        if not self._server.listen(self._server_name):
            if self._notify_existing_instance():
                self._is_primary_instance = False
                return False
            error = self._server.errorString()
            raise RuntimeError(
                f"Failed to start single-instance server '{self._server_name}': {error}"
            )

        self._server.newConnection.connect(self._on_new_connection)
        self._is_primary_instance = True
        return True

    def close(self) -> None:
        if self._server.isListening():
            self._server.close()
            QLocalServer.removeServer(self._server_name)
        self._is_primary_instance = False

    def _notify_existing_instance(self) -> bool:
        socket = self._socket_factory()
        socket.connectToServer(self._server_name, QIODeviceBase.OpenModeFlag.ReadWrite)
        if not socket.waitForConnected(self._CONNECT_TIMEOUT_MS):
            socket.abort()
            socket.deleteLater()
            return False

        socket.write(self._MESSAGE)
        socket.flush()
        socket.waitForBytesWritten(self._CONNECT_TIMEOUT_MS)
        socket.disconnectFromServer()
        if socket.state() != QLocalSocket.LocalSocketState.UnconnectedState:
            socket.waitForDisconnected(self._CONNECT_TIMEOUT_MS)
        socket.deleteLater()
        return True

    @staticmethod
    def _build_server_name() -> str:
        organization = QCoreApplication.organizationName().strip() or "codex"
        application = QCoreApplication.applicationName().strip() or "application"
        return f"{organization}.{application}.single-instance"

    @Slot()
    def _on_new_connection(self) -> None:
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            if socket is None:
                continue
            socket.readyRead.connect(lambda connection=socket: self._consume_message(connection))
            socket.disconnected.connect(socket.deleteLater)
            self._consume_message(socket)

    def _consume_message(self, socket: QLocalSocket) -> None:
        if socket.bytesAvailable() == 0 and socket.state() == QLocalSocket.LocalSocketState.ConnectedState:
            socket.waitForReadyRead(self._READ_TIMEOUT_MS)
        payload = bytes(socket.readAll()).strip()
        if payload == self._MESSAGE:
            self.activated.emit()
        socket.disconnectFromServer()
