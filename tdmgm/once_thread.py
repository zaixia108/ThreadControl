"""单次执行线程"""
from __future__ import annotations

import functools
import threading
from typing import Callable, Optional, Any

from .base import BaseThread, ThreadStatus
from .registry import ThreadRegistry, global_registry


class OnceThread(BaseThread):
    """
    单次执行线程，执行完成后自动结束

    示例: 
        >>> def task():
        ...     return "完成"

        >>> thread = OnceThread(task, name='once').start()
        >>> result = thread.wait_for_result(timeout=10)
        >>> print(result. value)  # "完成"
    """

    _registry: ThreadRegistry = global_registry

    def __init__(
            self,
            func: Callable,
            name: Optional[str] = None,
            daemon: bool = True,  # OnceThread 默认为守护线程
            error_handler: Optional[Callable[[Exception], None]] = None,
            stop_on_error: bool = False,
            *args,
            **kwargs
    ):
        super().__init__(
            func=func,
            name=name,
            daemon=daemon,
            error_handler=error_handler,
            stop_on_error=stop_on_error,
            *args,
            **kwargs
        )
        self._completed = threading.Event()
        self._registry = global_registry

    def _run_loop(self):
        """执行一次用户函数"""
        try:
            self._execute_func()
            self._result.status = ThreadStatus.FINISHED
        finally:
            self._completed.set()

    def wait_for_result(self, timeout: Optional[float] = None) -> Any:
        """
        等待线程完成并返回结果

        Args:
            timeout: 超时时间（秒），None 表示无限等待

        Returns:
            ThreadResult 对象

        Raises:
            TimeoutError: 等待超时
        """
        if not self._completed.wait(timeout=timeout):
            raise TimeoutError(f"Thread '{self._name}' did not complete within {timeout}s")
        return self._result

    @property
    def is_completed(self) -> bool:
        """检查是否已完成"""
        return self._completed.is_set()

    @classmethod
    def as_thread(
            cls,
            name: Optional[str] = None,
            daemon: bool = True,
            auto_start: bool = True,
            **kwargs
    ):
        """装饰器：将函数转换为单次执行线程"""

        def decorator(func: Callable) -> OnceThread:
            @functools.wraps(func)
            def wrapper(*args, **kw) -> OnceThread:
                thread = cls(
                    func=func,
                    name=name,
                    daemon=daemon,
                    *args,
                    **{**kwargs, **kw}
                )
                if auto_start:
                    thread.start()
                return thread

            return wrapper()

        return decorator

    @classmethod
    def get_thread(cls, name: str) -> Optional["OnceThread"]:
        thread = cls._registry.get(name)
        if isinstance(thread, cls):
            return thread
        return None

    @classmethod
    def get_all_threads(cls) -> dict:
        return {
            name: t for name, t in cls._registry.get_all().items()
            if isinstance(t, cls)
        }