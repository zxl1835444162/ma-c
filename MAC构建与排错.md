# 构建 macOS 版 & 「打不开」排错

面向 Windows 上的你。全文分三部分：**先确诊为什么打不开** → **再重新构建** → **最后是保底方案**。

---

## 一、为什么 GitHub Actions 打出来的那个打不开

先说结论：**CI 那份 workflow 结构上是对的**（构建步骤、权限修复、`ditto` 打包都没问题），
它真正的问题是两个「静默」的坑 —— 一个是架构，一个是 Tcl/Tk 的 Homebrew 路径。
而且它**从不验证产物能不能启动**，所以坏包会一路绿灯发到你手上。

按发生概率排序：

### ① 架构选错了（最可能）

旧 workflow 要你手选 `arm64` 或 `x86_64`，默认 `arm64`。

| 你的 Mac | 下的包 | 结果 |
|---|---|---|
| Apple Silicon（M1/M2/M3/M4） | arm64 | ✅ 正常 |
| Apple Silicon | **x86_64** | 提示需要 Rosetta，多数人直接当成「打不开」 |
| Intel | **arm64** | ❌ 完全打不开，且提示很含糊 |
| Intel | x86_64 | ✅ 正常 |

**确诊**：在 Mac 终端执行

```bash
uname -m
lipo -archs ~/Downloads/寒山小说发布工具.app/Contents/MacOS/寒山小说发布工具
```

两个值不一致 → 就是这个原因。**改法：重新下载对应架构的包**，或用后面的双架构 workflow。

### ② 系统的 Gatekeeper 拦截（第二可能，也是最好解决的）

包是 **ad-hoc 签名**（`codesign --sign -`），不是 Apple 开发者证书，所以：

- 弹「Apple 无法验证"寒山小说发布工具"…」→ 正常现象；
- 弹「"寒山小说发布工具"已损坏，无法打开，你应该将它移到废纸篓」→ 也是同一个原因，
  **不是文件坏了**。

**确诊**：

```bash
xattr -l ~/Downloads/寒山小说发布工具.app | grep quarantine
```

有输出就是它。

**修复**（一条命令，所有 macOS 版本都有效）：

```bash
xattr -dr com.apple.quarantine ~/Downloads/寒山小说发布工具.app
```

之后双击即可。**注意 macOS 15 Sequoia 已经移除了「右键→打开」的绕过方式**，
必须走「系统设置 → 隐私与安全性 → 安全性 → 仍要打开」。

### ③ Tcl/Tk（tkinter）没正确打进包 —— 这是旧 workflow 的真实技术缺陷

旧 workflow 的 Python 来源是这样的：

```yaml
- uses: actions/setup-python@v5
  with: { python-version: '3.10' }
# 若 setup-python 的构建不带 tkinter，就回退到：
#   brew install python@3.10 python-tk@3.10
```

问题出在那个 Homebrew 回退分支。Homebrew 的 Tcl/Tk 是**绝对路径依赖**
（`/opt/homebrew/opt/tcl-tk/lib/libtcl8.6.dylib`），PyInstaller 未必能把它正确搬进
`.app` 并改写成相对路径。结果是：**包在构建机上（有 Homebrew）是好的，
拿到没装 Homebrew 的 Mac 上启动即闪退** —— 表现就是双击一下、图标闪一下就没了。

而且因为 spec 里写了 `console=False`，加上 macOS 上单实例/`LSUIElement` 的行为，
这种闪退**通常一句话都不留**，非常像「打不开」。

**确诊**：

```bash
# 直接跑包里的主程序，让报错打到终端
~/Downloads/寒山小说发布工具.app/Contents/MacOS/寒山小说发布工具
```

看到 `ModuleNotFoundError: No module named '_tkinter'`，
或 `Library not loaded: /opt/homebrew/...` → 就是这个。

**根治**：用 **python.org 的官方 universal2 安装包**做打包基座，别用 Homebrew。
官方包的 Tcl/Tk 是官方 installer 专用布局，是 PyInstaller 文档推荐的 macOS 打包方式。
新 workflow 已经改成这样。

### ④ 你的 Mac 系统版本低于 App 声明的最低版本

`novel_publisher_mac.spec` 里写死了：

```python
'LSMinimumSystemVersion': '11.0',
```

也就是说 **macOS 10.15 Catalina 及更早的机器，系统会直接拒绝启动**，
而且提示往往不显眼。

**确诊**：`sw_vers -productVersion`，小于 11.0 就是这个原因。
**改法**：把 spec 里那行改成你机器实际支持的版本（比如 `'10.15'`）再重新打包；
但要注意 Python 3.10 官方包本身也只支持到 macOS 10.9+，理论可行。

### ⑤ 解压层级搞错了（容易误判）

GitHub 的 artifact 下载下来本身就是一层 zip，而旧 workflow 在 zip **里面**
又放了一个**同名**的 zip：

```
寒山小说发布工具-macOS-arm64.zip      ← 从 Artifacts 下载的这个
└── 寒山小说发布工具-macOS-arm64.zip  ← 解压一次后看到的是这个，同名！
    └── 寒山小说发布工具.app          ← 要再解压一次才是 app
```

很多人解压一次看到还是个 zip，就以为「下下来的不是 app」。
**确诊**：看解压出来的东西后缀是不是 `.zip`。**要再解压一次。**

---

## 二、重新构建（三条路，按推荐度）

### 路线 1：GitHub Actions 双架构构建（推荐，你全程留在 Windows）

我已经写好了新 workflow：**`.github/workflows/build-macos-all.yml`**。

它相对旧版的改动：

| 改动 | 解决的问题 |
|---|---|
| 一次产出 **arm64 + x86_64** 两个包（matrix） | 彻底消除「架构选错」 |
| **同时构建 Python 3.10 与 3.13 两套**（matrix） | Python 3.10 自带的 Tcl/Tk 是 8.6.12（2021 年），在 macOS 15 上会崩；3.13 自带新一代 Tk。两套并存，自检结果直接告诉你要哪套 |
| Python 用 **python.org universal2 官方包**，不用 Homebrew | 消除 Tcl/Tk 路径依赖，同时让它能在 arm64 机器上交叉产出 x86_64 |
| 加 **启动自检**（浅色 + 深色各跑一次） | 坏包再也发不出来，**且不在自检失败时让整个运行变红** —— 结论直接写进 artifact 名字（「可用-…」/「启动失败-…」） |
| 加 **私有路径扫描**：`otool` 检查包内是否残留 `/opt/homebrew`、`/Users/runner` | 提前拦住「构建机能跑、你的机器不能跑」 |
| 产物是**单层 zip**，且 artifact 名字与内层 zip 不再重名 | 消除解压层级误判 |

### 为什么是 Python 3.10 在拖后腿

原流程固定用 **Python 3.10.11** 构建。而 **Python 3.10 自 2023 年起，python.org 就只发源码、不再发布安装包了** —— 它自带的 Tcl/Tk 被永久冻结在 **8.6.12**。

实测崩溃栈：

```
TkpGetColor → Tk_GetColor → Tk_Get3DBorder → Tk_InitOptions
→ CreateFrame → TkInitialize → Tkapp_New
libc++abi: terminating due to uncaught exception of type NSException
```

正是 Tk 在 macOS 15.6 上创建根窗口时的取色代码。**这个 Tk 版本无法修补，只能换 Python 版本。**

源码已通过 Python 3.13 的静态兼容性检查：23 个 `.py` 文件**语法零错误**，且**没有**用到任何在 3.12/3.13 中被移除的模块或 API（`distutils`、`imp`、`inspect.getargspec`、`asyncio.coroutine`、`collections.Mapping`、`cgi` 等均为 0 处）。

> 所以 **py3.13 是首选**；py3.10 保留为对照组，用来确认问题确实出在 Tk 版本上。

**操作步骤**（假设你还没把它推上 GitHub）：

```bash
cd "C:/Users/Administrator/Downloads/novel-publisher-mac-main/novel-publisher-mac-main"

git init
git add -A
git commit -m "novel publisher mac"

# 先在 GitHub 网页上建一个空仓库（不要勾选 README），然后把地址填进来
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git branch -M main
git push -u origin main
```

> 只有公开仓库的 macOS runner 才免费无限量。私有仓库也能跑，但会扣额度。

然后在网页上：**Actions 标签页 → 左侧「构建 macOS 应用（双架构 + 启动自检）」
→ 右侧 Run workflow**。等 15–25 分钟，在该次运行的 **Artifacts** 区会看到两个：

```
寒山小说发布工具-macOS-arm64-安装包
寒山小说发布工具-macOS-x86_64-安装包
```

下载对应你 Mac 的那个。解压一次 → 得到文件夹 → 里面有 `.app`、说明、诊断脚本。

> **旧的 `build-macos.yml` 建议删掉**，否则两个 workflow 都会在 push 时触发、
> 重复跑两遍。留着也不影响正确性，只是浪费 CI 时间。

### 路线 2：直接在 Mac 上构建（最可靠，需要你摸一下 Mac）

PyInstaller 不支持交叉编译，所以在 Mac 上构建是**天然最稳**的路。

```bash
# 1) 装带 tkinter 的 Python 3.10 —— 强烈建议用官网安装包，别用 Homebrew
#    https://www.python.org/downloads/release/python-31011/
#    选 "macOS 64-bit universal2 installer"

# 2) 把整个 novel_publisher_mac 目录拷到 Mac，然后：
cd novel_publisher_mac
chmod +x *.sh *.command assets/*.sh
./build_mac.sh
```

`build_mac.sh` 本身写得不错：8 步流水线，会**先检查 tkinter**（`import tkinter` 不过就直接报错退出，
不会给你坏包），最后还会自检 `Info.plist` 和包体积。

指定架构：

```bash
TARGET_ARCH=arm64  ./build_mac.sh     # Apple Silicon
TARGET_ARCH=x86_64 ./build_mac.sh     # Intel
```

产物在 `dist/寒山小说发布工具.app`。**这个包天生不带 `com.apple.quarantine`**，
因为它是本地生成的，所以在本机能直接打开 —— 比 CI 包少一层麻烦。

顺带出 DMG：`MAKE_DMG=1 ./build_mac.sh`

### 路线 3：不打包，直接跑（保底方案）

如果打包怎么都不顺，这条路绕开了 PyInstaller 的全部问题：

```bash
cd novel_publisher_mac
chmod +x 启动.command
./启动.command          # 或右键 → 打开
```

首次会自动建 `.venv-run` 装依赖（1–3 分钟），然后直接跑源码。
**前提同上：Mac 上要有一个带 tkinter 的 Python 3.10。**

代价是需要目标机器有 Python，好处是没有任何打包/签名/架构问题。

---

## 三、拿到包之后的标准流程

1. **先解压到看到 `.app`**（可能要解压两次，见 ⑤）。
2. 把 `.app` 拖到「应用程序」或留在原处。
3. **双击同目录下的「打不开就先双击我-诊断.command」**（首次需右键 → 打开）。
   它会把 macOS 版本、CPU 架构、App 架构、签名、隔离属性、真实崩溃堆栈**全部打印出来**，
   并且自己判断结论。
4. 按它给出的结论处理。绝大多数情况就是一条命令：

```bash
xattr -dr com.apple.quarantine "/Applications/寒山小说发布工具.app"
```

5. 还不行就把诊断输出贴出来 —— 那里面一定有真实原因，不用再猜。

---

## 附：本次新增/改动的文件

| 文件 | 说明 |
|---|---|
| `.github/workflows/build-macos-all.yml` | **新增**。双架构 + 启动自检 + 私有路径扫描的构建流水线 |
| `诊断.command` | **新增**。放到 Mac 上双击，一键定位打不开的原因 |
| `MAC构建与排错.md` | 本文件 |
| `.gitattributes` | **新增**。强制 `*.command` / `*.sh` 用 LF 换行，防止 Windows 上被 git 转成 CRLF 后 macOS 报 `bad interpreter: /bin/bash^M` |

> 最后一条容易被忽略但很致命：`.command` 和 `.sh` 一旦变成 CRLF，在 macOS 上
> 双击**完全没反应**、终端报 `bad interpreter`。仓库里原有的 `启动.command`、
> `build_mac.sh` 都依赖 LF，所以加了 `.gitattributes` 兜住。
