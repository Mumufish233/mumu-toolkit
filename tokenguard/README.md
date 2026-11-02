# tokenguard · 给 Agent 开发者省 token

> **一个命令，四件事：量 · 控 · 省 · 算账。**
> 免费、MIT、零依赖（纯 Python 标准库）。

![savings](tokenguard-savings.png)

---

## 为什么做它

用 AI Agent 的人几乎都碰到同一件事：**账单在涨，但不知道涨在哪。**

- 是读了一个 5 万 token 的大文件？
- 是同一条命令跑了几十遍？
- 是每轮都在把同一段历史重新塞进去？

**大多数"省 token 指南"告诉你要少读——问题是你不知道哪个文件该少读。**
tokenguard 就是干这个：**先让浪费可见，再谈省。**

---

## 四个子命令

### 1. 量：`meter` —— 读之前先量

```bash
python tokenguard.py meter AGENTS.md 项目/日志.md
```

```
文件                          字   ≈token  建议
AGENTS.md                  9047     4443  别整读：grep + 局部
12-四小时日志.md            48117    23782  禁止整读：让脚本算结论
合计 ≈28225 token
```

**阈值**：<800 可整读 / 800–3000 想清楚 / 3000–8000 用 grep+局部 / >8000 别整读。

### 2. 控：`brief` —— 定长简报替代整读

```bash
python tokenguard.py brief AGENTS.md 计划.md
```

输出结构恒定（前缀稳定 → 更容易命中前缀缓存），把"整读"换成"看骨架"。
实测：**5,509 token → 192 token。**

### 3. 省：`cache` —— 命令结果缓存

```bash
python tokenguard.py cache --ttl 24h -- python tools/selfcheck.py
```

命中就复用，不重跑、不把输出再喂一遍模型。第二次运行直接返回缓存内容。

### 4. 算账：`report` —— 看省了多少

```bash
python tokenguard.py report
```

```
📊 tokenguard 账本（近 30 天）
  量过文件          12 次
  生成简报           8 次
  缓存命中          31 次
  **省下 token**  ≈   47,552
  粗估（按 $3/1M 输入价）：≈ $0.14
```

账本在 `~/.tokenguard/ledger.jsonl`，一行一条，可删可改。

---

## 装法

**零安装**：把 `tokenguard.py` 复制进你的项目，直接 `python tokenguard.py ...`。

想全局用：

```bash
# Windows
copy tokenguard.py %USERPROFILE%\bin\tokenguard.py   # 再自己配个 doskey/aliases
# macOS/Linux
cp tokenguard.py ~/bin/tokenguard && chmod +x ~/bin/tokenguard
```

依赖：**Python 3.8+，无第三方包**。

---

## 实测数字（同一项目，由本工具自己算出）

| 场景 | 以前 | 现在 | 省 |
|---|---|---|---|
| 每次开工恢复上下文 | 31,325 | **192** | 99% |
| 日志整读（按月切前后）| 63,228 | **23,782** | 62% |
| 重复命令第二次运行 | 5,000 | **0** | 100% |

---

## 它不做什么（边界）

- **不改模型**：KV cache、投机解码、路由都在服务端，这个工具碰不到
- **不保证精确**：token 数是估算（中文 ≈1.2 字/token，英文 ≈3.5 字符/token），够用来决策
- **不替你改代码**：只给判断和建议

---

## 给团队用（后续）

个人看 `report` 就够了；**团队才需要"谁在烧钱"**：

- 按项目/按人汇总的账本
- 超预算告警
- CI 卡口：超过预算的读取直接失败

如果你在做团队版，欢迎开 issue 说需求。

---

## License

MIT。拿走用，改完不用告诉我。

---

## 🔧 v0.3 修了 7 个真问题（自查清单）

| # | 问题 | 为什么会错 | 已修 |
|---|---|---|---|
| 1 | cache 的 key 只算命令串 | **换目录/换环境变量会命中错误缓存** | key 加 cwd |
| 2 | cache 只存 stdout | 回放时**警告/报错看不见**，误以为成功 | 两个都存 |
| 3 | 没有 `--force` / 过期清理 / 体积上限 | 缓存越积越多，大输出塞爆盘 | 都补上（单条 2MB 上限）|
| 4 | **写操作也被缓存** | `git push` 跑一次，第二次"成功"但从没执行 | 默认只缓存读类；写类要 `--allow-write` |
| 5 | report 用 **$3/1M 美元**价 | 对国产模型误导（实际 2 元/M）| 改人民币 + 分模型 |
| 6 | brief 只是"取第一行" | 不是预览，信息量太低 | 去重 + 限行 + 恒结构（V2 格式）|
| 7 | 估算系数写死 | 对 DeepSeek/Qwen 高估 30–100% | `--model deepseek/qwen/generic` |

**最难发现的是第 4 条**：缓存写操作 = **假装成功**。这比多花 token 严重得多。

---

## 已知还不行的地方（下一版）

- **没有真实 tokenizer**：仍是估算（DeepSeek 官方包/`offline-token-counter` 可解决）
- **cache 无并发锁**：两个进程同时写同一 key 可能损坏
- **没有 hook**：还是要手动调；真正省事要接进 Agent 的 tools/pre-execute
- **brief 不是摘要**：只是结构预览，别指望它替代理解

---

## 🎯 v0.4：接了**真 tokenizer**（不再只是估算）

安装（可选，装了就是精确值）：

```bash
pip install offline-token-counter     # 离线，429 个 tokenizer，含 DeepSeek/Qwen
```

```bash
python tokenguard.py --model deepseek meter AGENTS.md
# 合计 5469 token（精确·deepseek-v3）

python tokenguard.py --model qwen meter AGENTS.md
# 合计 5970 token（精确·qwen-2.5）
```

**没装也能用**：自动退回**标定后的估算**（用真 tokenizer 标出来的系数：
DeepSeek 中文 0.583 token/字、英文 0.191 token/字符），并**明确标注"估算"**。

### 精度修正（实测）

| 方式 | AGENTS.md（9,663 字）| 误差 |
|---|---|---|
| 旧估算（1.2 字/token）| 4,443 | **低估 23%** |
| 新标定估算（兜底用）| 4,779 | 低估 13% |
| **真 tokenizer（deepseek-v3）** | **5,469** | 基准 |

**结论：之前所有"省了多少 token"的数字，都偏保守——真实数字更大。**
（比如日志整读从"23,782"修正为 **31,091** token）

### 用真 tokenizer 量出来的真相（我们自己的库）

| 文件 | 真实 token |
|---|---|
| `12-四小时日志.md` | **31,091** |
| `工具库索引.md` | 6,116 |
| `视频-最小流水线.md` | 5,542 |
| `AGENTS.md` | 5,469 |
| `AI构图-提示词模板.md` | 4,628 |

---

## 🚪 v0.5：`read` —— 最薄的 hook（读前自动量）

```bash
python tokenguard.py read 大文件.md                 # 超预算 → 只给前 25 行 + 指路
python tokenguard.py read 大文件.md --grep "关键词"   # 只给命中行
python tokenguard.py read 大文件.md --range 120-180  # 只给这段
python tokenguard.py read 小文件.md                  # 小文件直接给
python tokenguard.py read 大文件.md --full           # 强制整读（会警告）
```

**这就是"hook 化"最薄的一层**：把"我该不该整读"从**人的自觉**变成**命令的默认行为**。

### 实测（我们自己的日志，31,453 token）

| 用法 | 放进上下文的 token | 省 |
|---|---|---|
| 整读 | 31,453 | 0 |
| **`read`（守门）** | **329** | **31,124** |
| `read --grep tokenguard` | 388 | 31,065 |
| `read --range 1-6` | 66 | 5,679 |

**它不聪明，但它不让你犯错。**
