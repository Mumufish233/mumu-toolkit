#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""批量重命名：序号 / 日期 / 正则替换，全部先预演、可撤销。

用法:
  # 看预演（不动文件）
  python rename_batch.py D:\\图片 --prefix 照片 --seq 3 --dry-run

  # 真改名
  python rename_batch.py D:\\图片 --prefix 照片 --seq 3

  # 正则替换
  python rename_batch.py D:\\下载 --regex "第(\\d+)集" --replace "EP\\1"

  # 纯日期前缀
  python rename_batch.py D:\\截图 --date %Y%m%d --seq 2

  # 撤销
  python rename_batch.py D:\\图片 --undo rename-log-xxx.json
"""
import argparse
import json
import os
import re
import sys
import time


def natural_key(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def build_plan(files, args):
    """新名 = [日期_] [前缀_] [序号_] 主体[_原后缀]
    主体默认是原名（不含扩展名），有 --regex 时是替换后的结果。
    """
    plan = []
    used = set()
    for i, name in enumerate(files, start=1):
        base, ext = os.path.splitext(name)

        body = re.sub(args.regex, args.replace or "", base) if args.regex else base

        parts = []
        if args.date:
            mtime = os.path.getmtime(os.path.join(args.root, name))
            parts.append(time.strftime(args.date, time.localtime(mtime)))
        if args.prefix:
            parts.append(args.prefix)
        if args.seq:
            parts.append(str(i).zfill(args.seq))
        parts.append(body)

        new_base = args.sep.join(p for p in parts if p != "")
        candidate = new_base + ext

        # 防重名：已用过或磁盘已存在其它文件 -> 加 _1 _2
        k, final = 1, candidate
        while final.lower() in used or (
                os.path.exists(os.path.join(args.root, final)) and final != name):
            final = f"{new_base}_{k}{ext}"
            k += 1
        used.add(final.lower())
        plan.append((name, final))
    return plan


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="批量重命名（可预演、可撤销）")
    ap.add_argument("root")
    ap.add_argument("--prefix", default=None, help="前缀")
    ap.add_argument("--seq", type=int, default=0, help="序号位数，如 3 -> 001")
    ap.add_argument("--sep", default="_", help="分隔符，默认下划线")
    ap.add_argument("--date", default=None, help="日期前缀，strftime 格式，如 %%Y%%m%%d")
    ap.add_argument("--regex", default=None, help="正则匹配（作用在文件名不含扩展名部分）")
    ap.add_argument("--replace", default=None, help="正则替换内容，支持 \\\\1 反向引用")
    ap.add_argument("--keep-name", action="store_true", help="保留原名，只加前缀/序号")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--undo", metavar="LOG")
    args = ap.parse_args()

    root = args.root
    if not os.path.isabs(root):
        root = os.path.abspath(root)
    if not os.path.isdir(root):
        print("目录不存在：", root)
        return 1

    if args.undo:
        with open(args.undo, encoding="utf-8") as f:
            log = json.load(f)
        n = 0
        for mv in log["moves"]:
            src = os.path.join(root, mv["new"])
            dst = os.path.join(root, mv["old"])
            if os.path.exists(src) and not os.path.exists(dst):
                os.rename(src, dst)
                n += 1
        print(f"已撤销 {n} 个改名。")
        return 0

    files = [f for f in os.listdir(root)
             if os.path.isfile(os.path.join(root, f)) and not f.startswith(".")]
    files.sort(key=natural_key)
    if not files:
        print("目录里没有文件。")
        return 1

    args.root = root
    plan = build_plan(files, args)
    changed = [(a, b) for a, b in plan if a != b]
    print(f"共 {len(files)} 个文件，需要改名 {len(changed)} 个")
    for a, b in changed[:20]:
        print(f"  {a}  ->  {b}")
    if len(changed) > 20:
        print(f"  …… 还有 {len(changed) - 20} 个")

    if args.dry_run:
        print("\n（预演模式，没有改动任何文件。）")
        return 0
    if not changed:
        return 0

    ans = input("\n确认改名？输入 y 继续：").strip().lower()
    if ans != "y":
        print("已取消。")
        return 0

    moves = []
    for a, b in changed:
        os.rename(os.path.join(root, a), os.path.join(root, b))
        moves.append({"old": a, "new": b})
    log_path = os.path.join(os.path.dirname(root),
                            f"rename-log-{time.strftime('%Y%m%d-%H%M%S')}.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump({"root": root, "moves": moves}, f, ensure_ascii=False, indent=2)
    print(f"\n已改名 {len(moves)} 个。")
    print(f"撤销日志：{log_path}")
    print(f"要撤销：python rename_batch.py \"{root}\" --undo \"{log_path}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
