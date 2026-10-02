"""平台策略基类与注册表（platforms 包）。

- 基类 BasePlatform 与注册表在本文件；
- `platforms/adapters.py` 把各平台的 run() 桥接到
  NovalPublisherApp.automation_flow_by_* 方法。

还原自 PyInstaller 归档中的 `novel_publisher.platforms` 模块（Python 3.10 字节码），
其中 `BasePlatform` 是 ABC，方法 run() 由 register_platform 装饰的子类实现。
"""
from abc import ABC, abstractmethod
from typing import Dict, Type


class BasePlatform(ABC):
    """发布平台抽象基类。

    子类需实现 run() 方法，完成从加载配置到发布章节的完整流程。
    """
    name: str = ''

    @abstractmethod
    def run(self, app) -> bool:
        """执行发布流程。

        Args:
            app: NovelPublisherApp 实例，提供配置、浏览器、日志等能力

        Returns:
            True 表示成功，False 表示失败
        """


PLATFORMS: Dict[str, BasePlatform] = {}


def register_platform(cls: Type[BasePlatform]) -> Type[BasePlatform]:
    """装饰器：将平台类注册到 PLATFORMS。"""
    PLATFORMS[cls.name] = cls()
    return cls


def get_platform(name: str):
    """根据平台名获取平台实例。"""
    return PLATFORMS.get(name)


from . import adapters  # noqa: E402,F401  触发平台注册
