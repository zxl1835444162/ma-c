"""平台补丁：把 Windows 专有实现替换为跨平台版本。

原程序里有若干函数直接依赖 Windows API（win32com、os.startfile、注册表）。
本模块在启动时对 NovelPublisherApp 打猴子补丁，用 macos_support 中的等价实现
替换它们。这样业务逻辑（automation_flow_by_* / publish_single_chapter_* 等）
无需任何改动即可在 macOS 上运行。

用法（在 app.py 的 `if __name__ == '__main__':` 之后、实例化窗口之前）：

    import platform_patch          # noqa: F401  (导入即生效)
"""
from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import messagebox

import macos_support as ms

def _writer_name(app) -> str:
    try:
        name = app.novel_writer_var.get().strip() or 'default'
    except Exception:
        name = 'default'
    return name

def create_shortcut(self):
    """创建「浏览器分身」（macOS 用 .command，Windows 用 .lnk）。"""
    browser_path = self.custom_browser_path_var.get().strip()
    if not browser_path:
        messagebox.showerror('错误', '请先填写浏览器地址（自动检测或手动选择）')
        return None
    if not ms.IS_MAC and not ms.IS_WIN:
        messagebox.showerror('错误', f'当前平台 {ms.platform_label()} 暂不支持创建分身')
        return None

    writer = _writer_name(self)
    mapping = ms.load_contrast_map()
    port, profile_dir = ms.allocate_port_and_profile(mapping, writer)
    site_url = self._get_site_url()
    args = ms.browser_launch_args(port, profile_dir, site_url)
    target = ms.create_browser_shortcut(writer, browser_path, args)

    self.custom_browser_path_var.set(str(port))
    print(f'已创建快捷方式: {writer}')
    print(f'  启动器: {target}')
    print(f'  调试端口: {port}')
    print(f'  数据目录: {profile_dir}')
    # 打开 Shortcuts 目录方便查看（macOS 上是 Finder）
    ms.open_path(ms.shortcut_dir())
    return None

def open_browser_lnk(self):
    """启动已创建的分身。"""
    writer = _writer_name(self)
    if not ms.shortcut_exists(writer):
        messagebox.showerror('错误', f'未找到 {writer} 的分身，请先点「创建分身」')
        return None
    ms.open_browser_shortcut(writer)
    print(f'已打开分身: {writer}')
    return None

def relative_browser_lnk(self):
    """把「浏览器地址」一栏切换为分身端口（用于接管已在运行的分身）。"""
    mapping = ms.load_contrast_map()
    if not mapping:
        messagebox.showerror('错误', '未找到分身配置文件')
        return False
    writer = _writer_name(self)
    port = mapping.get(writer)
    if port is None:
        messagebox.showerror('错误', '未找到该账号的分身')
        return False
    self.custom_browser_path_var.set(str(port))
    print(f'已切换到分身端口: {port}')
    return None

def open_file(self, event=None):
    novel_dir = os.path.abspath(self.novels_folder_var.get())
    chapter_no = self.start_chapter_var.get()
    path = os.path.join(novel_dir, f'Chapter_{chapter_no:03d}.md')
    if not os.path.exists(path):
        messagebox.showerror('错误', f'章节文件不存在:\n{path}')
        return None
    ms.open_path(path)
    return None

def open_dir(self, event=None):
    path = os.path.abspath(self.novels_folder_var.get())
    if not os.path.isdir(path):
        messagebox.showerror('错误', f'目录不存在:\n{path}')
        return None
    ms.open_path(path)
    return None

def _get_app_base_dir(self):
    """数据目录：macOS 落在 ~/Library/Application Support/<应用名>/。"""
    return ms.ensure_app_dirs()

def _get_login_profile_dir(self):
    """登录流程使用的浏览器 profile 目录。"""
    return os.path.join(self._get_app_base_dir(), 'login_profile')

def _terminate_browser_using_profile(self, profile_dir):
    return ms.kill_processes_using_profile(profile_dir)

def on_closing(self):
    """关闭窗口：macOS 上直接退出，Windows 行为不变。"""
    try:
        self.restore_stdout()
    except Exception:
        pass
    try:
        if getattr(self, 'tray_icon', None) is not None:
            self.tray_icon.stop()
    except Exception:
        pass
    self.destroy()

def run_tray(self):
    """macOS 必须在主线程用 run_detached 挂到 NSApplication。"""
    try:
        ms.tray_run(self.tray_icon)
    except Exception as exc:  # pragma: no cover - 平台相关
        print(f'托盘图标启动失败（不影响主功能）: {exc}')

def apply(app_cls) -> None:
    """对 NovelPublisherApp 打补丁。"""
    patched = {
        'create_shortcut': create_shortcut,
        'open_browser_lnk': open_browser_lnk,
        'relative_browser_lnk': relative_browser_lnk,
        'open_file': open_file,
        'open_dir': open_dir,
        '_get_app_base_dir': _get_app_base_dir,
        '_get_login_profile_dir': _get_login_profile_dir,
        '_terminate_browser_using_profile': _terminate_browser_using_profile,
        'on_closing': on_closing,
        'run_tray': run_tray,
    }
    for name, func in patched.items():
        if hasattr(app_cls, name):
            setattr(app_cls, name, func)
        else:
            # 方法在反编译中缺失时补一个可用的实现
            setattr(app_cls, name, func)
    print(f'已应用跨平台补丁（{ms.platform_label()}）：{", ".join(sorted(patched))}')
