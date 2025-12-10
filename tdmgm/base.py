from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Optional, Any, TYPE_CHECKING
from abc import ABC, abstractmethod
import threading
import ctypes
import logging

ENDSIGN = "end"

if TYPE_CHECKING:
    from .registry import ThreadRegistry

logger = logging.getLogger(__name__)


class ThreadStatus(Enum):
    CREATED = auto()
    RUNNING = auto()
    PAUSED = auto()
    STOPPING = auto()
    STOPPED = auto()
    FINISHED = auto()  # 仅适用一次性线程
    ERROR = auto()

class Signal(Enum):
    CONTINUE = auto()
    STOP = auto()

    @classmethod
    def from_return(cls, value: Any) -> 'Signal':
        if value == ENDSIGN:
            return cls.STOP
        return cls.CONTINUE

@dataclass
class ThreadResult:
    value: Any = None
    error: Optional[Exception] = None
    status: ThreadStatus = ThreadStatus.CREATED

    @property
    def success(self) -> bool:
        return self.error is None and self.status in (ThreadStatus.FINISHED, ThreadStatus.STOPPED)

class BaseThread(ABC):

    _registry: Optional["ThreadRegistry"]

    def __init__(self,
        func: Callable,
        name: Optional[str] = None,
        daemon: bool = False,
        error_handler: Optional[Callable[[Exception], None]] = None,
        stop_on_error: bool = False,
         *args,
        **kwargs
    ):
        self._func = func
        self._name = name or self._generate_name()
        self.args = args
        self.kwargs = kwargs
        self._daemon = daemon
        self._error_handler = error_handler
        self._stop_on_error = stop_on_error


        #状态管理
        self._status = ThreadStatus.CREATED
        self._result = ThreadResult()
        self._status_lock = threading.Lock()

        #控制信号
        self._running = threading.Event()
        self._paused = threading.Event()
        self._paused.set()

        #线程对象
        self._thread: Optional[threading.Thread] = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def status(self) -> ThreadStatus:
        with self._status_lock:
            return self._status

    @status.setter
    def status(self, value: ThreadStatus):
        with self._status_lock:
            old_status = self._status
            self._status = value
            logger.debug(f'Thread {self.name} status: {old_status} -> {value}')

    @property
    def result(self) -> ThreadResult:
        with self._status_lock:
            return self._result

    @property
    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> "BaseThread":
        """启动线程"""

        if self._thread is not None:
            raise RuntimeError(f"Thread '{self._name}' already started")

        self._running.set()
        self._thread = threading.Thread(
            target=self._safe_run,
            name=self._name,
            daemon=self._daemon
        )
        self.status = ThreadStatus.RUNNING
        self._thread.start()

        # 注册到注册表
        if self._registry is not None:
            self._registry.register(self)

        return self

    def pause(self) -> "BaseThread":
        """暂停线程"""
        if self.status != ThreadStatus.RUNNING:
            logger.warning(f"Cannot pause thread '{self._name}' in status {self.status.name}")
            return self

        self._paused.clear()
        self.status = ThreadStatus.PAUSED
        return self

    def resume(self) -> "BaseThread":
        """恢复线程"""
        if self.status != ThreadStatus.PAUSED:
            logger.warning(f"Cannot resume thread '{self._name}' in status {self.status.name}")
            return self

        self._paused.set()
        self.status = ThreadStatus.RUNNING
        return self

    def stop(self, force: bool = False, timeout: float = 5.0) -> "BaseThread":
        """
        停止线程

        Args:
            force: 是否强制终止（使用 ctypes 注入异常）
            timeout: 等待线程结束的超时时间
        """
        if self.status in (ThreadStatus.STOPPED, ThreadStatus.FINISHED):
            return self

        self.status = ThreadStatus.STOPPING
        self._running.clear()
        self._paused.set()  # 确保不阻塞在暂停状态

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

            # 如果线程仍在运行且需要强制终止
            if self._thread.is_alive() and force:
                logger.warning(f"Force terminating thread '{self._name}'")
                self._force_terminate()

        self.status = ThreadStatus.STOPPED

        # 从注册表移除
        if self._registry:
            self._registry.unregister(self._name)

        return self

    def join(self, timeout: Optional[float] = None) -> "BaseThread":
        """等待线程结束"""
        if self._thread:
            self._thread.join(timeout=timeout)
        return self

    def _safe_run(self):
        """线程的实际运行逻辑"""
        try:
            self._run_loop()
        except SystemExit:
            logger.debug(f'Thread {self.name} received SystemExit')
        except Exception as e:
            self._handle_error(e)
        finally:
            if self.status not in (ThreadStatus.STOPPED, ThreadStatus.FINISHED, ThreadStatus.ERROR):
                self.status = ThreadStatus.FINISHED

    @abstractmethod
    def _run_loop(self):
        """
        线程的实际运行逻辑

        子类需要实现这个方法来定义线程的行为
        """
        pass

    def _execute_func(self) -> Any:
        """执行线程函数"""
        result = self._func(*self.args, **self.kwargs)
        self._result.value = result
        return result

    def _handle_error(self, error: Exception):
        """统一错误处理"""
        logger.error(f'Error in thread {self.name}: {error}', exc_info=True)
        self._result.error = error
        self._result.status = ThreadStatus.ERROR

        if self._error_handler:
            try:
                self._error_handler(error)
            except Exception as handler_error:
                logger.error(f"Error handler failed: {handler_error}")
        if self._stop_on_error:
            self.status = ThreadStatus.ERROR
            self._running.clear()

    def _force_terminate(self):
        """强制终止线程（危险操作）"""
        if not self._thread or not self._thread.is_alive():
            return

        tid = self._thread.ident
        if tid is None:
            return

        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
            ctypes.c_ulong(tid),
            ctypes.py_object(SystemExit)
        )

        if res == 0:
            logger.error(f"Invalid thread id {tid}")
        elif res > 1:
            # 异常情况，需要清除
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(tid), None)
            logger.error(f"Failed to terminate thread '{self._name}'")

    @staticmethod
    def _generate_name(length: int = 16) -> str:
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    # 上下文管理器支持
    def __enter__(self) -> "BaseThread":
        if self.status == ThreadStatus.CREATED:
            self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.stop()
        return False

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name='{self._name}' status={self.status.name}>"

