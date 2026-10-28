#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PDF 小工具箱：合并 / 拆分 / 提文字 / 图片转 PDF。

用法:
  python pdf_kit.py merge  a.pdf b.pdf -o 合并.pdf
  python pdf_kit.py split  大.pdf --pages 1-3,7 -o 拆分#.pdf
  python pdf_kit.py text   a.pdf -o 文本.txt
  python pdf_kit.py fromimg 图片目录 -o 影集.pdf
"""
import argparse
import glob
import os
import sys

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    print("需要 pypdf：pip install pypdf")
    raise SystemExit(1)


def cmd_merge(args):
    w = PdfWriter()
    total = 0
    for p in args.files:
        r = PdfReader(p)
        for page in r.pages:
            w.add_page(page)
        total += len(r.pages)
        print(f"  + {os.path.basename(p)}  {len(r.pages)} 页")
    with open(args.out, "wb") as f:
        w.write(f)
    print(f"已合并 {len(args.files)} 个文件，共 {total} 页 -> {args.out}")


def parse_ranges(spec):
    out = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            out.append((int(a), int(b)))
        else:
            n = int(part)
            out.append((n, n))
    return out


def cmd_split(args):
    r = PdfReader(args.file)
    n = len(r.pages)
    print(f"原文件 {n} 页")
    ranges = parse_ranges(args.pages)
    made = 0
    for i, (a, b) in enumerate(ranges, 1):
        if a < 1 or b > n or a > b:
            print(f"  跳过越界范围 {a}-{b}")
            continue
        w = PdfWriter()
        for p in range(a - 1, b):
            w.add_page(r.pages[p])
        out = args.out.replace("#", str(i))
        with open(out, "wb") as f:
            w.write(f)
        print(f"  {a}-{b} 页 -> {out}")
        made += 1
    print(f"已生成 {made} 个文件")


def cmd_text(args):
    r = PdfReader(args.file)
    chunks = []
    for i, page in enumerate(r.pages, 1):
        t = page.extract_text() or ""
        chunks.append(f"===== 第 {i} 页 =====\n{t}")
    body = "\n\n".join(chunks)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(body)
    # 只统计正文，不含页码分隔符
    real = sum(len((page.extract_text() or "").strip()) for page in r.pages)
    print(f"{len(r.pages)} 页 -> {args.out}（正文 {real} 字符）")
    if real < 50:
        print("⚠️ 提取到的文字很少，可能是扫描件（需要 OCR）")


def cmd_fromimg(args):
    from PIL import Image
    files = []
    for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp", "*.bmp"):
        files += glob.glob(os.path.join(args.dir, ext))
        files += glob.glob(os.path.join(args.dir, ext.upper()))
    files = sorted(set(files))
    if not files:
        print("目录里没有图片。")
        return 1
    imgs = []
    for f in files:
        im = Image.open(f).convert("RGB")
        imgs.append(im)
        print(f"  + {os.path.basename(f)}  {im.width}x{im.height}")
    imgs[0].save(args.out, save_all=True, append_images=imgs[1:])
    print(f"已生成 {len(imgs)} 页 PDF -> {args.out}")
    return 0


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="PDF 小工具箱")
    sub = ap.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("merge", help="合并多个 PDF")
    m.add_argument("files", nargs="+")
    m.add_argument("-o", "--out", default="合并.pdf")
    m.set_defaults(func=cmd_merge)

    s = sub.add_parser("split", help="按页范围拆分")
    s.add_argument("file")
    s.add_argument("--pages", required=True, help="如 1-3,7,10-12")
    s.add_argument("-o", "--out", default="拆分#.pdf")
    s.set_defaults(func=cmd_split)

    t = sub.add_parser("text", help="提取文字")
    t.add_argument("file")
    t.add_argument("-o", "--out", default="提取.txt")
    t.set_defaults(func=cmd_text)

    i = sub.add_parser("fromimg", help="图片目录转 PDF")
    i.add_argument("dir")
    i.add_argument("-o", "--out", default="图片集.pdf")
    i.set_defaults(func=cmd_fromimg)

    args = ap.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
