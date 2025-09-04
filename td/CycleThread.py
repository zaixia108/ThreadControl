import threading
import ctypes
import inspect
import functools
import time
from typing import Callable, Any, Optional, Dict, List, Union
from enum import Enum
from .thread_utils import generate_random_name

class ThreadStatus(Enum):
    """线程状态枚举"""
    RUNNING = 1  # 运行中
    PAUSED = 2  # 已暂停
    STOPPED = 3  # 已停止
    ERROR = 4  # 出错


class CycleThread:
    """
    可控制循环线程类，支持暂停、恢复、停止等操作。

    使用示例:
        # 基本用法
        def print_time():
            print(time.time())
            return None  # 返回'end'将停止线程

        # 创建并启动线程
        thread = CycleThread(func=print_time, name='print_time')

        # 暂停线程
        thread.pause()

        # 恢复线程
        thread.resume()

        # 停止线程
        thread.stop()

        # 使用with语句
        with CycleThread(func=print_time, name='print_time') as t:
            time.sleep(5)  # 运行5秒
        # 退出with块后线程自动停止

        # 使用装饰器
        @CycleThread.as_thread(name='decorated_thread')
        def background_task():
            print("Running in background")

        # 获取线程池中的线程
        thread = CycleThread.get_thread('thread_name')
    """

    # 线程池，存储所有创建的线程实例
    _thread_pool: Dict[str, 'CycleThread'] = {}

    def __init__(self,
                 func: Callable,
                 name: Optional[str] = None,
                 daemon: bool = False,
                 error_stop: bool = False,
                 error_callback: Optional[Callable] = None,
                 *args,
                 **kwargs):
        """
        初始化循环线程

        Args:
            func: 要执行的函数
            name: 线程名称，默认自动生成32位随机字符串
            daemon: 是否为守护线程，默认False
            error_stop: 出错时是否停止线程，默认False
            error_callback: 错误回调函数，接收异常作为参数，默认None
            *args: 传递给func的位置参数
            **kwargs: 传递给func的关键字参数
        """
        self.func = func
        # 如果未提供名称，则生成随机名称
        self.name = name if name is not None else generate_random_name()
        self.args = args
        self.kwargs = kwargs
        self.error_stop = error_stop
        self.error_callback = error_callback
        self.result = None
        self.last_error = None
        self._status = ThreadStatus.RUNNING

        # 控制线程的事件标志
        self.__flag = threading.Event()
        self.__flag.set()  # 设置为True
        self.__running = threading.Event()
        self.__running.set()  # 将running设置为True

        # 创建并启动线程
        self.thread = threading.Thread(target=self.run, name=self.name)
        self.thread.daemon = daemon
        self.thread.start()

        # 将线程添加到线程池
        CycleThread._thread_pool[self.name] = self

    def run(self):
        """线程运行的主函数，不应直接调用"""
        while self.__running.is_set():
            self.__flag.wait()  # 为True时立即返回, 为False时阻塞

            try:
                ret = self.func(*self.args, **self.kwargs)
                self.result = ret

                # 如果返回值是'end'，停止线程
                if ret == 'end':
                    self.stop()
                    break

            except Exception as e:
                self.last_error = e
                if self.error_callback:
                    self.error_callback(e)
                else:
                    print(f"异常发生在线程 {self.name}: {e}")

                if self.error_stop:
                    self._status = ThreadStatus.ERROR
                    self.stop()
                    break

    def pause(self):
        """暂停线程运行"""
        self.__flag.clear()
        self._status = ThreadStatus.PAUSED
        return self

    def resume(self):
        """恢复线程运行"""
        self.__flag.set()
        self._status = ThreadStatus.RUNNING
        return self

    def stop(self):
        """停止线程运行"""
        self.__flag.set()  # 确保线程不处于阻塞状态
        self.__running.clear()
        self._status = ThreadStatus.STOPPED
        self._safe_terminate(self.thread)

        # 从线程池中移除
        if self.name in CycleThread._thread_pool:
            del CycleThread._thread_pool[self.name]

        return self

    def get_result(self):
        """获取线程函数的返回结果"""
        return self.result

    def is_alive(self):
        """检查线程是否仍在运行"""
        return self.thread.is_alive()

    def get_status(self):
        """获取线程当前状态"""
        return self._status

    def _safe_terminate(self, thread):
        """安全终止线程"""
        if not thread.is_alive():
            return

        def _async_raise(tid, exctype):
            """向线程抛出异常"""
            tid = ctypes.c_long(tid)
            if not inspect.isclass(exctype):
                exctype = type(exctype)
            res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
            if res == 0:
                return False  # 线程ID无效
            elif res != 1:
                # 如果返回值不为1，说明出现了错误，需要清除异常状态
                ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
                return False
            return True

        try:
            success = _async_raise(thread.ident, SystemExit)
            if not success:
                print(f"警告: 无法终止线程 {self.name}")
        except Exception as e:
            print(f"终止线程时出错: {e}")

    def __enter__(self):
        """支持with语句的上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持with语句的上下文管理器退出"""
        self.stop()
        return False  # 允许异常传播

    @classmethod
    def as_thread(cls, name=None, daemon=False, error_stop=False, error_callback=None):
        """
        将函数转换为循环线程的装饰器

        Args:
            name: 线程名称，默认自动生成随机名称
            daemon: 是否为守护线程
            error_stop: 出错时是否停止线程
            error_callback: 错误回调函数

        Returns:
            装饰器函数
        """

        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                thread = cls(func=func, name=name, daemon=daemon,
                             error_stop=error_stop, error_callback=error_callback,
                             *args, **kwargs)
                return thread

            # 立即执行并返回线程实例
            return wrapper()

        return decorator

    @classmethod
    def get_thread(cls, name):
        """
        从线程池中获取线程实例

        Args:
            name: 线程名称

        Returns:
            CycleThread实例或None
        """
        return cls._thread_pool.get(name)

    @classmethod
    def get_all_threads(cls):
        """
        获取所有活动线程

        Returns:
            线程字典，键为线程名，值为线程实例
        """
        return cls._thread_pool.copy()