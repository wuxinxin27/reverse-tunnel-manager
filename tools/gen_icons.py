#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 assets/icon.svg 生成 assets/icon.png、assets/icon-512.png 和 assets/icon.ico。
依赖：python3-gi + GdkPixbuf（GNOME 桌面自带，无第三方包）。

用法：python3 tools/gen_icons.py
"""

import struct
import sys
from pathlib import Path

import gi

gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "icon.svg"
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]


def render(size: int):
    return GdkPixbuf.Pixbuf.new_from_file_at_size(str(SRC), size, size)


def png_bytes(pb) -> bytes:
    res = pb.save_to_bufferv("png", [], [])
    if isinstance(res, tuple):  # 旧版 PyGObject 返回 (ok, bytes)
        ok, data = res
        if not ok:
            raise RuntimeError("PNG 编码失败")
        return bytes(data)
    return bytes(res)


def build_ico(entries, path: Path) -> None:
    """把多张 PNG 打包成 ICO（Vista+ 支持 PNG 压缩条目）"""
    count = len(entries)
    header = struct.pack("<HHH", 0, 1, count)
    offset = 6 + 16 * count
    directory, blobs = b"", b""
    for size, data in entries:
        b = 0 if size >= 256 else size  # 256 用 0 表示
        directory += struct.pack("<BBBBHHII", b, b, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
        blobs += data
    path.write_bytes(header + directory + blobs)


def main() -> int:
    if not SRC.exists():
        print(f"找不到 {SRC}")
        return 1

    for size, name in ((256, "icon.png"), (512, "icon-512.png")):
        pb = render(size)
        out = SRC.parent / name
        out.write_bytes(png_bytes(pb))
        print(f"生成 {out.relative_to(ROOT)} ({size}x{size})")

    entries = []
    for size in ICO_SIZES:
        entries.append((size, png_bytes(render(size))))
    ico = SRC.parent / "icon.ico"
    build_ico(entries, ico)
    print(f"生成 {ico.relative_to(ROOT)}（{len(entries)} 个尺寸）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
