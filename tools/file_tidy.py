#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""文件夹整理器：按类型把文件归到子目录，带预演、日志、一键撤销。

用法:
  python file_tidy.py <目录> --dry-run          # 只预演，不动文件
  python file_tidy.py <目录>                    # 真整理
  python file_tidy.py <目录> --undo <日志文件>   # 撤销上一次整理
"""
import argparse
import json
import os
import shutil
import sys
import time

CATEGORIES = {
    "图片": {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"},
    "文档": {".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".odt"},
    "表格": {".xls", ".xlsx", ".csv", ".ods"},
    "演示": {".ppt", ".pptx", ".key", ".odp"},
    "音视频": {".mp3", ".wav", ".mp4", ".mkv", ".mov", ".avi", ".flac"},
    "压缩包": {".zip", ".rar", ".7z", ".tar", ".gz"},
    "程序": {".exe", ".msi", ".bat", ".ps1", ".py", ".js", ".json"},
}


def category_of(name):
    ext = os.path.splitext(name)[1].lower()
    for cat, exts in CATEGORIES.items():
        if ext in exts:
            return cat
    return "其他"


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def scan(root):
    items = []
    for name in sorted(os.listdir(root)):
        p = os.path.join(root, name)
        if not os.path.isfile(p):
            continue
        items.append({
            "name": name,
            "src": p,
            "cat": category_of(name),
            "size": os.path.getsize(p),
        })
    return items


def plan(items, root):
    ops = []
    for it in items:
        dst_dir = os.path.join(root, it["cat"])
        dst = os.path.join(dst_dir, it["name"])
        if os.path.exists(dst):
            base, ext = os.path.splitext(it["name"])
            i = 1
            while os.path.exists(os.path.join(dst_dir, f"{base}_{i}{ext}")):
                i += 1
            dst = os.path.join(dst_dir, f"{base}_{i}{ext}")
        ops.append({"src": it["src"], "dst": dst, "cat": it["cat"],
                    "size": it["size"]})
    return ops


def show(ops, root):
    if not ops:
        print("没有需要整理的文件。")
        return
    groups = {}
    for op in ops:
        groups.setdefault(op["cat"], []).append(op)
    total = sum(o["size"] for o in ops)
    print(f"预演：{len(ops)} 个文件，共 {human(total)}")
    for cat, group in groups.items():
        size = sum(o["size"] for o in group)
        print(f"\n  [{cat}]  {len(group)} 个 / {human(size)}")
        for o in group[:5]:
            print(f"    {os.path.basename(o['src'])}  ->  {cat}/")
        if len(group) > 5:
            print(f"    …… 还有 {len(group) - 5} 个")


def execute(ops, root):
    log = {
        "root": root,
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "moves": [],
    }
    for op in ops:
        os.makedirs(os.path.dirname(op["dst"]), exist_ok=True)
        shutil.move(op["src"], op["dst"])
        log["moves"].append({"from": op["dst"], "to": op["src"]})
    log_path = os.path.join(
        os.path.dirname(root.rstrip("\\/")),
        f"tidy-log-{time.strftime('%Y%m%d-%H%M%S')}.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    print(f"\n已整理 {len(ops)} 个文件。")
    print(f"撤销日志：{log_path}")
    print(f"要撤销：python file_tidy.py \"{root}\" --undo \"{log_path}\"")
    return log_path


def undo(root, log_path):
    with open(log_path, encoding="utf-8") as f:
        log = json.load(f)
    moved = 0
    for mv in log["moves"]:
        src, dst = mv["from"], mv["to"]
        if not os.path.exists(src):
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        moved += 1
    # 清掉空目录
    for cat in CATEGORIES.keys() | {"其他"}:
        d = os.path.join(log["root"], cat)
        if os.path.isdir(d) and not os.listdir(d):
            os.rmdir(d)
    print(f"已撤销 {moved} 个文件。")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="文件夹整理器（可预演、可撤销）")
    ap.add_argument("root", help="要整理的目录")
    ap.add_argument("--dry-run", action="store_true", help="只预演，不动文件")
    ap.add_argument("--undo", metavar="LOG", help="按日志撤销")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print("目录不存在：", root)
        return 1

    if args.undo:
        undo(root, args.undo)
        return 0

    items = scan(root)
    ops = plan(items, root)
    show(ops, root)
    if args.dry_run:
        print("\n（预演模式，没有改动任何文件。）")
        return 0
    if not ops:
        return 0
    ans = input("\n确认整理？输入 y 继续：").strip().lower()
    if ans != "y":
        print("已取消。")
        return 0
    execute(ops, root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
