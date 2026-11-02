#!/usr/bin/env python -X utf8
# -*- coding: utf-8 -*-
"""上下文成本计量：读一个文件要花多少 token，值不值得读。

依据（经验估算，不是精确 tokenizer）：
  · 中文 ≈ 1 token / 1.2 字
  · 英文/代码 ≈ 1 token / 3.5 字符
  · 混合文本按上面两式分别估算再相加

用法：
  python tools/ctx_meter.py AGENTS.md
  python tools/ctx_meter.py 项目/12-四小时日志.md 工具库索引.md
  python tools/ctx_meter.py --glob "项目/*.md" --top 10
"""
import argparse
import glob
import os
import re
import sys

# 经验系数（明确标注是估算）
CJK_PER_TOKEN = 1.2
LATIN_PER_TOKEN = 3.5
# 提示阈值
WARN_TOKENS = 3000      # 超过就建议别整读
HARD_TOKENS = 8000      # 超过就该 grep/摘要


def estimate(text):
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin = len(text) - cjk
    return int(cjk / CJK_PER_TOKEN + latin / LATIN_PER_TOKEN)


def suggest(tokens):
    if tokens < 800:
        return "可以直接整读"
    if tokens < WARN_TOKENS:
        return "整读也行，但先想清楚要哪一段"
    if tokens < HARD_TOKENS:
        return "别整读：先 grep 命中行，或 read --offset/--limit"
    return "禁止整读：用 grep + 局部 read，或让脚本替你算"


def measure(path):
    try:
        txt = open(path, encoding="utf-8", errors="ignore").read()
    except Exception as e:
        return None
    t = estimate(txt)
    return {"path": path, "chars": len(txt), "lines": txt.count("\n") + 1,
            "tokens": t, "suggest": suggest(t)}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--glob", default=None)
    ap.add_argument("--top", type=int, default=15)
    args = ap.parse_args()

    files = list(args.paths)
    if args.glob:
        files += glob.glob(args.glob, recursive=True)

    rows = [r for r in (measure(f) for f in files if os.path.exists(f)) if r]
    if not rows:
        raise SystemExit("没有可读文件")

    rows.sort(key=lambda r: -r["tokens"])
    print(f"{'文件':<40}{'行':>7}{'字':>9}{'≈token':>9}  建议")
    print("-" * 96)
    for r in rows[:args.top]:
        name = os.path.basename(r["path"])[:38]
        print(f"{name:<40}{r['lines']:>7}{r['chars']:>9}{r['tokens']:>9}  {r['suggest']}")
    total = sum(r["tokens"] for r in rows[:args.top])
    print("-" * 96)
    print(f"合计 ≈ {total} token（{len(rows[:args.top])} 个文件）")
    print("\n省法：①grep 定位行号 → read 局部  ②让脚本算出结论  ③只读索引/摘要")
    return 0


if __name__ == "__main__":
    sys.exit(main())
