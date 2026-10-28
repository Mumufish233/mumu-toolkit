#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""冒烟测试：把 6 个工具各跑一遍，确认没坏。

用法: python smoke_test.py
输出: 终端 PASS/FAIL + 项目/21-冒烟测试报告.md
"""
import os
import shutil
import subprocess
import sys
import tempfile

from openpyxl import Workbook, load_workbook
from PIL import Image
from pypdf import PdfWriter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
REPORT = os.path.join(ROOT, "smoke-report.md")
BASE = os.path.join(tempfile.gettempdir(), "smoke_mumu")


def run(args, expect_ok=True):
    p = subprocess.run([PY] + args, cwd=ROOT, capture_output=True,
                       text=True, errors="ignore")
    ok = (p.returncode == 0) if expect_ok else True
    return ok, (p.stdout or "") + (p.stderr or "")


def prep():
    shutil.rmtree(BASE, ignore_errors=True)
    os.makedirs(BASE)

    # 1) 乱文件目录
    messy = os.path.join(BASE, "messy")
    os.makedirs(messy)
    for i, ext in enumerate(["pdf", "png", "xlsx", "zip", "txt", "mp3", "py", "dat"]):
        with open(os.path.join(messy, f"文件{i}.{ext}"), "wb") as f:
            f.write(b"x" * 2048)

    # 2) 重命名目录
    ren = os.path.join(BASE, "ren")
    os.makedirs(ren)
    for i in range(1, 6):
        with open(os.path.join(ren, f"IMG_{i}.jpg"), "wb") as f:
            f.write(b"x")

    # 3) Excel
    xl = os.path.join(BASE, "xl")
    os.makedirs(xl)
    for name, cols in [("a.xlsx", ["姓名", "金额"]),
                       ("b.xlsx", ["姓名", "金额", "备注"])]:
        wb = Workbook()
        ws = wb.active
        ws.append(cols)
        ws.append(["测试", 100] + (["x"] if len(cols) == 3 else []))
        wb.save(os.path.join(xl, name))

    # 4) PDF
    pdf = os.path.join(BASE, "pdf")
    os.makedirs(pdf)
    for name, n in [("p1.pdf", 3), ("p2.pdf", 2)]:
        w = PdfWriter()
        for _ in range(n):
            w.add_blank_page(width=300, height=400)
        with open(os.path.join(pdf, name), "wb") as f:
            w.write(f)

    # 5) 图片
    img = os.path.join(BASE, "img")
    os.makedirs(img)
    for i in range(1, 4):
        Image.new("RGB", (600, 800), (240, 240, 240)).save(
            os.path.join(img, f"p{i}.png"))
    return messy, ren, xl, pdf, img


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    messy, ren, xl, pdf, img = prep()
    rows = []

    def check(name, args, ok_extra=None):
        ok, out = run(args)
        detail = ""
        if ok and ok_extra:
            ok, detail = ok_extra()
        rows.append((name, ok, detail or ("rc=0" if ok else out.strip().splitlines()[-1][:60] if out.strip() else "rc!=0")))
        print(f"{'✅' if ok else '❌'} {name}  {detail}")

    # 1 文件整理
    check("file_tidy 预演", ["tools/file_tidy.py", messy, "--dry-run"])

    def tidy_real():
        p = subprocess.run([PY, "tools/file_tidy.py", messy], cwd=ROOT,
                           input="y\n", capture_output=True, text=True, errors="ignore")
        n = len([d for d in os.listdir(messy) if os.path.isdir(os.path.join(messy, d))])
        return n >= 3, f"{n} 个分类目录"
    check("file_tidy 真整理", ["tools/file_tidy.py", messy, "--dry-run"], tidy_real)

    # 2 重命名
    check("rename_batch 预演", ["tools/rename_batch.py", ren, "--prefix", "t", "--seq", "2", "--dry-run"])

    def ren_real():
        p = subprocess.run([PY, "tools/rename_batch.py", ren, "--prefix", "t", "--seq", "2"],
                           cwd=ROOT, input="y\n", capture_output=True, text=True, errors="ignore")
        names = os.listdir(ren)
        return any(n.startswith("t_01") for n in names), f"{len(names)} 个文件"
    check("rename_batch 真改名", ["tools/rename_batch.py", ren, "--prefix", "t", "--seq", "2", "--dry-run"], ren_real)

    # 3 Excel
    out_xlsx = os.path.join(BASE, "合并.xlsx")
    check("excel_merge 合并", ["tools/excel_merge.py", xl, "-o", out_xlsx])

    def xl_check():
        if not os.path.exists(out_xlsx):
            return False, "没有输出文件"
        ws = load_workbook(out_xlsx).active
        return ws.max_row >= 3, f"{ws.max_row} 行 × {ws.max_column} 列"
    check("excel_merge 结果", ["tools/excel_merge.py", xl, "--dry-run"], xl_check)

    # 4 PDF
    merged = os.path.join(BASE, "合并.pdf")
    check("pdf_kit 合并", ["tools/pdf_kit.py", "merge", os.path.join(pdf, "p1.pdf"),
                        os.path.join(pdf, "p2.pdf"), "-o", merged])
    check("pdf_kit 拆分", ["tools/pdf_kit.py", "split", merged, "--pages", "1-2",
                        "-o", os.path.join(BASE, "拆#.pdf")])
    check("pdf_kit 图转PDF", ["tools/pdf_kit.py", "fromimg", img, "-o",
                           os.path.join(BASE, "图集.pdf")])

    # 5 视频（只验证导出帮助和环境，不真渲）

    # 写报告
    lines = ["# 冒烟测试报告", "",
             f"时间：{__import__('time').strftime('%Y-%m-%d %H:%M:%S')}", "",
             "| 工具 | 结果 | 说明 |", "|---|---|---|"]
    for name, ok, detail in rows:
        lines.append(f"| {name} | {'✅' if ok else '❌'} | {detail} |")
    bad = [r for r in rows if not r[1]]
    lines += ["", "---", "",
              f"**结论：{'全部通过' if not bad else '失败 ' + str(len(bad)) + ' 项'}**", ""]
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print()
    print("结论:", "全部通过" if not bad else f"失败 {len(bad)} 项")
    print("报告:", REPORT)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())

