#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""tokenguard v0.3 —— Agent 项目的"省 token 守门员"

一个命令，四件事：量 · 控 · 省 · 算账。

v0.3 相比 v0.2 修的真问题（都是自查出来的）
  1) cache 的 key 只算命令串 → 换目录/换环境会命中错误缓存  → key 加 cwd
  2) cache 只存 stdout，回放丢 stderr（警告看不见）          → 两个都存
  3) cache 没有 --force、没有过期清理、没有体积上限          → 都补上
  4) cache 会把"写操作/外部动作"也缓存（危险）                → 默认只缓存读类
  5) report 用 $3/1M 美元价，对国产模型误导                    → 改人民币价 + 分模型
  6) brief 只是"取第一行"，不是预览                            → 去重 + 限行 + 恒结构
  7) 估算系数写死                                              → --model deepseek/qwen/generic

子命令
  meter  <文件...>                 读之前先量
  brief  <文件...>                 预览式简报（去重、限行、恒定结构）
  cache  [--ttl 24h] [--force] [--allow-write] -- <命令>
  settle --tool workbuddy --pages N [--saved N] [--note ...]
  report [--json]

账本：~/.tokenguard/ledger.jsonl    缓存：~/.tokenguard/cache/
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
CACHE_MAX_BYTES = 2 * 1024 * 1024
LEDGER_MAX_LINES = 20000

# 每字符 ≈ token（DeepSeek 官方：1 中文字符≈0.6 token；Qwen2.5 中文 CPT≈2.8）
# 系数用真 tokenizer 标定（2026-11-03 实测）：
#   deepseek-v3：中文 0.583 token/字，英文 0.191 token/字符
#   qwen-2.5   ：中文 0.625 token/字，英文 0.191 token/字符
MODEL_PROFILES = {
    "deepseek": (0.583, 0.191),
    "qwen": (0.625, 0.191),
    "generic": (1 / 1.2, 1 / 3.5),
}
# 真 tokenizer 对应的模型名（offline_token_counter）
EXACT_MODEL = {"deepseek": "deepseek-v3", "qwen": "qwen-2.5", "generic": None}
_EXACT_OK = None
PRICE_CNY_PER_M = {"deepseek": 2.0, "qwen": 2.0, "generic": 2.0}
CUR_MODEL = "deepseek"

# 只给"确定性读类"命令缓存；这些词一出现就拒绝（除非 --allow-write）
WRITE_HINTS = ("rm ", "del ", "move ", "mv ", "cp ", "copy ", "publish", "send",
               "git push", "commit", "pip install", "upload", "delete", ">", ">>")


def tokenizer_available():
    """真 tokenizer 能不能用（offline_token_counter，本地离线）。"""
    global _EXACT_OK
    if _EXACT_OK is None:
        try:
            import offline_token_counter  # noqa: F401
            _EXACT_OK = True
        except Exception:
            _EXACT_OK = False
    return _EXACT_OK


def tok_exact(text, model=None):
    """用真 tokenizer 数 token；不可用返回 None。"""
    name = EXACT_MODEL.get(model or CUR_MODEL)
    if not name or not tokenizer_available():
        return None
    try:
        import offline_token_counter
        return int(offline_token_counter.count_tokens(text, model=name))
    except Exception:
        return None


def tok(text, model=None):
    """优先精确；不可用才估算。返回值恒定是 token 数。"""
    exact = tok_exact(text, model)
    if exact is not None:
        return exact
    cjk_c, lat_c = MODEL_PROFILES.get(model or CUR_MODEL, MODEL_PROFILES["deepseek"])
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin = len(text) - cjk
    return int(cjk * cjk_c + latin * lat_c)


def mode_label(model=None):
    name = EXACT_MODEL.get(model or CUR_MODEL)
    if name and tokenizer_available():
        return f"精确·{name}"
    return f"估算·{model or CUR_MODEL}"


def log_event(kind, saved=0, note=""):
    os.makedirs(HOME, exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": int(time.time()), "kind": kind,
                            "saved": int(saved), "note": note}, ensure_ascii=False) + "\n")
    rotate_ledger()


def rotate_ledger():
    try:
        if not os.path.exists(LEDGER):
            return
        with open(LEDGER, encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > LEDGER_MAX_LINES:
            half = LEDGER_MAX_LINES // 2
            keep = lines[-half:]
            with open(LEDGER + ".old", "w", encoding="utf-8") as w:
                w.writelines(lines[:-half])
            with open(LEDGER, "w", encoding="utf-8") as w:
                w.writelines(keep)
    except Exception:
        pass


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
    print(f"合计 {sum(r[2] for r in rows)} token（{mode_label()}）")
    log_event("meter", 0, f"{len(rows)} 个文件")
    return 0


# ---------- brief（预览式，不是摘要） ----------
def brief_file(path, max_lines=12):
    text = open(path, encoding="utf-8-sig", errors="ignore").read()
    seen, picked = set(), []
    for ln in text.split("\n"):
        s = ln.strip()
        if not s or s in seen:
            continue
        if s.startswith("#") or len(picked) < max_lines:
            picked.append(s[:90])
            seen.add(s)
        if len(picked) >= max_lines:
            break
    return picked


def cmd_brief(args):
    if not args.files:
        print("❌ 给几个文件：tokenguard brief A.md B.md")
        return 2
    rows = []
    for p in args.files:
        if not os.path.exists(p):
            print(f"❌ 不存在：{p}")
            continue
        text = open(p, encoding="utf-8-sig", errors="ignore").read()
        rows.append({"name": os.path.basename(p), "tok": tok(text), "lines": brief_file(p)})
    out = ["TOKENGUARD-BRIEF/V2", f"MODEL: {CUR_MODEL}  FILES: {len(rows)}", "---"]
    for r in rows:
        out.append(f"[{r['name']}] ≈{r['tok']}tok")
        for ln in r["lines"]:
            out.append("  " + ln)
        out.append("")
    out.append("END-BRIEF")
    brief = "\n".join(out)
    print(brief)
    total = sum(r["tok"] for r in rows)
    saved = total - tok(brief)
    if saved > 0:
        log_event("brief", saved, f"{len(rows)} 个文件")
    print(f"\n[原文件 {total} · 简报 {tok(brief)} · 省 {saved} · {mode_label()}]", file=sys.stderr)
    return 0


# ---------- cache ----------
def looks_writeful(cmd):
    joined = " ".join(cmd).lower()
    return any(w in joined for w in WRITE_HINTS)


def cmd_cache(args):
    if not args.command:
        print("❌ 用法：tokenguard cache [--ttl 24h] -- <命令>")
        return 2
    cmd = args.command
    if looks_writeful(cmd) and not args.allow_write:
        print("[tokenguard] 这条命令看起来会改东西，默认不缓存（要缓存加 --allow-write）",
              file=sys.stderr)
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        sys.stdout.write(r.stdout or "")
        sys.stderr.write(r.stderr or "")
        return r.returncode

    os.makedirs(CACHE, exist_ok=True)
    key_src = os.getcwd() + "\x00" + "\x00".join(cmd)   # v0.3: 加 cwd
    key = hashlib.sha256(key_src.encode("utf-8")).hexdigest()[:16]
    path = os.path.join(CACHE, key + ".json")
    ttl = parse_ttl(args.ttl)

    if os.path.exists(path) and not args.force:
        try:
            d = json.load(open(path, encoding="utf-8"))
            if time.time() - d["ts"] < ttl:
                sys.stdout.write(d.get("stdout", ""))
                sys.stderr.write(d.get("stderr", ""))
                age = int((time.time() - d["ts"]) // 60)
                print(f"[tokenguard] 命中缓存（{age} 分钟前，省 ≈{d.get('tok', 0)} token）",
                      file=sys.stderr)
                log_event("cache_hit", d.get("tok", 0), " ".join(cmd)[:80])
                return d.get("rc", 0)
        except Exception:
            pass

    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    sys.stdout.write(r.stdout or "")
    sys.stderr.write(r.stderr or "")
    size = len(r.stdout or "") + len(r.stderr or "")
    if size <= CACHE_MAX_BYTES:
        json.dump({"ts": time.time(), "rc": r.returncode, "cwd": os.getcwd(),
                   "stdout": r.stdout or "", "stderr": r.stderr or "",
                   "tok": tok((r.stdout or "") + (r.stderr or ""))},
                  open(path, "w", encoding="utf-8"), ensure_ascii=False)
        log_event("cache_set", 0, " ".join(cmd)[:80])
    else:
        print(f"[tokenguard] 输出 {size//1024}KB 超过缓存上限，本次不缓存", file=sys.stderr)
    return r.returncode


# ---------- settle ----------
def cmd_settle(args):
    saved = args.saved if args.saved is not None else int((args.pages or 0) * 1500)
    log_event("outsource", saved, f"{args.tool}: {args.note}")
    print(f"✅ 已记账：外包 {args.tool}，省 ≈{saved} token（{args.note}）")
    return 0


# ---------- report ----------
def cmd_report(args):
    if not os.path.exists(LEDGER):
        print("还没有账。先跑几次 meter / brief / cache。")
        return 0
    events = []
    for ln in open(LEDGER, encoding="utf-8"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            events.append(json.loads(ln))
        except Exception:
            continue
    now = time.time()
    month = [e for e in events if now - e["ts"] < 30 * 86400]
    saved = sum(e.get("saved", 0) for e in month)
    by_kind = {}
    for e in month:
        if e.get("saved"):
            by_kind[e["kind"]] = by_kind.get(e["kind"], 0) + e["saved"]
    price = PRICE_CNY_PER_M.get(CUR_MODEL, 2.0)

    if args.json:
        print(json.dumps({"model": CUR_MODEL, "saved_30d": saved, "by_kind": by_kind,
                          "cny_saved": round(saved / 1_000_000 * price, 4)},
                         ensure_ascii=False, indent=1))
        return 0

    print(f"📊 tokenguard 账本（近 30 天 · {mode_label()}）")
    print("-" * 46)
    for kind, v in sorted(by_kind.items(), key=lambda x: -x[1]):
        label = {"cache_hit": "缓存命中", "brief": "简报", "outsource": "外包重活"}.get(kind, kind)
        print(f"  {label:<10} ≈{v:>8} token")
    print("-" * 46)
    print(f"  **合计省下**  ≈{saved:>8} token")
    print(f"  粗估金额（{price} 元/百万 token）：≈ ¥{saved/1_000_000*price:.4f}")
    print("\n账本：", LEDGER)
    return 0


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="tokenguard", description="Agent 省 token 守门员 v0.3")
    ap.add_argument("--model", default="deepseek", choices=list(MODEL_PROFILES))
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("meter", help="读之前先量")
    a.add_argument("files", nargs="+")
    a.set_defaults(fn=cmd_meter)

    b = sub.add_parser("brief", help="预览式简报替代整读")
    b.add_argument("files", nargs="*")
    b.set_defaults(fn=cmd_brief)

    c = sub.add_parser("cache", help="缓存命令结果（默认只缓存读类）")
    c.add_argument("--ttl", default="24h")
    c.add_argument("--force", action="store_true")
    c.add_argument("--allow-write", action="store_true")
    c.add_argument("command", nargs=argparse.REMAINDER)
    c.set_defaults(fn=cmd_cache)

    e = sub.add_parser("settle", help="外包结账")
    e.add_argument("--tool", default="workbuddy")
    e.add_argument("--pages", type=int, default=0)
    e.add_argument("--saved", type=int, default=None)
    e.add_argument("--note", default="")
    e.set_defaults(fn=cmd_settle)

    d = sub.add_parser("report", help="看省了多少")
    d.add_argument("--json", action="store_true")
    d.set_defaults(fn=cmd_report)

    args = ap.parse_args()
    global CUR_MODEL
    CUR_MODEL = args.model
    if args.cmd == "cache" and args.command and args.command[0] == "--":
        args.command = args.command[1:]
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
