"""在本机把单篇论文包交给已打开目标文献库的程序导入。

【依赖】QtCore、QtNetwork 的本机套接字；services.bundle_import 的单篇导入服务。
【被谁调用】__main__ 取得同库锁后启动接收端；技能脚本遇到同库锁时调用发送端。
【扩展点】连接只接受一条以换行结束的 UTF-8 JSON 消息；协议改变时更新版本。
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Callable
from functools import partial
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QStandardPaths, QTimer
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from .services.app_context import AppContext
from .services.bundle_import import import_bundle

_MESSAGE_LIMIT = 512 * 1024    # 只传目录和入库结果，大文件通过原路径读取
_RESULT_UNKNOWN = "未收到完整入库回执，论文可能已经导入。再次尝试时请使用同一份论文包核对。"


class ImportServerUnavailable(RuntimeError):
    """还没有连上持锁的程序，未发送任何导入请求，可以重新尝试取得库锁。"""


def _endpoint(library: Path) -> str:
    key = hashlib.sha256(os.fsencode(os.path.normcase(str(library.resolve())))).hexdigest()[:32]
    name = "litmgr-import-" + key
    if os.name == "nt":
        return name
    # Unix 的套接字放在当前用户的私有运行目录，异常退出后只会留下本用户的端点。
    runtime = QStandardPaths.writableLocation(QStandardPaths.RuntimeLocation)
    if not runtime:
        raise RuntimeError("无法取得当前用户的本机通信目录")
    return str(Path(runtime) / name)


def _message(data: dict) -> bytes:
    payload = json.dumps(data).encode("utf-8") + b"\n"
    if len(payload) > _MESSAGE_LIMIT:
        raise ValueError("后台导入消息过长")
    return payload


class LocalImportServer(QLocalServer):
    """由持有目标库单实例锁的进程创建，在 Qt 事件循环中用现有 AppContext 逐篇导入。"""

    def __init__(self, ctx: AppContext, is_busy: Callable[[], bool] | None = None) -> None:
        super().__init__()
        self._ctx = ctx
        self._is_busy = is_busy
        self._library = ctx.library_path.resolve()
        self.setSocketOptions(QLocalServer.UserAccessOption)
        name = _endpoint(self._library)
        if os.name != "nt":
            QLocalServer.removeServer(name)   # 此时已独占该库，清理异常退出的 Unix 套接字
        self.newConnection.connect(self._accept)
        if not self.listen(name):
            raise RuntimeError(f"无法启动本机论文导入入口：{self.errorString()}")

    def _accept(self) -> None:
        while self.hasPendingConnections():
            socket = self.nextPendingConnection()
            socket.setReadBufferSize(_MESSAGE_LIMIT + 1)
            socket.disconnected.connect(socket.deleteLater)
            # 未发完路径的客户端不能占用连接，也不能阻塞程序界面。
            timer = QTimer(socket)
            timer.setSingleShot(True)
            timer.timeout.connect(socket.abort)
            timer.start(10000)
            receive = partial(self._receive, socket, timer)
            socket.readyRead.connect(receive)
            receive()

    def _receive(self, socket: QLocalSocket, timer: QTimer) -> None:
        if not timer.isActive():   # 每条连接只接收一篇
            return
        too_long = socket.bytesAvailable() > _MESSAGE_LIMIT
        if not too_long and not socket.canReadLine():
            return
        timer.stop()
        try:
            if too_long:
                raise ValueError("后台导入请求过长")
            request = json.loads(bytes(socket.readAll()).decode("utf-8"))
            if not isinstance(request, dict) or request.get("version") != 1:
                raise ValueError("不支持的后台导入请求")
            if Path(request["library"]) != self._library:
                raise ValueError("请求的文献库与当前打开的库不一致")
            folder = Path(request["folder"])
            if not folder.is_absolute():
                raise ValueError("成品文件夹必须为绝对路径")
            if self._is_busy and self._is_busy():
                raise ValueError("手动导入正在进行，请稍后重试。")
            result = import_bundle(self._ctx, folder)
        except Exception as exc:  # 单次导入或消息解析出错，只把错误交回这个客户端
            reply = _message({"error": str(exc)[:4096] or "后台导入失败"})
        else:
            try:
                reply = _message({"result": result})
            except ValueError:
                reply = _message({"error": _RESULT_UNKNOWN})
        socket.write(reply)
        socket.disconnectFromServer()   # Qt 会先发完回执再关闭

    def close(self) -> None:
        """停止接收请求，先于关闭 AppContext 和释放库锁执行。"""
        super().close()
        for socket in self.findChildren(QLocalSocket):
            socket.abort()


def import_from_running(library: Path, folder: Path) -> dict:
    """在无窗口的技能进程中提交一次；仅连接前的失败可安全切换到独占库的导入方式。"""
    app = QCoreApplication.instance() or QCoreApplication([])  # 保持引用直到套接字关闭
    library = library.resolve()
    name = _endpoint(library)
    request = _message({"version": 1, "library": str(library), "folder": str(folder.resolve())})
    socket = QLocalSocket()
    socket.setReadBufferSize(_MESSAGE_LIMIT + 1)
    try:
        # 程序启动时先拿库锁，再创建接收端。此处只重试连接，绝不重发请求。
        deadline = time.monotonic() + 3
        while True:
            socket.connectToServer(name)
            if socket.waitForConnected(200):
                break
            socket.abort()
            if time.monotonic() >= deadline:
                raise ImportServerUnavailable(
                    "目标库正被占用，无法连接后台导入入口。若运行的是旧版软件，请更新并重启一次。")
            time.sleep(0.1)

        if socket.write(request) != len(request):
            raise RuntimeError(_RESULT_UNKNOWN)
        while socket.bytesToWrite():
            if not socket.waitForBytesWritten(5000):
                raise RuntimeError(_RESULT_UNKNOWN)

        # 大附件的复制和校验可能较慢。回执丢失不代表事务失败，交由下次查重核实。
        deadline = time.monotonic() + 600
        while not socket.canReadLine():
            remaining = int((deadline - time.monotonic()) * 1000)
            if socket.bytesAvailable() > _MESSAGE_LIMIT or remaining <= 0:
                raise RuntimeError(_RESULT_UNKNOWN)
            if not socket.waitForReadyRead(remaining) and not socket.canReadLine():
                raise RuntimeError(_RESULT_UNKNOWN)
        if socket.bytesAvailable() > _MESSAGE_LIMIT:
            raise RuntimeError(_RESULT_UNKNOWN)
        try:
            reply = json.loads(bytes(socket.readLine()).decode("utf-8"))
        except (ValueError, RecursionError) as exc:
            raise RuntimeError(_RESULT_UNKNOWN) from exc
        if not isinstance(reply, dict):
            raise RuntimeError(_RESULT_UNKNOWN)
        if "error" in reply:
            raise RuntimeError(str(reply["error"]))
        result = reply.get("result")
        if not isinstance(result, dict) or result.get("status") not in ("imported", "duplicate"):
            raise RuntimeError(_RESULT_UNKNOWN)
        if not isinstance(result.get("library"), str) or Path(result["library"]) != library:
            raise RuntimeError(_RESULT_UNKNOWN)
        return result
    finally:
        socket.abort()
        del app
