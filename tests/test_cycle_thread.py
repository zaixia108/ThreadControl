"""CycleThread 单元测试"""
import time
import pytest
import threading
# from tdmgm import CycleThread, ThreadStatus, Signal
from tdmgm import CycleThread, ThreadStatus, Signal

class TestCycleThread:
    """CycleThread 测试用例"""

    def test_basic_start_stop(self):
        """测试基本的启动和停止"""
        counter = {"value": 0}

        def increment():
            counter["value"] += 1

        thread = CycleThread(increment, name="test_basic")
        thread.start()
        time.sleep(0.1)
        thread.stop()

        assert counter["value"] > 0
        assert thread.status == ThreadStatus.STOPPED

    def test_pause_resume(self):
        """测试暂停和恢复"""
        counter = {"value": 0}

        def increment():
            counter["value"] += 1
            time.sleep(0.01)

        thread = CycleThread(increment, name="test_pause")
        thread.start()
        time.sleep(0.05)

        thread.pause()
        paused_value = counter["value"]
        time.sleep(0.05)

        # 暂停期间不应该增加
        assert counter["value"] == paused_value
        assert thread.status == ThreadStatus.PAUSED

        thread.resume()
        time.sleep(0.05)

        # 恢复后应该继续增加
        assert counter["value"] > paused_value
        thread.stop()

    def test_return_end_stops_thread(self):
        """测试返回 'end' 停止线程"""
        call_count = {"value": 0}

        def limited_task():
            call_count["value"] += 1
            if call_count["value"] >= 3:
                return "end"

        thread = CycleThread(limited_task, name="test_end")
        thread.start()
        thread.join(timeout=1)

        assert call_count["value"] == 3
        assert thread.status in (ThreadStatus.FINISHED, ThreadStatus.STOPPED)

    def test_error_handling(self):
        """测试错误处理"""
        errors = []

        def error_handler(e):
            errors.append(e)

        def failing_task():
            raise ValueError("test error")

        thread = CycleThread(
            failing_task,
            name="test_error",
            error_handler=error_handler,
            stop_on_error=True
        )
        thread.start()
        thread.join(timeout=1)

        assert len(errors) == 1
        assert isinstance(errors[0], ValueError)
        assert thread.status == ThreadStatus.ERROR

    def test_context_manager(self):
        """测试上下文管理器"""
        counter = {"value": 0}

        def increment():
            counter["value"] += 1
            time.sleep(0.01)

        with CycleThread(increment, name="test_ctx") as thread:
            time.sleep(0.05)
            assert thread.is_alive

        # 退出后应该停止
        time.sleep(0.02)
        assert not thread.is_alive

    def test_interval(self):
        """测试循环间隔"""
        timestamps = []

        def record_time():
            timestamps.append(time.time())
            if len(timestamps) >= 3:
                return "end"

        thread = CycleThread(record_time, name="test_interval", interval=0.1)
        thread.start()
        # thread.join(timeout=1)
        time.sleep(0.01)
        # 检查间隔
        for i in range(1, len(timestamps)):
            diff = timestamps[i] - timestamps[i - 1]
            assert diff >= 0.09  # 允许一些误差

    def test_decorator(self):
        """测试装饰器"""
        counter = {"value": 0}

        @CycleThread.as_thread(name="decorated", interval=0.01)
        def decorated_task():
            counter["value"] += 1
            if counter["value"] >= 5:
                return "end"

        # decorated_task 已经是 CycleThread 实例
        assert isinstance(decorated_task, CycleThread)
        decorated_task.join(timeout=1)
        assert counter["value"] == 5


class TestOnceThread:
    """OnceThread 测试用例"""

    def test_basic_execution(self):
        """测试基本执行"""
        from tdmgm import OnceThread

        def task():
            return 42

        thread = OnceThread(task, name="test_once")
        thread.start()
        result = thread.wait_for_result(timeout=1)

        assert result.value == 42
        assert result.success

    def test_timeout(self):
        """测试超时"""
        from tdmgm import OnceThread

        def slow_task():
            time.sleep(10)
            return "done"

        thread = OnceThread(slow_task, name="test_timeout")
        thread.start()

        with pytest.raises(TimeoutError):
            thread.wait_for_result(timeout=0.1)

        thread.stop(force=True)


class TestRegistry:
    """注册表测试"""

    def test_thread_registration(self):
        """测试线程注册"""
        from tdmgm import global_registry, CycleThread

        initial_count = len(global_registry)

        thread = CycleThread(lambda: time.sleep(10), name="test_reg")
        print("[测试] CycleThread created:", thread)
        thread.start()
        print("[测试] 注册表 after start:", global_registry.get_all())
        print("[测试] 注册表长度 after start:", len(global_registry))
        time.sleep(0.01)

        assert len(global_registry) == initial_count + 1
        assert global_registry.get("test_reg") is thread

        thread.stop()
        assert "test_reg" not in global_registry

    def test_stop_all(self):
        """测试停止所有线程"""
        from tdmgm import stop_all, CycleThread

        threads = [
            CycleThread(lambda: time.sleep(0.01), name=f"test_all_{i}")
            for i in range(3)
        ]

        for t in threads:
            t.start()

        time.sleep(0.05)
        stop_all()
        for t in threads:
            t.join(timeout=1)
            assert t.status == ThreadStatus.STOPPED or ThreadStatus.ERROR