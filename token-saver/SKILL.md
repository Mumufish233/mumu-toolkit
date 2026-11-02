---
name: dsh-token-saver
description: 给长期运行的 AI Agent 省 token：读前量成本（ctx_meter）、切巨型日志（log_rotate）、工具冒烟体检（smoke_all）。当上下文快满、日志过大、脚本多到记不住、或怀疑某个工具坏了时使用。
---

# Agent 省 token：三个动作

## 什么时候用（触发条件）

| 症状 | 动作 |
|---|---|
| 想读一个文件，但不确定要花多少 | `ctx_meter.py <文件>`，看建议再决定 |
| 日志/笔记文件 > 50 千字 | `log_rotate.py` 按月切 |
| 改了公共函数，怕弄坏别的脚本 | `smoke_all.py --tools-dir tools/` |
| 每轮开头要恢复状态 | 用**定长前缀简报**（见下），别整读日志 |

---

## 动作一：读之前先量

```bash
python tools/ctx_meter.py <文件...>
python tools/ctx_meter.py --glob "项目/*.md" --top 10
```

按输出建议行动：

| 建议 | 该怎么做 |
|---|---|
| 可以直接整读 | 读 |
| 整读也行，但先想清楚要哪一段 | 先想问题，再读 |
| 别整读：先 grep 命中行 | `grep` → `read --offset/--limit` |
| 禁止整读 | 让脚本替你算结论，别把文件塞进上下文 |

**硬阈值**：>3000 token 不许整读；>8000 token 只许看脚本算出来的结论。

## 动作二：日志按月切

```bash
python tools/log_rotate.py --log <日志.md> --archive <归档目录>            # 预览
python tools/log_rotate.py --log <日志.md> --archive <归档目录> --apply    # 真切（自动备份）
```

- 按 `## YYYY-MM-DD` 切块；本月留主文件，往月进归档
- 切完再量一次：`ctx_meter.py <日志.md>` 确认体积降下来
- 建议每月底跑一次，或者主文件 >50 千字就跑

## 动作三：工具冒烟

```bash
python tools/smoke_all.py --tools-dir tools/
```

- 只测 argparse 工具，排除危险名单（会发消息/开浏览器/花钱的）
- 失败会列出具体脚本 + 最后一行错误
- **接进自检**：让你的自检脚本把这条当一项，健康分里体现

---

## 定长前缀简报（配套思路，不含代码）

每轮开工不要读日志，读一份**结构恒定**的简报，例如：

```
PROJECT-BRIEF/V1
SCOPE: <这轮要干什么>
RULE: <三条纪律>
PENDING: <唯一待办>
STATE:
  收入 <数字>
  工具 <数字> 索引 <同步/需重跑>
  别整读 <最重的 3 个文件>≈<token>
END-STATE
```

**为什么要定长**：每次开头几行完全相同 → 更容易命中前缀缓存；人也能一眼扫完。

---

## 反模式（花 token 没效果）

- 把整个日志/知识库贴进对话"让模型参考"
- 为了找一段配置通读 3000 行代码
- 同一个查询跑两遍（先看有没有落盘缓存）
- 让 Agent"回忆"以前做过什么（应该写进文件，用 grep 查）

---

## 验证方法

1. 跑 `ctx_meter.py` 记录改动前的 log 体积
2. 跑 `log_rotate.py --apply`
3. 再跑 `ctx_meter.py` 对比
4. 把两个数字写进你的日志——**没有数字的优化不算优化**
