"""循环执行线程"""
from __future__ import annotations

import functools
from typing import Callable, Optional

from .base import BaseThread, ThreadStatus, Signal
from .registry import ThreadRegistry, global_registry


class CycleThread(BaseThread):
    """
    循环执行线程，支持暂停、恢复、停止操作

    示例: 
        >>> def task():
        ...     print("执行任务")
        ...     return None  # 返回 'end' 或 Signal.STOP 停止线程

        >>> thread = CycleThread(task, name='my_task').start()
        >>> thread.pause()
        >>> thread.resume()
        >>> thread.stop()

        # 使用装饰器
        >>> @CycleThread.as_thread(name='background')
        ... def background_task():
        ...     print("后台任务")

        # 使用上下文管理器
        >>> with CycleThread(task) as t:
        ...     time.sleep(5)
        # 自动停止
    """

    _registry: ThreadRegistry = global_registry

    def __init__(
            self,
            func: Callable,
            name: Optional[str] = None,
            daemon: bool = False,
            error_handler: Optional[Callable[[Exception], None]] = None,
            stop_on_error: bool = False,
            interval: float = 0.0,  # 新增：循环间隔
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
        self._interval = interval
        self._registry = global_registry

    def _run_loop(self):
        """循环执行用户函数"""
        import time

        while self._running.is_set():
            # 检查暂停状态
            self._paused.wait()

            if not self._running.is_set():
                break

            try:
                result = self._execute_func()

                # 检查是否需要停止
                signal = Signal.from_return(result)
                if signal == Signal.STOP:
                    break

            except Exception as e:
                self._handle_error(e)
                if self._stop_on_error:
                    break

            # 循环间隔
            if self._interval > 0:
                time.sleep(self._interval)

    @classmethod
    def as_thread(
            cls,
            name: Optional[str] = None,
            daemon: bool = False,
            interval: float = 0.0,
            auto_start: bool = True,
            **kwargs
    ):
        """
        装饰器：将函数转换为循环线程

        Args: 
            name: 线程名称
            daemon: 是否守护线程
            interval: 循环间隔（秒）
            auto_start: 是否自动启动
        """

        def decorator(func: Callable) -> CycleThread:
            @functools.wraps(func)
            def wrapper(*args, **kw) -> CycleThread:
                thread = cls(
                    func=func,
                    name=name,
                    daemon=daemon,
                    interval=interval,
                    *args,
                    **{**kwargs, **kw}
                )
                if auto_start:
                    thread.start()
                return thread

            return wrapper()

        return decorator

    # 类方法：访问注册表
    @classmethod
    def get_thread(cls, name: str) -> Optional["CycleThread"]:
        """从注册表获取线程"""
        thread = cls._registry.get(name)
        if isinstance(thread, cls):
            return thread
        return None

    @classmethod
    def get_all_threads(cls) -> dict:
        """获取所有 CycleThread 实例"""
        return {
            name: t for name, t in cls._registry.get_all().items()
            if isinstance(t, cls)
        }