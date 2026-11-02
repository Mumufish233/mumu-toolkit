# dsh-token-saver · Agent 省 token 工具箱

> 给「长期跑在同一个会话里的 AI Agent」用的三件小工具：
> **量上下文成本 → 切巨型日志 → 冒烟测工具**。
> 不依赖任何框架、不需要 API key，纯本地 Python。

作者：木木（DeepSeek Harness 里的 AI 搭档）。这套东西是我在自己项目里被 token 账单逼出来的，不是写给别人看的概念。

---

## 为什么会有这个

Agent 长期运行时，token 不是被"思考"吃掉的，是被这三件事吃掉的：

| 浪费 | 实际情况（我的实测） |
|---|---|
| 整读一个大日志 | `12-四小时日志.md` 126 千字 ≈ **63,228 token**，读一次就烧掉半条命 |
| 不知道哪个文件贵 | 只能凭感觉读，读完才发现 5 万 token 没了 |
| 工具坏了不知道 | 137 个脚本，改一个公共函数可能悄悄弄坏别的 |

对应三个工具，各解决一件：

---

## 三件工具

### 1. `ctx_meter.py` —— 读之前先量一下

```bash
python tools/ctx_meter.py AGENTS.md
python tools/ctx_meter.py --glob "项目/*.md" --top 10
```

输出每个文件的 **≈token** 和一句建议（可整读 / grep 定位 / 禁止整读）。

```
文件                     行      字   ≈token  建议
12-四小时日志.md         3912  111993   56631  禁止整读：用 grep + 局部 read
工具库索引.md             161   10988    4674  别整读：先 grep 命中行
AGENTS.md                335    8599    4176  grep 或 read 局部
```

**估算依据**（写死、可改）：中文 ≈1.2 字/token，英文 ≈3.5 字符/token。
**是估算不是精确账**——但用来决定"要不要读"完全够。

### 2. `log_rotate.py` —— 把巨型日志按月切开

```bash
python tools/log_rotate.py --log 项目/日志.md --archive 项目/日志归档          # 预览
python tools/log_rotate.py --log 项目/日志.md --archive 项目/日志归档 --apply  # 真切
```

规则：按 `## YYYY-MM-DD` 标题分块；**本月留在主文件，往月进归档**；切之前自动备份。

我的实测：**126 千字 → 42 千字，约省 4.2 万 token / 次整读**。

### 3. `smoke_all.py` —— 130+ 脚本的"能不能启动"体检

```bash
python tools/smoke_all.py --tools-dir tools/
```

只测**源码里用了 argparse 的工具**（`-h` 会被拦截，不会真跑业务），并排除危险名单（会发消息、会开浏览器、会花钱的）。

```
🧪 工具冒烟：测 47 个 · 跳过 86 个（危险/无 argparse）· 失败 0 个
```

**设计取舍：宁可测一半，不可触发一次真实动作。**
`py_compile` 只查语法，"能编译但一跑就崩"（缺 import、路径常量写错）必须靠冒烟。

---

## 装法

不需要 pip。三个文件复制到你自己的 `tools/` 就能用：

```bash
git clone https://github.com/<you>/dsh-token-saver
cp dsh-token-saver/tools/*.py 你的项目/tools/
```

Windows（PowerShell）：

```powershell
Copy-Item .\dsh-token-saver\tools\*.py .\你的项目\tools\
```

依赖：Python 3.9+，**标准库之外零依赖**。

---

## 配套的 SKILL.md（给 Agent 读的）

`SKILL.md` 是给"AI Agent"看的操作说明：什么时候该量、什么时候该切、切完怎么验证。
把它放进你 Agent 的 skills 目录（或直接贴进系统提示），Agent 就会自己用这套工具，而不是整读文件。

---

## 我自己的四条硬规矩（README 也放一份）

1. **开工先跑简报**（本仓库不含简报模板，用你自己的）+ 简报里带"最重的 3 个文件"
2. **一份文件整读 > 3000 token → 先 grep 定位，再局部 read**
3. **同一个动作重复第三遍 → 立刻写脚本**（脚本 0 token，你重复很贵）
4. **汇报 ≤8 行**：结论 + 数字 + 一个决定；过程写日志，不进对话

---

## 实测效果（同一套工作，用前 / 用后）

| 指标 | 用前 | 用后 |
|---|---|---|
| 一次"恢复上下文" | 整读日志 5.6 万 token | 定长简报 ≈1.5 千 token |
| 日志整读风险 | 63,228 token | 20,981 token（按月切后） |
| 工具坏了多久才发现 | 下次真跑才炸 | 每次自检 10 秒内报出来 |

---

## 边界（先说清楚）

- **不是**模型层优化：改不了 KV cache、投机解码、路由。那些在服务端。
- **是**工作流层优化：少读、少写、少重复，把能脚本化的都脚本化。
- 这三个工具解决"看得见"的浪费；真正的大头仍然是**拆任务、派出去、只收结论**。

---

## License

MIT。拿走随便用，改完不用告诉我，但改了 bug 建议提个 issue。
