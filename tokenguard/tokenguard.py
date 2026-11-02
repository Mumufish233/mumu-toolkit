#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""tokenguard —— Agent 项目的"省 token 守门员"（v0.2 原型）

一句话：**一个命令，四件事——量、控、省、算账。**

为什么需要它（真实痛点）：
  用 Agent 的人都知道账单疼，但**没人知道痛在哪**：
  是读了太大文件？是同一命令跑了几十遍？是每次都把日志整读？
  tokenguard 把这四件事变成四个子命令，并且**把省下的量记成账**。

子命令：
  meter  <文件...>              读之前先量：这个文件要花多少 token
  brief  <文件...>              生成定长简报（替代整读，前缀稳定利于缓存）
  cache  --ttl 24h -- <命令>    缓存命令结果；命中就不重跑（省的是输入 token）
  report                        看账：这个月一共省了多少 token

账本：`~/.tokenguard/ledger.jsonl`（每行一条，可删）

用法示例：
  python tools/tokenguard.py meter AGENTS.md 项目/日志.md
  python tools/tokenguard.py cache --ttl 24h -- python tools/listing_health.py
  python tools/tokenguard.py report
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time

HOME = os.path.expanduser("~/.tokenguard")
LEDGER = os.path.join(HOME, "ledger.jsonl")
CACHE = os.path.join(HOME, "cache")


# ---------- 通用 ----------
def tok(text):
    """估算：中文 1.2 字/token，英文 3.5 字符/token。"""
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    return int(cjk / 1.2 + (len(text) - cjk) / 3.5)


def log_event(kind, saved=0, note=""):
    os.makedirs(HOME, exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": int(time.time()), "kind": kind, "saved": int(saved), "note": note},
                           ensure_ascii=False) + "\n")


def parse_ttl(s):
    m = re.match(r"^(\d+)\s*([smhd]?)$", str(s).strip())
    if not m:
        return 24 * 3600
    n, unit = int(m.group(1)), m.group(2) or "h"
    return n * {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]


# ---------- meter ----------
def cmd_meter(args):
    rows = []
    for p in args.files:
        if not os.path.exists(p):
            print(f"❌ 不存在：{p}")
            continue
        text = open(p, encoding="utf-8-sig", errors="ignore").read()
        t = tok(text)
        verdict = ("可以直接读" if t < 800 else
                   "想清楚再读" if t < 3000 else
                   "别整读：grep + 局部" if t < 8000 else
                   "禁止整读：让脚本算结论")
        rows.append((p, len(text), t, verdict))
    if not rows:
        return 1
    rows.sort(key=lambda r: -r[2])
    print(f"{'文件':<38}{'字':>9}{'≈token':>9}  建议")
    print("-" * 78)
    for p, n, t, v in rows:
        print(f"{os.path.basename(p)[:36]:<38}{n:>9}{t:>9}  {v}")
    print("-" * 78)
    print(f"合计 ≈{sum(r[2] for r in rows)} token")
    log_event("meter", 0, f"{len(rows)} 个文件")
    return 0


# ---------- brief ----------
def cmd_brief(args):
    files = args.files
    if not files:
        print("❌ 给几个文件：tokenguard brief A.md B.md")
        return 2
    rows = []
    for p in files:
        text = open(p, encoding="utf-8-sig", errors="ignore").read()
        rows.append((os.path.basename(p), tok(text), text))
    out = ["TOKENGUARD-BRIEF/V1", "FILES:"]
    for name, t, _ in rows:
        out.append(f"  {name} ≈{t}tok")
    out.append("STATE:")
    for name, t, text in rows:
        first = next((ln.strip() for ln in text.split("\n") if ln.strip()), "")
        out.append(f"  {name}: {first[:60]}")
    out.append("END-BRIEF")
    brief = "\n".join(out)
    print(brief)
    saved = sum(t for _, t, _ in rows) - tok(brief)
    log_event("brief", max(0, saved), f"{len(rows)} 个文件")
    print(f"\n（省 ≈{saved} token）", file=sys.stderr)
    return 0


# ---------- cache ----------
def cmd_cache(args):
    if not args.command:
        print("❌ 用法：tokenguard cache --ttl 24h -- <命令>")
        return 2
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.sha256(" ".join(args.command).encode("utf-8")).hexdigest()[:16]
    path = os.path.join(CACHE, key + ".json")
    ttl = parse_ttl(args.ttl)

    if os.path.exists(path):
        try:
            d = json.load(open(path, encoding="utf-8"))
            if time.time() - d["ts"] < ttl:
                print(d["stdout"], end="")
                saved = d.get("tok", 0)
                print(f"\n[tokenguard] 命中缓存（{int((time.time()-d['ts'])//60)} 分钟前），"
                      f"省 ≈{saved} token", file=sys.stderr)
                log_event("cache_hit", saved, " ".join(args.command)[:80])
                return d.get("rc", 0)
        except Exception:
            pass

    r = subprocess.run(args.command, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    print(r.stdout or "", end="")
    if r.stderr:
        print(r.stderr, end="", file=sys.stderr)
    d = {"ts": time.time(), "rc": r.returncode, "stdout": r.stdout or "",
         "tok": tok(r.stdout or "")}
    json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    log_event("cache_set", 0, " ".join(args.command)[:80])
    return r.returncode


# ---------- report ----------
def cmd_report(args):
    if not os.path.exists(LEDGER):
        print("还没有账。先跑几次 meter / brief / cache。")
        return 0
    events = [json.loads(ln) for ln in open(LEDGER, encoding="utf-8") if ln.strip()]
    now = time.time()
    month = [e for e in events if now - e["ts"] < 30 * 86400]
    saved = sum(e["saved"] for e in month)
    hits = sum(1 for e in month if e["kind"] == "cache_hit")
    briefs = sum(1 for e in month if e["kind"] == "brief")
    meters = sum(1 for e in month if e["kind"] == "meter")

    print("📊 tokenguard 账本（近 30 天）")
    print("-" * 44)
    print(f"  量过文件      {meters:>5} 次")
    print(f"  生成简报      {briefs:>5} 次")
    print(f"  缓存命中      {hits:>5} 次")
    print(f"  **省下 token**  ≈{saved:>8}")
    print("-" * 44)
    # 给一个"相当于多少钱"的粗估（按主流价 $3/1M input 折算，仅示意）
    print(f"  粗估（按 $3/1M 输入价）：≈ ${saved/1_000_000*3:.4f}")
    print("\n账本文件：", LEDGER)
    return 0


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="tokenguard", description="Agent 省 token 守门员")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("meter", help="读之前先量")
    a.add_argument("files", nargs="+")
    a.set_defaults(fn=cmd_meter)

    b = sub.add_parser("brief", help="定长简报替代整读")
    b.add_argument("files", nargs="*")
    b.set_defaults(fn=cmd_brief)

    c = sub.add_parser("cache", help="缓存命令结果")
    c.add_argument("--ttl", default="24h")
    c.add_argument("command", nargs=argparse.REMAINDER)
    c.set_defaults(fn=cmd_cache)

    d = sub.add_parser("report", help="看省了多少")
    d.set_defaults(fn=cmd_report)

    args = ap.parse_args()
    if args.cmd == "cache" and args.command and args.command[0] == "--":
        args.command = args.command[1:]
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
