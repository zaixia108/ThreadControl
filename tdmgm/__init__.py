"""
线程控制系统 - 提供易于使用的线程管理工具

此包提供了两种线程类:
- CycleThread: 循环执行的线程，支持暂停、恢复和停止操作
- OnceThread: 单次执行的线程，执行完成后自动终止

示例:
    from thread_control import CycleThread, OnceThread

    # 使用循环线程
    def periodic_task():
        print("定期执行的任务")

    cycle_thread = CycleThread(func=periodic_task, name='periodic')

    # 使用单次执行线程
    def one_time_task():
        return "任务完成"

    once_thread = OnceThread(func=one_time_task, name='one_time')
    result = once_thread.wait_for_result()
"""

import threading
import ctypes
import inspect
import functools
import time
from typing import Callable, Any, Optional, Dict, List, Union
from enum import Enum
from .thread_utils import generate_random_name
# 导入两个线程类
from .CycleThread import CycleThread, ThreadStatus as CycleThreadStatus
from .OnceThread import OnceThread, ThreadStatus as OnceThreadStatus

__version__ = '1.0.0'
__author__ = 'zaixia108'

# 指定公开的API
__all__ = [
    'CycleThread',
    'OnceThread',
    'CycleThreadStatus',
    'OnceThreadStatus',
    'create_cycle_thread',
    'create_once_thread',
    'get_thread',
    'stop_all_threads'
]

# 全局线程注册表
_threads = {}

# 更新公开的API列表
__all__ = [
    'CycleThread',
    'OnceThread',
    'CycleThreadStatus',
    'OnceThreadStatus',
    'create_cycle_thread',
    'create_once_thread',
    'get_thread',
    'stop_all_threads',
    'generate_random_name'  # 添加生成随机名称函数到公开API
]


def create_cycle_thread(func, name=None, **kwargs):
    """
    创建并返回一个循环执行的线程

    Args:
        func: 要执行的函数
        name: 线程名称，默认自动生成随机名称
        **kwargs: 传递给CycleThread构造函数的其他参数

    Returns:
        CycleThread实例
    """
    # 不需要从函数名生成默认名称，因为类构造函数会处理这种情况
    thread = CycleThread(func=func, name=name, **kwargs)
    _threads[thread.name] = thread  # 使用实际线程名(可能是生成的)
    return thread


def create_once_thread(func, name=None, **kwargs):
    """
    创建并返回一个单次执行的线程

    Args:
        func: 要执行的函数
        name: 线程名称，默认自动生成随机名称
        **kwargs: 传递给OnceThread构造函数的其他参数

    Returns:
        OnceThread实例
    """
    # 不需要从函数名生成默认名称，因为类构造函数会处理这种情况
    thread = OnceThread(func=func, name=name, **kwargs)
    _threads[thread.name] = thread  # 使用实际线程名(可能是生成的)
    return thread


def get_thread(name):
    """
    获取指定名称的线程

    Args:
        name: 线程名称

    Returns:
        线程实例或None
    """
    # 先检查CycleThread池
    thread = CycleThread.get_thread(name)
    if thread:
        return thread

    # 再检查OnceThread池
    thread = OnceThread.get_thread(name)
    if thread:
        return thread

    # 最后检查本地注册表
    return _threads.get(name)


def stop_all_threads():
    """
    停止所有已创建的线程
    """
    # 停止CycleThread池中的线程
    for name, thread in list(CycleThread.get_all_threads().items()):
        thread.stop()

    # 停止OnceThread池中的线程
    for name, thread in list(OnceThread.get_all_threads().items()):
        thread.stop()

    # 停止本地注册表中的线程
    for name, thread in list(_threads.items()):
        if hasattr(thread, 'stop'):
            thread.stop()