# 寒山小说自动发布工具 · macOS 版

把 Windows 版 `app(1).exe`（PyInstaller + Python 3.10 + Playwright + tkinter）逆向还原，
并重建为可在 macOS（Apple Silicon / Intel）运行的等价应用。

- 原始样本：`app(1).exe`，64,171,543 字节，SHA256 `835CDB3732E56A9A852E40B5C29F888530E949D222B7B9EE61B93D56AB3BA4EE`
- 原程序版本号：`v2.2.8`（`app.py` 中 `VERSION = 'v2.2.8'`）
- 还原方式：PyInstaller 解包 → PYZ 解出 133 个 code object → 反编译 + 按字节码逐处校对

---

## 1. 快速开始（macOS）

```bash
# 1) 依赖（Python 3.10；建议用 python.org 安装包，自带 Tcl/Tk 8.6）
python3.10 -m pip install -r requirements-mac.txt

# 2) 安装 Playwright 内置 Chromium（可选，但推荐）
python3.10 -m playwright install chromium

# 3) 开发模式直接运行
./run_dev_mac.sh
# 等价于： python3.10 app.py

# 4) 打包成 .app
./build_mac.sh
# 产物： dist/寒山小说发布工具.app
```

首次启动后：

1. 「浏览器地址/端口」一栏点 **自动检测**，程序会在 `/Applications` 里找
   Chrome / Edge / Chromium / Brave / Vivaldi；找不到就手填内置 Chromium 路径
   （`~/Library/Caches/ms-playwright/chromium-*/chrome-mac/Chromium.app/Contents/MacOS/Chromium`）。
2. 点 **创建分身** → 在 `~/Library/Application Support/寒山小说发布工具/Shortcuts/`
   生成 `<笔名>.command` 启动器（macOS 版等价于 Windows 的 `.lnk`），同时分配一个
   调试端口（默认从 42900 起）。
3. 点 **登录(完成)** 完成各平台账号登录，登录态保存到数据目录的 `auth.json`。
4. 填小说标题/文件夹，保存配置，即可 **开始发布**。

---

## 2. 目录结构

```
novel_publisher_mac/
├── app.py                      主程序（tkinter GUI + 各平台发布流程）
├── browser_detector.py         浏览器检测（macOS 走 /Applications，Windows 走注册表）
├── macos_support.py            macOS 平台能力层（路径/打开文件/分身启动器/托盘/进程）
├── platform_patch.py           把 Windows 专有实现替换为跨平台实现的猴子补丁
├── novel_publisher/            业务包
│   ├── browser.py              Playwright 浏览器启动与 CDP 接管
│   ├── chapter_files.py        章节文件读写、字数统计、重复内容检查
│   ├── config.py               PublishConfig（15 元素元组兼容切片）
│   ├── create_book.py          从大纲创建新书
│   ├── downloader.py           番茄/飞卢/起点小说下载
│   ├── logging_redirect.py     stdout 重定向到 GUI 日志区
│   ├── navigation.py           页面导航与浮层处理
│   ├── platforms.py            平台基类 + 注册表
│   ├── platforms/adapters.py   11 个平台到 automation_flow_by_* 的桥接
│   ├── sstory.py               番茄短故事自动发布
│   ├── tasks.py                定时任务注册表
│   ├── tasks/adapters.py       scheduled_* 方法桥接
│   └── tray.py                 系统托盘
├── font_map.py / icon.py       字体映射表、内嵌 PNG 图标（base64）
├── novel_publisher_mac.spec    PyInstaller 打包描述
├── build_mac.sh                一键打包脚本
├── run_dev_mac.sh              开发模式启动
└── requirements-mac.txt        依赖清单
```

运行期数据目录（与程序目录分离，符合 macOS 规范）：

```
~/Library/Application Support/寒山小说发布工具/
├── config.ini        界面与小说配置（原版放在 exe 同目录）
├── auth.json         各平台登录态（Playwright storage_state）
├── 签约信息.txt      自动签约用的作者信息
└── Shortcuts/
    ├── contrast.json 笔名 → 调试端口 映射
    ├── <笔名>.command 浏览器分身启动器
    └── <端口>/       分身专属 user-data-dir
```

---

## 3. 相对 Windows 版做了哪些平台适配

| 功能 | Windows 原实现 | macOS 版实现 |
|---|---|---|
| 浏览器检测 | 读注册表 `App Paths\chrome.exe` 等 + `C:\Program Files\...` | 探测 `/Applications/*.app/Contents/MacOS/*`、`~/Applications`，不依赖注册表 |
| 浏览器分身 | `win32com` 生成 `.lnk` 快捷方式 | 生成可执行 `.command` 脚本，参数完全一致：`--remote-debugging-port=<端口> --user-data-dir="<目录>" --new-window <站点>` |
| 打开文件/文件夹 | `os.startfile()` | `open` / `open -R`（Finder 定位） |
| 结束占用 profile 的浏览器 | `taskkill` | `ps -ax` + `SIGTERM` |
| 数据目录 | exe 同目录 / `sys._MEIPASS` | `~/Library/Application Support/寒山小说发布工具/`（首次运行会把旧的 `config.ini`、`auth.json` 自动迁移） |
| 日志字体 | 微软雅黑 | PingFang SC（`macos_support.preferred_ui_font`） |
| 托盘图标 | `threading.Thread(icon.run)` | `pystray` 的 `run_detached(darwin_nsapplication=NSApp)`，符合 macOS 主线程约束 |
| 下拉框/窗口尺寸 | `640x900` 固定 | 同原值，Retina 下由 `NSHighResolutionCapable` 保证清晰 |

业务逻辑（各平台发布流程、章节处理、下载器）不区分平台，未做改动。

---

## 3.5 还原进度

<!-- STATUS:BEGIN -->
### 还原进度（自动统计，app.py 共 4077 行 / 115 个函数）

| 功能域 | 已还原 | 待补全 |
|---|---|---|
| 浏览器与登录 | 5/5 | — |
| 发布主流程 | 10/10 | — |
| 单章发布 | 6/6 | — |
| 章节与下载 | 4/4 | — |
| 创书与定时 | 7/7 | — |
| 配置与界面 | 5/5 | — |

- 空实现（`pass`）方法：无
- 业务包 `novel_publisher/` 全部模块通过语法检查与导入检查，`selftest_business.py` 全绿
<!-- STATUS:END -->

## 4. 逆向与还原说明（可复核）

### 4.1 解包链路

```
app(1).exe
 ├─ PE x86-64, subsystem=GUI, .rsrc + CArchive
 ├─ PyInstaller 归档：1402 个条目（含 python310.dll / tcl86t.dll / playwright driver）
 └─ PYZ.pyz：610 个模块，其中自研代码 17 个（novel_publisher.* / browser_detector / font_map / icon）
```

用到的工具（都保留在 `../tools/` 下，可复现）：

| 工具 | 用途 |
|---|---|
| `pyinstxtractor.py` / `pyinstxtractor_ng.py` | 解 CArchive 与 PYZ |
| `extract_calls310.py` | 从字节码提取**每个调用点的真实参数个数与关键字名**（`nargs` 来自 `CALL_FUNCTION_KW` 的 oparg，关键字名来自紧邻的 `LOAD_CONST` 元组） |
| `disasmfn.py` / `dump_class.py` | 逐函数反汇编（xdis 驱动，UTF-8 安全输出） |
| `repair_flat.py` | 修复 pycdc 的关键字参数错位（206 处） |
| `clean_pycdc.py` | 清除 pycdc 的非源码拼接（`None(None,None,None)`、伪 `with None:`、`from  import`、`(lambda .0: ...)`） |
| `missing_methods.py` | 比对字节码与源码，列出未还原的函数 |

### 4.2 pycdc 在本样本上的三类系统性缺陷（已全部处理）

1. **关键字参数错位**：`f(a, k=v)` 会被输出成 `f(a, v, **('k',))`。
   依据 `CALL_FUNCTION_KW` 的 oparg（= 位置参数 + 关键字参数总数）与关键字名元组复原，共修正 206 处。
2. **`self` 丢失**：闭包里的 `self` 变成裸 `None`（如 `None.title(...)`、`None.config.get(...)`），
   按 `LOAD_DEREF __class__` 指令判定对象后逐一修正。
3. **异常处理块丢弃**：含 `try/except` 的函数体被压缩成 `pass`（如 `check_repeat_content`），
   已按异常表与指令流重建。

---

## 5. 已知限制与后续工作

1. **`app.py` 的类方法还原**：pycdc 在 `refresh_ui` 之后截断，原文件约 5680 行、133 个 code object，
   其中 94 个函数（主要是 `automation_flow_by_*`、`publish_single_chapter_on_*`、`login`、
   `export/import_chapters`、`_execute_create_book`）需要按字节码逐条重建。
   未还原的方法调用时会 `AttributeError`，对应 GUI 按钮不可用。重建清单见 `../out/missing_app_functions.txt`。
2. **浏览器二进制不能跨平台复用**：Windows 版内嵌的 Chromium 无法在 macOS 上运行，
   必须执行 `playwright install chromium`，或依赖本机已安装的 Chrome / Edge。
3. **首次运行提示**：从网络下载的 `.app` 会被 Gatekeeper 打上隔离属性，本机自测可执行
   `xattr -dr com.apple.quarantine 寒山小说发布工具.app`；对外分发需要 Developer ID + `notarytool`。
4. **架构选择**：Playwright 的 universal2 wheel 复用 x86_64 driver，因此推荐 **分别打 arm64 与 x86_64 两份包**
   （`TARGET_ARCH=arm64|x86_64 ./build_mac.sh`），不要用 universal2。
5. **签名注意**：macOS 13 起 `codesign --deep` 已被 Apple 标记为不推荐；对外分发时应逐项签名，
   `build_mac.sh` 里的 `--deep` 仅用于本机 ad-hoc 自测。

---

## 6. 合规声明（沿用原程序说明）

原程序随附声明：本工具仅用于学习和研究，不涉及任何商业用途。
本目录是对该程序的格式转换与平台适配，未改变其功能定位。
