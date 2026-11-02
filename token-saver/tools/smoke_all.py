#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""工具库冒烟测试：每个工具能不能正常启动（不影响任何真实动作）。

为什么需要：脚本到 130+ 之后，改一个公共函数可能悄悄弄坏别的工具。
`selfcheck` 只查语法（py_compile 能过但 import 就崩的查不出来）。

做法（保守，绝不触发真实动作）：
  1. 只测**源码里用了 argparse** 的工具（它们会拦截 -h，不会真跑业务）
  2. 排除名单里的危险工具（会发商品、会开浏览器、会花钱的）
  3. 每个跑 `python 工具 -h`，超时 20 秒；非 0 退出或超时算失败

用法：
  python tools/smoke_all.py
  python tools/smoke_all.py --verbose
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

TOOLS = os.environ.get("TOKEN_SAVER_TOOLS", os.path.dirname(os.path.abspath(__file__)))

# 危险：会发商品 / 开浏览器 / 调外部付费额度 / 真实交付
RISKY = {
    "publish_xianyu.py", "xianyu_off.py", "listing_health.py", "xy_session.py",
    "xianyu_probe.py", "e2e_tarot.py", "wb_task.py", "doubao_img.py",
    "doubao_batch.py", "doubao_ask.py", "ai_ask.py", "resume_service.py",
    "ef_digest.py", "launch_check.py", "prove_ready.py", "selfcheck.py",
    "build_index.py", "make_reading_pdf.py", "make_tarot_short.py",
    "slideshow_video.py", "add_bgm.py", "make_bgm.py", "make_resume_templates.py",
    "smoke_all.py",
}


def is_argparse(src):
    return "import argparse" in src or "from argparse" in src


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--tools-dir", default=TOOLS)
    args = ap.parse_args()

    tools_dir = args.tools_dir
    files = sorted(glob.glob(os.path.join(tools_dir, "*.py")))
    tested, skipped, failed = 0, [], []

    for f in files:
        name = os.path.basename(f)
        if name in RISKY or name.startswith("_"):
            skipped.append(name)
            continue
        try:
            src = open(f, encoding="utf-8", errors="ignore").read()
        except Exception:
            skipped.append(name)
            continue
        if not is_argparse(src):
            skipped.append(name)
            continue

        try:
            r = subprocess.run([sys.executable, f, "-h"], capture_output=True,
                               text=True, encoding="utf-8", errors="replace",
                               timeout=args.timeout)
        except subprocess.TimeoutExpired:
            failed.append((name, "超时"))
            continue
        tested += 1
        if r.returncode != 0:
            err = ((r.stderr or "").strip().split("\n") or [""])[-1][:110]
            failed.append((name, err))
        elif args.verbose:
            print(f"  ✅ {name}")

    print(f"\n🧪 工具冒烟：测 {tested} 个 · 跳过 {len(skipped)} 个（危险/无 argparse）· 失败 {len(failed)} 个")
    if failed:
        for name, err in failed:
            print(f"  ❌ {name} → {err}")
        print("\n修完再跑一次：python tools/smoke_all.py")
        return 1
    print("  ✅ 全部能启动")
    return 0


if __name__ == "__main__":
    sys.exit(main())
