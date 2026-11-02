#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""日志按月切分：把越来越大的 `12-四小时日志.md` 拆成归档 + 近期视图。

为什么：日志 3920 行 / 11 万字 ≈ **5.6 万 token**，整读一次就烧掉一大截上下文。
切分后：
  · `项目/日志归档/2026-11.md` —— 该月全部（几乎不用读）
  · `项目/12-四小时日志.md`     —— 只留**本月**（月底再切）

用法：
  python tools/log_rotate.py            # 预览要切出多少行
  python tools/log_rotate.py --apply    # 真切（会备份原文件）
"""
import argparse
import datetime
import os
import re
import shutil
import sys

LOG = os.environ.get("TOKEN_SAVER_LOG", "log.md")
ARCH = os.environ.get("TOKEN_SAVER_ARCHIVE", "log-archive")


def split_by_month(text):
    """按 `## YYYY-MM-DD` 行切块，返回 (前言, [(月份, 块文本)])。按行扫，最稳。"""
    lines = text.split("\n")
    head, blocks, cur_month, cur = [], [], None, []
    for ln in lines:
        m = re.match(r"^## (\d{4})-(\d{2})-\d{2}", ln)
        if m:
            if cur_month is not None:
                blocks.append((cur_month, "\n".join(cur)))
            elif not blocks:
                head = list(cur)
            cur_month = f"{m.group(1)}-{m.group(2)}"
            cur = [ln]
        else:
            cur.append(ln)
    if cur_month is not None:
        blocks.append((cur_month, "\n".join(cur)))
    return "\n".join(head), blocks


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--log", default=LOG)
    ap.add_argument("--archive", default=ARCH)
    args = ap.parse_args()

    log_path, arch_dir = args.log, args.archive
    text = open(log_path, encoding="utf-8-sig").read()   # PowerShell 写的文件常带 BOM
    head, blocks = split_by_month(text)
    months = {}
    for m, body in blocks:
        months.setdefault(m, []).append("## " + body if not body.startswith("## ") else body)

    cur_month = datetime.date.today().strftime("%Y-%m")
    print(f"总长度 {len(text)//1000} 千字 ≈ {len(text)//2} token")
    for m in sorted(months):
        size = sum(len(x) for x in months[m])
        flag = "（保留）" if m == cur_month else "（归档）"
        print(f"  {m}: {len(months[m])} 条 · {size//1000} 千字 {flag}")

    if not args.apply:
        print("\n预览模式。要真切：--apply")
        return 0

    os.makedirs(arch_dir, exist_ok=True)
    kept = []
    for m in sorted(months):
        content = "\n".join(months[m]).rstrip() + "\n"
        if m == cur_month:
            kept.append(content)
            continue
        p = os.path.join(arch_dir, f"{m}.md")
        # 追加，避免重复切
        mode = "a" if os.path.exists(p) else "w"
        with open(p, mode, encoding="utf-8") as f:
            f.write(content)
        print(f"  ✅ 归档 → {p}")

    shutil.copy2(log_path, log_path + f".bak-{datetime.datetime.now():%m%d%H%M}")
    new_text = head.rstrip() + "\n\n" + "\n".join(kept) if kept else head
    open(log_path, "w", encoding="utf-8").write(new_text)
    print(f"\n✅ 主日志从 {len(text)//1000} 千字 → {len(new_text)//1000} 千字（省 {len(text)-len(new_text)} 字 ≈ {(len(text)-len(new_text))//2} token）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
