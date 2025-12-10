"""
ThreadControl - 易用的 Python 线程管理库

提供两种线程类型:
- CycleThread: 循环执行，支持暂停/恢复/停止
- OnceThread: 单次执行，支持结果等待

快速开始:
    >>> from tdmgm import CycleThread, OnceThread

    >>> # 循环线程
    >>> @CycleThread.as_thread(interval=1.0)
    ... def heartbeat():
    ...     print("ping")

    >>> # 单次线程
    >>> thread = OnceThread(lambda: 42).start()
    >>> result = thread.wait_for_result()
"""

__version__ = "1.1.0"
__author__ = "zaixia108"

from .base import ThreadStatus, Signal, ThreadResult, BaseThread
from .cycle_thread import CycleThread
from .once_thread import OnceThread
from .registry import ThreadRegistry, global_registry

__all__ = [
    # 核心类
    "CycleThread",
    "OnceThread",
    "BaseThread",
    # 数据类型
    "ThreadStatus",
    "Signal",
    "ThreadResult",
    # 注册表
    "ThreadRegistry",
    "global_registry",
    # 便捷函数
    "stop_all",
    "get_thread",
]


def stop_all(force: bool = False, timeout: float = 5.0) -> None:
    """停止所有已注册的线程"""
    global_registry.stop_all(force=force, timeout=timeout)


def get_thread(name: str) -> BaseThread | None:
    """根据名称获取线程"""
    return global_registry.get(name)