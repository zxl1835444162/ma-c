"""定时任务注册表与调度（tasks 包）。

- 注册表本体（register_task / get_task / list_task_names / execute_task）在本文件；
- `tasks/adapters.py` 把 NovalPublisherApp.scheduled_* 方法注册进来。

还原自 PyInstaller 归档中的 `novel_publisher.tasks` 模块（Python 3.10 字节码），
其中 `execute_task` 按指令流补全：`(func, threaded) = task`、`func(app)`。
"""
import threading
from typing import Callable, Dict, Optional

_TASKS: Dict[str, tuple] = {}


def register_task(name: str, threaded: bool = None) -> Callable:
    """装饰器：注册定时任务。

    Args:
        name: 任务名称（与界面下拉框对应）
        threaded: True 表示在子线程中执行，False 表示在主线程直接调用
    """
    def decorator(func: Callable):
        _TASKS[name] = (func, threaded)
        return func
    return decorator


def get_task(name: str):
    """获取任务 (执行函数, 是否子线程)。"""
    return _TASKS.get(name)


def list_task_names():
    """返回所有已注册的任务名。"""
    return list(_TASKS.keys())


def execute_task(name: str, app) -> bool:
    """执行指定任务。

    Returns:
        True 如果任务存在并已启动，False 如果任务不存在
    """
    task = get_task(name)
    if task is None:
        return False
    (func, threaded) = task
    if threaded:
        threading.Thread(target=func, args=(app,), daemon=True).start()
        return True
    func(app)
    return True


from . import adapters  # noqa: E402,F401  触发任务注册
