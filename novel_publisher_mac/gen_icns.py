#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_icns.py —— 由 PNG 生成 macOS .icns，纯 Python，跨平台。

    python3 gen_icns.py <输入.png> [输出.icns]

为什么需要它：
    macOS 的 sips / iconutil 只能在 mac 上跑，但 .icns 本身是极简单的容器：
        'icns' + uint32(总长度) + 若干 [4字节类型 + uint32(块长度) + 数据]
    现代 macOS 的 ic07~ic14 类型允许直接内嵌 PNG，所以用 Pillow 缩放后拼装即可。

    打包流程里先用本脚本兜底生成图标，再用 sips/iconutil 重做一份更好的；
    这样即使原生工具不可用，.app 也一定有图标。
"""
import io
import os
import struct
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit('需要 Pillow： python3 -m pip install pillow')

# (icns 类型码, 目标边长)
VARIANTS = [
    ('ic11', 32),    # 16x16@2x
    ('ic12', 64),    # 32x32@2x
    ('ic07', 128),   # 128x128
    ('ic13', 256),   # 128x128@2x
    ('ic08', 256),   # 256x256
    ('ic14', 512),   # 256x256@2x
    ('ic09', 512),   # 512x512
    ('ic10', 1024),  # 512x512@2x
]


def _png(img, size):
    im = img.copy()
    im.thumbnail((size, size), Image.LANCZOS)
    canvas = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    canvas.paste(im, ((size - im.width) // 2, (size - im.height) // 2))
    buf = io.BytesIO()
    canvas.save(buf, format='PNG', optimize=True)
    return buf.getvalue()


def build(src_png, out_icns):
    img = Image.open(src_png).convert('RGBA')
    blocks = []
    for code, size in VARIANTS:
        data = _png(img, size)
        blocks.append(code.encode('ascii') + struct.pack('>I', len(data) + 8) + data)
    body = b''.join(blocks)
    with open(out_icns, 'wb') as f:
        f.write(b'icns' + struct.pack('>I', 8 + len(body)) + body)
    return os.path.getsize(out_icns), len(blocks)


def verify(path):
    with open(path, 'rb') as f:
        raw = f.read()
    if raw[:4] != b'icns':
        return False, '缺少 icns 魔数'
    if struct.unpack('>I', raw[4:8])[0] != len(raw):
        return False, '总长度字段与实际不符'
    pos, n = 8, 0
    while pos < len(raw):
        t = raw[pos:pos + 4]
        ln = struct.unpack('>I', raw[pos + 4:pos + 8])[0]
        if ln < 8 or pos + ln > len(raw):
            return False, f'{t!r} 块长度越界'
        if raw[pos + 8:pos + 16] != b'\x89PNG\r\n\x1a\n':
            return False, f'{t!r} 块不是 PNG'
        pos += ln
        n += 1
    return True, f'{n} 个 PNG 块'


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(src)[0] + '.icns'
    if not os.path.isfile(src):
        sys.exit(f'输入文件不存在: {src}')
    size, n = build(src, dst)
    ok, msg = verify(dst)
    print(f'已生成 {dst}  ({size} 字节, {n} 个图像块)')
    print(f'结构校验: {"通过" if ok else "失败"} —— {msg}')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
