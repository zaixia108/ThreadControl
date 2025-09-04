

# tdmgm

python线程控制，使用ctypes实现即时线程还在运行中，也可以强行终止线程运行。

## 特性

- 线程控制工具类
- 支持循环线程和一次性线程
- 便捷的线程管理与结果获取

## 安装

推荐使用 pip 安装（需先打包或上传到 PyPI）：

```bash
pip install tdmgm
```

或直接在本地项目中使用：

```bash
git clone https://github.com/zaixia108/ThreadControl.git
cd ThreadControl
pip install .
```

## 目录结构

```
tdmgm/
├── __init__.py
├── CycleThread.py
├── OnceThread.py
├── thread_utils.py
```

## 快速上手

```python
from tdmgm.CycleThread import CycleThread
from tdmgm.OnceThread import OnceThread

def my_task():
    print("线程任务执行中")

# 循环线程示例
cycle = CycleThread(target=my_task, name="循环线程")
cycle.start()

# 一次性线程示例
once = OnceThread(target=my_task, name="一次性线程")
once.start()
```

## 许可证

MIT License

## 作者

zaixia108  
邮箱: xvbowen2012@gmail.com

## 项目主页

[https://github.com/zaixia108/ThreadControl](https://github.com/zaixia108/ThreadControl)
```
此文件保存为 `README.md`，放在项目根目录即可。