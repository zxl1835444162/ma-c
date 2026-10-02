# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置（macOS 主目标 / Windows 亦可构建）。

构建（必须在目标平台上执行，PyInstaller 不支持交叉编译）：
    # macOS Apple Silicon
    ./build_mac.sh
    # macOS Intel
    TARGET_ARCH=x86_64 ./build_mac.sh
    # 通用二进制（需要 universal2 版 Python）
    TARGET_ARCH=universal2 ./build_mac.sh

产物：
    macOS   -> dist/寒山小说发布工具.app
    Windows -> dist/寒山小说发布工具/寒山小说发布工具.exe

设计要点
  1. onedir（COLLECT）+ BUNDLE，不用 onefile：Playwright 的 node driver 近 100MB，
     onefile 每次启动都要解压到临时目录，macOS 上还会被 Gatekeeper 反复扫描。
  2. upx 全关：UPX 会破坏 macOS 代码签名。
  3. darwin 上把 win32* 全部 exclude —— 源码里 `import win32com.client` 藏在
     create_shortcut() 内部（已被 platform_patch 替换），但 PyInstaller 的静态
     分析仍会去找它，不排除就会报 hidden import 缺失。
  4. playwright 的 driver(含 node) 由 collect_data_files 收集；但 data 文件会丢
     可执行位，所以额外挂一个 runtime hook 在启动时 chmod +x（见 rthook_frozen_macos.py）。
"""
import os
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

APP_NAME = '寒山小说发布工具'
VERSION = '2.2.8'
BUNDLE_ID = 'com.hanshan.novelpublisher'

# PyInstaller 在执行 spec 时注入 SPECPATH = 「包含 spec 文件的目录」，即本工程根。
# 注意不要再 dirname 一次，否则会退到上一级，导致 assets/app.icns 找不到、.app 丢图标。
ROOT = os.path.abspath(SPECPATH) if 'SPECPATH' in globals() else os.path.abspath('.')
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)
print(f'[spec] 工程根: {ROOT}')

IS_DARWIN = sys.platform == 'darwin'

# --------------------------------------------------------------------- 资源收集

datas = []
binaries = []

# 注意：源码运行期并不读取 assets/ 目录（图标由 icon.py 以 base64 内嵌），
# 所以这里不打包 assets。/ 唯一的构建期用途是 assets/app.icns，由下面的
# BUNDLE(icon=...) 嵌入到 Contents/Resources/app.icns。
_ASSETS = os.path.join(ROOT, 'assets')
if not os.path.isdir(_ASSETS):
    print(f'[spec] 警告：缺少资源目录 {_ASSETS}')

# playwright 的 driver（node 可执行文件 + package 目录）
try:
    datas += collect_data_files('playwright')
except Exception as exc:                     # pragma: no cover
    print(f'[spec] 收集 playwright 数据失败: {exc}')

hiddenimports = [
    'playwright.sync_api',
    'playwright._impl._driver',
    'playwright._impl._transport',
    'novel_publisher.browser',
    'novel_publisher.chapter_files',
    'novel_publisher.config',
    'novel_publisher.create_book',
    'novel_publisher.downloader',
    'novel_publisher.logging_redirect',
    'novel_publisher.navigation',
    'novel_publisher.platforms',
    'novel_publisher.platforms.adapters',
    'novel_publisher.sstory',
    'novel_publisher.tasks',
    'novel_publisher.tasks.adapters',
    'novel_publisher.tray',
    'browser_detector',
    'font_map',
    'icon',
    'platform_patch',
    'macos_support',
]
hiddenimports += collect_submodules('novel_publisher')

# --------------------------------------------------------------------- 排除项

excludes = [
    # 体积杀手
    'matplotlib', 'numpy', 'pandas', 'scipy', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6',
    'IPython', 'jupyter', 'notebook', 'pytest', 'sphinx', 'tkinter.test', 'test',
]

if IS_DARWIN:
    # Windows 专有：源码里以函数内 import 形式出现，macOS 上不需要且会拖垮分析
    excludes += [
        'win32com', 'win32com.client', 'win32com.shell',
        'win32api', 'win32con', 'win32gui', 'win32process', 'win32event',
        'pythoncom', 'pywintypes', '_winreg', 'winreg', 'msvcrt',
    ]
else:
    # 非 macOS 上排除 pyobjc（仅 macOS 提供）
    excludes += ['objc', 'AppKit', 'Foundation', 'Quartz', 'PyObjCTools']

# --------------------------------------------------------------------- 构建

a = Analysis(
    ['app.py'],
    pathex=[os.path.abspath('.')],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=['rthook_frozen_macos.py'] if IS_DARWIN else [],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,                        # 需要无控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=os.environ.get('TARGET_ARCH') or None,
    codesign_identity=None,               # 缺省时 PyInstaller 做 ad-hoc 签名
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)

if IS_DARWIN:
    ICNS = os.path.join(ROOT, 'assets', 'app.icns')
    _icon = ICNS if os.path.exists(ICNS) else None
    if _icon is None:
        print('[spec] 警告：未找到 assets/app.icns，本次打包不带图标。')
        print('       先执行： bash assets/make_icns.sh')
    else:
        print(f'[spec] 使用图标: {_icon}')
    app = BUNDLE(
        coll,
        name=f'{APP_NAME}.app',
        icon=_icon,
        bundle_identifier=BUNDLE_ID,
        version=VERSION,
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '11.0',
            'CFBundleName': APP_NAME,
            'CFBundleDisplayName': APP_NAME,
            'CFBundleShortVersionString': VERSION,
            'CFBundleVersion': VERSION,
            'NSAppleEventsUsageDescription': '用于打开浏览器与文件夹',
            'NSDesktopFolderUsageDescription': '用于读取与保存小说章节文件',
            'NSDocumentsFolderUsageDescription': '用于读取与保存小说章节文件',
            'NSDownloadsFolderUsageDescription': '用于导出的章节与下载的小说',
            'LSUIElement': False,
            'NSRequiresAquaSystemAppearance': False,
        },
    )
