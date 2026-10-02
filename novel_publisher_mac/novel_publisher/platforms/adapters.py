"""平台适配器：将现有的 automation_flow_by_* 方法桥接到 BasePlatform 接口。

后续各平台逻辑可从此文件逐步迁出到独立模块。

每个平台类的 name（界面显示名）与 run() 绑定的 automation_flow 方法均按
adapters.pyc 中各类的 co_consts / co_names 逐条核对恢复。
"""
from . import BasePlatform, register_platform

@register_platform
class FanqiePlatform(BasePlatform):
    name = '番茄'

    def run(self, app) -> bool:
        return app.automation_flow_by_fanqienovel()

@register_platform
class QidianPlatform(BasePlatform):
    name = '起点'

    def run(self, app) -> bool:
        return app.automation_flow_by_qidiannovel()

@register_platform
class QyuePlatform(BasePlatform):
    name = 'Q阅'

    def run(self, app) -> bool:
        # 原程序此处同样绑定 qidian 流程（非笔误，按字节码保留）
        return app.automation_flow_by_qidiannovel()

@register_platform
class QimaoPlatform(BasePlatform):
    name = '七猫'

    def run(self, app) -> bool:
        return app.automation_flow_by_qimaonovel()

@register_platform
class ZonghengPlatform(BasePlatform):
    name = '纵横'

    def run(self, app) -> bool:
        # 原程序此处同样绑定 qimao 流程（非笔误，按字节码保留）
        return app.automation_flow_by_qimaonovel()

@register_platform
class FeiluPlatform(BasePlatform):
    name = '飞卢'

    def run(self, app) -> bool:
        return app.automation_flow_by_feilunovel()

@register_platform
class WechatPlatform(BasePlatform):
    name = '微信'

    def run(self, app) -> bool:
        return app.automation_flow_by_wechatnovel()

@register_platform
class ShuqiPlatform(BasePlatform):
    name = '书旗'

    def run(self, app) -> bool:
        return app.automation_flow_by_shuqinovel()

@register_platform
class JinjiangPlatform(BasePlatform):
    name = '晋江'

    def run(self, app) -> bool:
        return app.automation_flow_by_jinjiangnovel()

@register_platform
class XirangPlatform(BasePlatform):
    name = '息壤'

    def run(self, app) -> bool:
        return app.automation_flow_by_xirangnovel()

@register_platform
class MiguPlatform(BasePlatform):
    name = '咪咕'

    def run(self, app) -> bool:
        return app.automation_flow_by_migunovel()
