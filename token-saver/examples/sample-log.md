## 2026-10-01 10:00（旧月份示例）

- 这条会被归档到 `log-archive/2026-10.md`

## 2026-11-01 10:00（本月示例）

- 这条会留在主日志里
- 运行 `python tools/log_rotate.py --log examples/sample-log.md --archive examples/arch` 看预览

## 2026-11-02 11:00

- `--apply` 才会真的切，切之前自动备份 `.bak-*`
