"""线程安全的线程注册表"""
from __future__ import annotations

import threading
from typing import Dict, Optional, Iterator, TYPE_CHECKING
from weakref import WeakValueDictionary

if TYPE_CHECKING:
    from .base import BaseThread


class ThreadRegistry:
    """
    线程安全的线程注册表

    使用弱引用避免阻止线程对象被垃圾回收
    """

    def __init__(self):
        self._threads: WeakValueDictionary[str, "BaseThread"] = WeakValueDictionary()
        self._lock = threading.RLock()

    def register(self, thread: "BaseThread") -> None:
        """注册线程"""
        with self._lock:
            if thread.name in self._threads:
                raise ValueError(f"Thread with name '{thread.name}' already exists")
            self._threads[thread.name] = thread

    def unregister(self, name: str) -> Optional["BaseThread"]:
        """注销线程"""
        with self._lock:
            return self._threads.pop(name, None)

    def get(self, name: str) -> Optional["BaseThread"]:
        """获取线程"""
        with self._lock:
            return self._threads.get(name)

    def get_all(self) -> Dict[str, "BaseThread"]:
        """获取所有线程的副本"""
        with self._lock:
            return dict(self._threads)

    def stop_all(self, force: bool = False, timeout: float = 5.0) -> None:
        """停止所有线程"""
        threads = self.get_all()
        for thread in threads.values():
            thread.stop(force=force, timeout=timeout)

    def __len__(self) -> int:
        with self._lock:
            return len(self._threads)

    def __iter__(self) -> Iterator["BaseThread"]:
        with self._lock:
            return iter(list(self._threads.values()))

    def __contains__(self, name: str) -> bool:
        with self._lock:
            return name in self._threads


# 全局注册表实例
global_registry = ThreadRegistry()