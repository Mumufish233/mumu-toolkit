#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Excel 批量合并：把同一目录下多个 .xlsx 按表头合并成一个总表。

用法:
  python excel_merge.py <目录> --dry-run          # 预览：读到了哪些表、多少行
  python excel_merge.py <目录> -o 合并结果.xlsx    # 真合并
  python excel_merge.py <目录> --sheet 2          # 只取每个文件的第 2 个 sheet

特性:
  - 自动识别表头行（默认第 1 行，可 --header-row 指定）
  - 表头不完全一致的列会自动并集，缺的列留空
  - 生成「来源文件」「来源表」两列，方便追溯
  - 不修改任何原文件
"""
import argparse
import os
import sys

try:
    from openpyxl import Workbook, load_workbook
except ImportError:
    print("需要 openpyxl：pip install openpyxl")
    raise SystemExit(1)


def list_xlsx(root):
    out = []
    for name in sorted(os.listdir(root)):
        if name.lower().endswith(".xlsx") and not name.startswith("~$"):
            out.append(os.path.join(root, name))
    return out


def read_sheet(path, sheet_sel, header_row):
    wb = load_workbook(path, data_only=True)
    sheets = wb.worksheets
    if isinstance(sheet_sel, int):
        ws = sheets[sheet_sel - 1] if 0 < sheet_sel <= len(sheets) else sheets[0]
    else:
        ws = sheets[0]
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return ws.title, [], []
    header = [str(c) if c is not None else "" for c in rows[header_row - 1]]
    body = rows[header_row:]
    body = [r for r in body if any(c is not None and str(c).strip() != "" for c in r)]
    return ws.title, header, body


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Excel 批量合并")
    ap.add_argument("root")
    ap.add_argument("-o", "--out", default="合并结果.xlsx")
    ap.add_argument("--sheet", type=int, default=1, help="取第几个 sheet（默认 1）")
    ap.add_argument("--header-row", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print("目录不存在：", root)
        return 1

    files = list_xlsx(root)
    if not files:
        print("目录里没有 .xlsx 文件。")
        return 1

    previews, all_cols, total_rows = [], [], 0
    for f in files:
        try:
            title, header, body = read_sheet(f, args.sheet, args.header_row)
        except Exception as e:
            print(f"  跳过 {os.path.basename(f)}：{e}")
            continue
        previews.append((os.path.basename(f), title, header, body))
        total_rows += len(body)
        for h in header:
            if h and h not in all_cols:
                all_cols.append(h)

    print(f"找到 {len(previews)} 个表，共 {total_rows} 行，{len(all_cols)} 个不同列名")
    for name, title, header, body in previews:
        print(f"  {name} [{title}]  {len(body)} 行  {len(header)} 列")

    if args.dry_run:
        print("\n（预演：没有写出任何文件）")
        print("列名并集：", " / ".join(all_cols[:12]), "…" if len(all_cols) > 12 else "")
        return 0

    wb = Workbook()
    ws = wb.active
    ws.title = "合并结果"
    head = ["来源文件", "来源表"] + all_cols
    ws.append(head)
    for name, title, header, body in previews:
        idx = {h: i for i, h in enumerate(header) if h}
        for row in body:
            rec = [""] * len(all_cols)
            for h, i in idx.items():
                if i < len(row):
                    rec[all_cols.index(h)] = row[i]
            ws.append([name, title] + rec)

    # 简单列宽
    for i, h in enumerate(head, 1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = max(10, min(28, len(str(h)) + 6))

    out = args.out if os.path.isabs(args.out) else os.path.join(os.path.dirname(root), args.out)
    wb.save(out)
    print(f"\n已写出：{out}")
    print(f"总行数：{total_rows}（不含表头）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
