"""浏览器路径检测模块（macOS / Windows 双平台）。

原版 browser_detector.py 只读 Windows 注册表、只探测 .exe 路径，在 macOS 上
完全失效。本模块保持对外接口（BrowserDetector 的六个方法名与返回类型）不变，
内部按运行平台选择探测策略：

  * Windows：沿用原版注册表 + 默认安装路径逻辑；
  * macOS  ：探测 /Applications 下的 Chrome / Edge / Chromium / Brave / Vivaldi，
             以及用户目录 ~/Applications 的安装；返回 .app 包内的可执行文件路径。

返回值语义与原版一致：可直接传给 playwright 的 `executable_path`，
或用于 `--remote-debugging-port` 启动浏览器分身。
"""
import os
import sys
import platform
from typing import List, Optional, Dict

IS_MAC = sys.platform == 'darwin'
IS_WIN = sys.platform.startswith('win')

# ---------------------------------------------------------------------------
# macOS：.app 包内的可执行文件名与候选安装位置
# ---------------------------------------------------------------------------
MAC_BROWSERS = {
    'Chrome': {
        'bundle': 'Google Chrome.app',
        'exe': 'Contents/MacOS/Google Chrome',
        'roots': ['/Applications', os.path.expanduser('~/Applications')],
    },
    'Edge': {
        'bundle': 'Microsoft Edge.app',
        'exe': 'Contents/MacOS/Microsoft Edge',
        'roots': ['/Applications', os.path.expanduser('~/Applications')],
    },
    'Edge Dev': {
        'bundle': 'Microsoft Edge Dev.app',
        'exe': 'Contents/MacOS/Microsoft Edge Dev',
        'roots': ['/Applications', os.path.expanduser('~/Applications')],
    },
    'Chromium': {
        'bundle': 'Chromium.app',
        'exe': 'Contents/MacOS/Chromium',
        'roots': ['/Applications', os.path.expanduser('~/Applications')],
    },
    'Brave': {
        'bundle': 'Brave Browser.app',
        'exe': 'Contents/MacOS/Brave Browser',
        'roots': ['/Applications', os.path.expanduser('~/Applications')],
    },
    'Vivaldi': {
        'bundle': 'Vivaldi.app',
        'exe': 'Contents/MacOS/Vivaldi',
        'roots': ['/Applications', os.path.expanduser('~/Applications')],
    },
}

# ---------------------------------------------------------------------------
# Windows：与原版一致的注册表键与默认路径
# ---------------------------------------------------------------------------
WIN_BROWSERS = {
    'Chrome': {
        'registry_paths': [
            'Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\chrome.exe',
            'SOFTWARE\\Clients\\StartMenuInternet\\Google Chrome\\shell\\open\\command',
        ],
        'default_paths': [
            'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
            'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
            '%LOCALAPPDATA%\\Google\\Chrome\\Application\\chrome.exe',
        ],
    },
    'Edge': {
        'registry_paths': [
            'Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\msedge.exe',
            'SOFTWARE\\Clients\\StartMenuInternet\\Microsoft Edge\\shell\\open\\command',
        ],
        'default_paths': [
            'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
            'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
            'C:\\Program Files (x86)\\Microsoft\\Edge Dev\\Application\\msedge.exe',
            'C:\\Program Files\\Microsoft\\Edge Dev\\Application\\msedge.exe',
        ],
    },
    'Edge Dev': {
        'registry_paths': [
            'Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\msedge.exe',
        ],
        'default_paths': [
            'C:\\Program Files (x86)\\Microsoft\\Edge Dev\\Application\\msedge.exe',
            'C:\\Program Files\\Microsoft\\Edge Dev\\Application\\msedge.exe',
        ],
    },
    'Chromium': {
        'registry_paths': [
            'Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\chromium.exe',
        ],
        'default_paths': [
            'C:\\Program Files\\Chromium\\Application\\chromium.exe',
            'C:\\Program Files (x86)\\Chromium\\Application\\chromium.exe',
        ],
    },
}

class BrowserDetector:
    """跨平台浏览器路径检测器。"""

    BROWSER_REGISTRY_PATHS = WIN_BROWSERS if IS_WIN else {}
    BROWSER_MAC_PATHS = MAC_BROWSERS

    # ---------------------------------------------------------------- helpers

    @staticmethod
    def _expand_environment_variables(path: str) -> str:
        """展开环境变量（Windows 的 %VAR%、类 Unix 的 $VAR 都支持）。"""
        return os.path.expandvars(os.path.expanduser(path))

    @staticmethod
    def _check_file_exists(file_path: str) -> bool:
        """检查文件是否存在且可执行（macOS 下不要求 .exe 后缀）。"""
        if not file_path:
            return False
        file_path = BrowserDetector._expand_environment_variables(file_path)
        if not os.path.isfile(file_path):
            return False
        if os.name == 'nt':
            return file_path.lower().endswith('.exe')
        return os.access(file_path, os.X_OK)

    @staticmethod
    def _read_registry_value(key_path: str, value_name: str = ''):
        """读取 Windows 注册表值；非 Windows 平台直接返回 None。"""
        if not IS_WIN:
            return None
        try:
            import winreg  # noqa: WPS433  仅在 Windows 上可用
        except ImportError:
            return None
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)
            value = winreg.QueryValueEx(key, value_name)[0]
            winreg.CloseKey(key)
        except OSError:
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path)
                value = winreg.QueryValueEx(key, value_name)[0]
                winreg.CloseKey(key)
            except OSError:
                return None
        # 注册表里存的可能是 `"C:\path\chrome.exe" -- "%1"` 这种命令串
        if isinstance(value, str) and '"' in value:
            parts = value.split('"')
            if len(parts) > 1 and parts[1]:
                value = parts[1]
        elif isinstance(value, str) and value.lower().endswith('.exe') is False:
            first = value.split(' ')[0].strip()
            if first:
                value = first
        return value

    # ------------------------------------------------------------- detection

    @staticmethod
    def detect_browser_path(browser_name: str) -> Optional[str]:
        """检测指定浏览器的可执行文件路径，找不到返回 None。"""
        if IS_WIN:
            info = WIN_BROWSERS.get(browser_name)
            if not info:
                return None
            for reg_path in info['registry_paths']:
                path = BrowserDetector._read_registry_value(reg_path, '')
                if path and BrowserDetector._check_file_exists(path):
                    print(f'从注册表找到 {browser_name}: {path}')
                    return path
            for default_path in info['default_paths']:
                if BrowserDetector._check_file_exists(default_path):
                    print(f'从默认路径找到 {browser_name}: {default_path}')
                    return BrowserDetector._expand_environment_variables(default_path)
            return None

        info = MAC_BROWSERS.get(browser_name)
        if not info:
            return None
        for root in info['roots']:
            candidate = os.path.join(root, info['bundle'], info['exe'])
            if BrowserDetector._check_file_exists(candidate):
                print(f'在 {root} 找到 {browser_name}: {candidate}')
                return candidate
        return None

    @staticmethod
    def detect_all_browsers() -> Dict[str, str]:
        """检测所有可用的浏览器，返回 {名称: 可执行文件路径}。"""
        available_browsers = {}
        names = (list(WIN_BROWSERS) if IS_WIN else list(MAC_BROWSERS))
        print('开始检测可用的浏览器...')
        for browser_name in names:
            path = BrowserDetector.detect_browser_path(browser_name)
            if path:
                available_browsers[browser_name] = path
                print(f'✓ 找到 {browser_name}: {path}')
                continue
            print(f'✗ 未找到 {browser_name}')
        return available_browsers

    @staticmethod
    def get_recommended_browser() -> Optional[str]:
        """按优先级推荐一个浏览器路径。"""
        priority_order = ['Edge Dev', 'Edge', 'Chrome', 'Chromium', 'Brave', 'Vivaldi']
        available_browsers = BrowserDetector.detect_all_browsers()
        for browser_name in priority_order:
            if browser_name in available_browsers:
                recommended_path = available_browsers[browser_name]
                print(f'推荐使用 {browser_name}: {recommended_path}')
                return recommended_path
        print('未找到任何可用的浏览器')
        return None

    @staticmethod
    def get_browser_info() -> str:
        """返回人类可读的检测结果。"""
        available_browsers = BrowserDetector.detect_all_browsers()
        if not available_browsers:
            return '未检测到任何可用的浏览器\n请手动配置浏览器路径'
        info = ''
        for browser_name, path in available_browsers.items():
            info += f'  {browser_name}: {path}\n'
        recommended = BrowserDetector.get_recommended_browser()
        if recommended:
            info += f'\n推荐使用: {recommended}'
        return info

def test_browser_detection():
    """测试浏览器检测功能。"""
    print('=== 浏览器路径检测测试 ===')
    print(f'平台: {platform.system()} {platform.machine()}')
    print(BrowserDetector.get_browser_info())
    print('=== 测试完成 ===')

if __name__ == '__main__':
    test_browser_detection()
