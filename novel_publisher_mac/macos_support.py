"""macOS 平台适配层。

原程序（Windows 版）在若干处直接调用了 Windows 专有 API：

    create_shortcut()      用 win32com 创建 .lnk 快捷方式启动「浏览器分身」
    open_browser_lnk()     os.startfile 打开 .lnk
    relative_browser_lnk() os.startfile / 读取 Shortcuts/contrast.json
    open_file()/open_dir() os.startfile 打开文件与文件夹
    _get_app_base_dir()    sys._MEIPASS 下的目录布局
    tray.py                pystray.Icon.run() 在子线程里启动（macOS 上会失败）
    downloader.py          os.startfile(file_path) 打开下载结果

本模块给出这些能力的 macOS 等价实现，并在需要时回退到 Windows 行为，
使同一套业务代码在两个平台上都能运行。

设计要点：
  * 「浏览器分身」在 macOS 上用 .command 可执行脚本实现（等价于 Windows 的 .lnk），
    脚本内容与 Windows 版快捷方式的参数完全一致：
        <浏览器> --remote-debugging-port=<端口> --user-data-dir="<数据目录>" --new-window <站点>
  * 数据目录统一放在 ~/Library/Application Support/<APP_NAME>/，
    包括 config.ini / auth.json / Shortcuts/ / <端口> 用户数据目录。
"""
from __future__ import annotations

import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys

IS_MAC = sys.platform == 'darwin'
IS_WIN = sys.platform.startswith('win')

APP_NAME = '寒山小说发布工具'
APP_BUNDLE_ID = 'com.hanshan.novelpublisher'

# --------------------------------------------------------------------- paths

def is_frozen() -> bool:
    """是否运行在 PyInstaller 打包环境里。"""
    return getattr(sys, 'frozen', False)

def resource_dir() -> str:
    """只读资源目录（图标等打进包里的文件）。"""
    if is_frozen():
        return getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))

def app_base_dir() -> str:
    """可写的应用数据目录。

    macOS:  ~/Library/Application Support/寒山小说发布工具
    Windows: %APPDATA%/寒山小说发布工具
    Linux:   ~/.local/share/寒山小说发布工具
    """
    if IS_MAC:
        root = os.path.expanduser('~/Library/Application Support')
    elif IS_WIN:
        root = os.environ.get('APPDATA') or os.path.expanduser('~')
    else:
        root = os.environ.get('XDG_DATA_HOME') or os.path.expanduser('~/.local/share')
    path = os.path.join(root, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path

def ensure_app_dirs() -> str:
    """确保数据目录与子目录存在，返回数据根目录。"""
    base = app_base_dir()
    os.makedirs(os.path.join(base, 'Shortcuts'), exist_ok=True)
    return base

def migrate_legacy_files(names=('config.ini', 'auth.json', '签约信息.txt')) -> list:
    """把程序目录（旧版/Windows 习惯）里的配置迁移到数据目录，避免用户重配。"""
    base = app_base_dir()
    moved = []
    for name in names:
        src = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), name)
        dst = os.path.join(base, name)
        if os.path.exists(src) and not os.path.exists(dst):
            try:
                shutil.copy2(src, dst)
                moved.append(name)
            except OSError:
                pass
    return moved

# --------------------------------------------------------------- open / reveal

def open_path(path: str) -> None:
    """用系统默认程序打开文件或目录（等价 Windows 的 os.startfile）。"""
    if IS_WIN:
        os.startfile(path)  # type: ignore[attr-defined]
    elif IS_MAC:
        subprocess.Popen(['open', path])
    else:
        subprocess.Popen(['xdg-open', path])

def reveal_in_file_manager(path: str) -> None:
    """在文件管理器里定位文件。"""
    if IS_MAC:
        subprocess.Popen(['open', '-R', path])
    elif IS_WIN:
        subprocess.Popen(['explorer', '/select,', os.path.normpath(path)])
    else:
        subprocess.Popen(['xdg-open', os.path.dirname(path)])

def open_terminal_with(command: str) -> None:
    """打开终端执行命令（macOS：Terminal.app）。"""
    if IS_MAC:
        script = f'tell application "Terminal" to do script "{command}"'
        subprocess.Popen(['osascript', '-e', script])
    elif IS_WIN:
        subprocess.Popen(f'start cmd /k {command}', shell=True)
    else:
        subprocess.Popen(['x-terminal-emulator', '-e', command])

# ------------------------------------------------------------- browser profiles

def browser_profile_dir(port) -> str:
    """浏览器分身使用的 user-data-dir。"""
    return os.path.join(app_base_dir(), str(port))

def shortcut_dir() -> str:
    d = os.path.join(app_base_dir(), 'Shortcuts')
    os.makedirs(d, exist_ok=True)
    return d

def browser_launch_args(port, profile_dir: str, site_url: str) -> str:
    """与 Windows 版快捷方式完全一致的启动参数。"""
    return (f'--remote-debugging-port={port} '
            f'--user-data-dir="{profile_dir}" '
            f'--new-window {site_url}')

def create_browser_shortcut(name: str, browser_path: str, args: str) -> str:
    """创建「浏览器分身」启动器，返回其路径。

    macOS 生成可执行 .command 脚本；Windows 生成 .lnk（沿用 win32com）。
    """
    if IS_MAC:
        target = os.path.join(shortcut_dir(), f'{name}.command')
        body = ('#!/bin/bash\n'
                'cd "$(dirname "$0")"\n'
                f'exec "{browser_path}" {args}\n')
        with open(target, 'w', encoding='utf-8') as f:
            f.write(body)
        os.chmod(target, os.stat(target).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        return target

    target = os.path.join(shortcut_dir(), f'{name}.lnk')
    from win32com import client as win32client  # noqa: WPS433  (Windows only)
    shell = win32client.Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(target)
    shortcut.TargetPath = browser_path
    if args:
        shortcut.Arguments = args
    shortcut.IconLocation = f'{browser_path},0'
    shortcut.Save()
    return target

def open_browser_shortcut(name: str) -> bool:
    """启动已创建的分身。"""
    if IS_MAC:
        target = os.path.join(shortcut_dir(), f'{name}.command')
        if not os.path.exists(target):
            return False
        os.chmod(target, os.stat(target).st_mode | stat.S_IXUSR)
        subprocess.Popen(['/bin/bash', target], start_new_session=True)
        return True
    target = os.path.join(shortcut_dir(), f'{name}.lnk')
    if not os.path.exists(target):
        return False
    open_path(target)
    return True

def shortcut_exists(name: str) -> bool:
    ext = '.command' if IS_MAC else '.lnk'
    return os.path.exists(os.path.join(shortcut_dir(), f'{name}{ext}'))

CONSTRAST_FILE = 'contrast.json'

def load_contrast_map() -> dict:
    """读取「笔名 -> 调试端口」映射（与 Windows 版同名文件）。"""
    path = os.path.join(shortcut_dir(), CONSTRAST_FILE)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}

def save_contrast_map(mapping: dict) -> None:
    path = os.path.join(shortcut_dir(), CONSTRAST_FILE)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=4)

def allocate_port_and_profile(mapping: dict, writer_name: str, start: int = 42900,
                              span: int = 1000):
    """为笔名分配一个未被占用的调试端口与数据目录。"""
    if writer_name in mapping:
        port = mapping[writer_name]
        return port, browser_profile_dir(port)
    for i in range(span):
        port = start + i
        profile = browser_profile_dir(port)
        if not os.path.exists(profile):
            mapping[writer_name] = port
            save_contrast_map(mapping)
            os.makedirs(profile, exist_ok=True)
            return port, profile
        if not os.listdir(profile):
            mapping[writer_name] = port
            save_contrast_map(mapping)
            return port, profile
    os.makedirs(browser_profile_dir(start), exist_ok=True)
    return start, browser_profile_dir(start)

# ------------------------------------------------------------------ process mgmt

def kill_processes_using_profile(profile_dir: str) -> int:
    """结束正在使用该 user-data-dir 的浏览器进程（登录前清理占用）。"""
    pattern = os.path.abspath(profile_dir)
    killed = 0
    if IS_MAC or not IS_WIN:
        try:
            out = subprocess.run(['ps', '-ax', '-o', 'pid=,command='],
                                 capture_output=True, text=True).stdout
        except OSError:
            return 0
        for line in out.splitlines():
            if pattern in line:
                pid = line.strip().split(' ', 1)[0]
                if pid.isdigit() and int(pid) != os.getpid():
                    try:
                        os.kill(int(pid), 15)
                        killed += 1
                    except OSError:
                        pass
        return killed
    # Windows：用 wmic/powershell 查找命令行里包含该目录的进程
    try:
        out = subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*%s*' } | "
             "ForEach-Object { $_.ProcessId }" % pattern],
            capture_output=True, text=True).stdout
        for line in out.split():
            if line.isdigit() and int(line) != os.getpid():
                subprocess.run(['taskkill', '/PID', line, '/F'], capture_output=True)
                killed += 1
    except OSError:
        pass
    return killed

def site_url_for(writer_name: str = '', site: str = 'https://xingyuexiezuo.com') -> str:
    """默认站点地址（与原版一致）。"""
    return site

# -------------------------------------------------------------------- tk / tray

def apply_darwin_tk_defaults(root) -> None:
    """macOS 上 tkinter 的几处平台差异修正。

    * 原程序用「微软雅黑」，macOS 无此字体，回退到系统默认中文字体；
    * Tk 8.6 之前的旧版会让窗口贴顶，这里统一抬高一点；
    * macOS 需要显式设置前台进程属性，否则窗口可能被终端挡住。
    """
    if not IS_MAC:
        return
    try:
        root.tk.call('tk', 'scaling', 1.4)
    except Exception:
        pass
    for seq, func in ():
        pass
    try:
        from AppKit import NSApplication, NSApplicationActivationPolicyRegular
        NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyRegular)
    except Exception:
        pass

def preferred_ui_font(size: int = 9) -> tuple:
    """日志区等控件用的字体。"""
    if IS_MAC:
        return ('PingFang SC', size)
    if IS_WIN:
        return ('微软雅黑', size)
    return ('Noto Sans CJK SC', size)

def tray_run(icon, on_ready=None) -> None:
    """跨平台启动托盘图标。

    macOS：pystray 必须使用 run_detached + NSApplication 集成，且不能放进子线程；
    Windows：原版用 `threading.Thread(icon.run)`，这里保持兼容。
    """
    if IS_MAC:
        try:
            from AppKit import NSApplication
            icon.run_detached(darwin_nsapplication=NSApplication.sharedApplication())
            return
        except Exception:
            pass
    icon.run()

def nsapp():
    try:
        from AppKit import NSApplication
        return NSApplication.sharedApplication()
    except Exception:
        return None

def platform_label() -> str:
    return f'{platform.system()} {platform.machine()}'
