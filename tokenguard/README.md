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
