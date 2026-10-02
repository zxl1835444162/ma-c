"""打一个「传过去权限也不会丢」的 zip，给没有 Mac 开发经验的人用。

背景
----
Windows 文件系统没有 Unix 可执行位。直接用微信 / U 盘 / 网盘传 `.command`
文件，到 Mac 上 +x 就没了，双击会报：

    无法执行，因为你没有正确的访问权限

但 zip 的每个条目里带 external_attr，可以把 0755 写进去；macOS 的
「归档实用工具」解压时会按这个位还原权限。
所以规则是：**脚本永远走 zip 传，不要传裸文件。**

用法
----
    python make_mac_pack.py

产出仓库根目录下的 `Mac修复工具包.zip`。
"""
import pathlib
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "Mac修复工具包.zip"

# (源文件, zip 内文件名, 是否给可执行位)
ITEMS = [
    (ROOT / "一键修复.command", "① 先双击我-修复并打开.command", True),
    (ROOT / "诊断.command", "② 还不行就双击我-诊断.command", True),
    (ROOT / "MAC小白操作手册.md", "③ 小白操作手册.md", False),
]

README = """寒山小说发布工具 · Mac 修复工具包
=========================================

怎么用
------
1. 【必须整个 zip 传】用微信/QQ/网盘/U盘把这个 zip 传到 Mac 上。
   不要单独传里面的 .command 文件 —— 那样会丢权限，双击会报
   「无法执行，因为你没有正确的访问权限」。

2. 在 Mac 上【双击这个 zip】解压（不要用第三方解压软件，就用系统双击）。

3. 解压出来后，【双击 ① 先双击我-修复并打开.command】。
   第一次双击 macOS 会拦一次，在它上面【右键 → 打开 → 再点「打开」】。
   之后就能直接双击了。

4. 如果 ① 还是不行，双击 ② 还不行就双击我-诊断.command，
   把终端里打印的一整屏文字截图发出去。

如果双击时提示「无法执行，因为你没有正确的访问权限」
----------------------------------------------------
说明权限没还原成功。补救办法（要用一次终端，只用一次）：

  a) 按 Command + 空格，输入「终端」，回车，打开终端窗口。
  b) 在终端里输入以下内容（注意 chmod +x 后面有一个空格）：
         chmod +x 
  c) 把 ① 那个 .command 文件【拖进终端窗口】，路径会自动补全。
  d) 按回车。搞定，以后直接双击即可。

  或者更省事（不需要执行权限，但每次都要这么来）：
     bash  然后拖文件进来  然后回车

关于「打不开应用」本身
----------------------
这个包里【不含】应用本体。应用是「寒山小说发布工具.app」，
需要另外放进来或单独下载。① 会自己去「下载」「桌面」「应用程序」
这几个地方找它。找不到的话，把 .app 拖到 ① 的图标上松手即可。
"""


def main():
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        zi = zipfile.ZipInfo("先看我.txt", date_time=(2026, 10, 2, 9, 45, 0))
        zi.create_system = 3          # 3 = Unix，解压端才会认权限位
        zi.external_attr = 0o100644 << 16
        z.writestr(zi, README.encode("utf-8"))

        for src, name, executable in ITEMS:
            if not src.exists():
                print(f"跳过（不存在）: {src}")
                continue
            data = src.read_bytes().replace(b"\r\n", b"\n")
            zi = zipfile.ZipInfo(name, date_time=(2026, 10, 2, 9, 45, 0))
            zi.create_system = 3
            zi.external_attr = (0o100755 if executable else 0o100644) << 16
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, data)
            print(f"已加入: {name}  (mode {'755' if executable else '644'})")

    print(f"\n产出: {OUT}  ({OUT.stat().st_size / 1024:.1f} KB)")
    print("提醒：这个 zip 已被 .gitignore 排除，属于本地传输件，不进仓库。")


if __name__ == "__main__":
    main()
