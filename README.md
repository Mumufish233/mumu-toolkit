# mumu-toolkit

> 小而干脆的工具集：**每个都先给判断，再动手；能撤回的才敢改。**
> Small, dependency-light tools. **Preview first. Never break things silently.**

[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](#license)

---

## 里面有什么

| 目录 | 干什么 | 一句话 |
|---|---|---|
| **[tokenguard/](tokenguard/)** | **给 Agent 省 token**（读前守门 / 量 / 简报 / 缓存 / 账本）| 让 token 浪费可见，再谈省 |
| `tools/` | Windows 自动化（表格合并 / 文件整理 / PDF / 批量改名）| 先预演、可撤销、绝不删除 |
| `token-saver/` | 最早的三件套（ctx_meter / log_rotate / smoke_all）| tokenguard 的散装版 |

---

## 1. tokenguard —— 主推

**一个命令，五件事：量 · 控 · 省 · 算账 · 守门。**

```bash
python tokenguard/tokenguard.py read  大文件.md              # 读前守门：超预算只给预览
python tokenguard/tokenguard.py meter 文件A 文件B            # 量：值不值得读
python tokenguard/tokenguard.py brief 文件A                  # 简报：骨架替代整读
python tokenguard/tokenguard.py cache --ttl 24h -- <命令>    # 缓存：只缓存读类
python tokenguard/tokenguard.py report                       # 账本：省了多少
```

**实测（我们自己项目，精确 tokenizer 计数）**

| 场景 | 以前 | 现在 | 省 |
|---|---|---|---|
| 读一个 31,453 token 的日志 | 31,453 | **329** | **99%** |
| 每次开工恢复上下文 | 31,325 | **192** | 99% |
| 日志按月切分后整读 | 63,228 | 23,782 | 62% |
| 重复命令第二次运行 | 5,000 | **0** | 100% |

**30 天账本累计省下 ≈104,000 token**（`tokenguard report` 自己算的）。

**边界（先说清楚）**：不改模型、不做摘要、单人小量省不了多少钱。它的价值是**让浪费可见 + 不让你犯错**。

---

## 2. `tools/` —— Windows 自动化

```bash
python tools/file_tidy.py  D:\Downloads --dry-run     # 先预演
python tools/file_tidy.py  D:\Downloads               # 确认后执行（写撤销日志）
python tools/file_tidy.py  D:\Downloads --undo <log>  # 一条命令撤回
python tools/excel_merge.py  a.xlsx b.xlsx -o out.xlsx
python tools/pdf_kit.py     merge  a.pdf b.pdf -o out.pdf
python tools/rename_batch.py D:\某目录 --pattern "*.jpg"
```

三条立场：**`--dry-run` 先预演 · 每步可撤销 · 绝不删除（只移动）**。

---

## 3. `token-saver/` —— 散装三件套

```bash
python token-saver/tools/ctx_meter.py 文件              # 估 token
python token-saver/tools/log_rotate.py --log 日志.md --archive 归档/ --apply
python token-saver/tools/smoke_all.py --tools-dir tools/  # 批量脚本冒烟
```

---

## 为什么值得看

- **每个工具都有边界声明**：不吹牛，写清它做不到什么
- **每个数字都可复现**：跑一遍命令就能自己验证
- **每个改动能撤回**：文件操作有撤销日志，缓存有 `--force`

---

## License

MIT。拿走用，改完不用告诉我，但改了 bug 建议提个 issue。
