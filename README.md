# mumu-toolkit

> Small, dependency-light Windows automation tools that **preview before they touch anything**, and **can always be undone**.
>
> 一组小而干脆的 Windows 自动化小工具。**先预演，再动手；做了就能撤回。**

[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](#license)

---

## Why this exists / 为什么造它

Most "clean up my folder" scripts are all-or-nothing: you run them, and if they guess wrong, you spend an hour undoing it.

These tools take the opposite stance:

- **Dry-run first.** `--dry-run` prints exactly what would change and writes nothing.
- **Undo always.** Every run writes a JSON undo log; one flag reverses it.
- **Never delete.** Files are moved, never removed. Name collisions get a `_1` suffix.

> 大多数"整理文件夹"的脚本都是一次性梭哈。这几个工具反过来：
> **先预演、可撤销、绝不删除。**

---

## The tools / 工具

| Tool | What it does | 实测 |
|---|---|---|
| [`file_tidy.py`](tools/file_tidy.py) | Sort files into type folders | 64 files in **0.4s**, undo in **0.2s** |
| [`rename_batch.py`](tools/rename_batch.py) | Prefix / sequence / date / regex rename | `第01集 → EP01`, full undo |
| [`excel_merge.py`](tools/excel_merge.py) | Merge many `.xlsx` into one | column union, order-independent mapping |
| [`pdf_kit.py`](tools/pdf_kit.py) | Merge / split / extract text / images→PDF | 13-page merge, 2880 chars extracted |

---

## Quick start / 上手

```bash
pip install openpyxl pypdf pillow   # only needed for excel_merge / pdf_kit

# 1) See what would happen (nothing is touched)
python tools/file_tidy.py "D:\Downloads" --dry-run

# 2) Do it
python tools/file_tidy.py "D:\Downloads"

# 3) Changed your mind
python tools/file_tidy.py "D:\Downloads" --undo "tidy-log-20261028-135820.json"
```

### Batch rename

```bash
python tools/rename_batch.py "D:\photos" --prefix trip --seq 3 --dry-run
python tools/rename_batch.py "D:\episodes" --regex "第(\d+)集" --replace "EP\1"
```

### Merge spreadsheets

```bash
python tools/excel_merge.py "D:\reports" -o merged.xlsx
```

Handles differing columns (union) and differing column **order**. Adds `_source_file` / `_source_sheet` columns for traceability.

### PDF toolbox

```bash
python tools/pdf_kit.py merge a.pdf b.pdf -o out.pdf
python tools/pdf_kit.py split big.pdf --pages 1-3,7,10-13 -o part#.pdf
python tools/pdf_kit.py text a.pdf -o text.txt
python tools/pdf_kit.py fromimg "D:\photos" -o album.pdf
```

> Scanned PDFs (image-only) yield no text — `text` warns you instead of pretending it worked.

---

## Tests / 自测

```bash
python tests/smoke_test.py
```

Creates a throwaway folder, exercises every tool end to end, prints PASS/FAIL, exits non-zero on failure.

```
✅ file_tidy 预演
✅ file_tidy 真整理  7 个分类目录
✅ rename_batch 真改名  5 个文件
✅ excel_merge 结果  3 行 × 5 列
✅ pdf_kit 合并
✅ pdf_kit 拆分
✅ pdf_kit 图转PDF
结论: 全部通过
```

---

## Design notes / 设计取舍

- **Standard library only** where possible; the two Excel/PDF tools need `openpyxl` / `pypdf` / `pillow`.
- **No GUI, no service, no telemetry.** CLI scripts you can read in five minutes.
- **Undo logs are plain JSON** — diffable, greppable, portable.
- **Scanned PDFs are called out, not silently mis-handled.**

---

## License

MIT
