"""imgproc 批量图像加工 —— Tkinter GUI（中文界面）。

运行：python main.py
依赖：Pillow（pip install Pillow）
注意：无显示器环境不要直接运行本文件（会实例化 Tk）。
"""
from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from core import (SUPPORTED, batch_process, resize_image, convert_format,
                  to_grayscale, make_thumbnail, add_text_watermark)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("imgproc 批量图像加工")
        self.geometry("720x600")
        self.folder = tk.StringVar()
        self._build()

    def _build(self):
        frm = ttk.Frame(self, padding=10)
        frm.pack(fill="both", expand=True)

        # 文件夹选择
        row = ttk.Frame(frm)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="输入文件夹：").pack(side="left")
        ttk.Entry(row, textvariable=self.folder, width=50).pack(side="left", padx=4)
        ttk.Button(row, text="浏览…", command=self._pick).pack(side="left")

        # 操作勾选区
        ops = ttk.LabelFrame(frm, text="批量操作（可多选）", padding=8)
        ops.pack(fill="x", pady=6)

        self.c_resize = tk.BooleanVar()
        self.c_convert = tk.BooleanVar()
        self.c_wm = tk.BooleanVar()
        self.c_gray = tk.BooleanVar()
        self.c_thumb = tk.BooleanVar()
        self.c_rename = tk.BooleanVar()

        ttk.Checkbutton(ops, text="缩放(宽/百分比)", variable=self.c_resize).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(ops, text="灰度化", variable=self.c_gray).grid(row=0, column=1, sticky="w")
        ttk.Checkbutton(ops, text="文字水印", variable=self.c_wm).grid(row=0, column=2, sticky="w")
        ttk.Checkbutton(ops, text="格式转换", variable=self.c_convert).grid(row=1, column=0, sticky="w")
        ttk.Checkbutton(ops, text="缩略图", variable=self.c_thumb).grid(row=1, column=1, sticky="w")
        ttk.Checkbutton(ops, text="模板重命名", variable=self.c_rename).grid(row=1, column=2, sticky="w")

        # 参数区
        p = ttk.LabelFrame(frm, text="参数", padding=8)
        p.pack(fill="x", pady=6)

        def add_param(parent, r, c, label, var, w=14):
            ttk.Label(parent, text=label).grid(row=r, column=c, sticky="w", padx=2)
            ttk.Entry(parent, textvariable=var, width=w).grid(row=r, column=c + 1, padx=2)

        self.p_rw = tk.StringVar()      # 缩放宽度
        self.p_rp = tk.StringVar()      # 缩放百分比
        self.p_fmt = tk.StringVar(value="jpg")
        self.p_q = tk.StringVar(value="85")
        self.p_wmt = tk.StringVar(value="全哥")
        self.p_wmp = tk.StringVar(value="rb")
        self.p_wmo = tk.StringVar(value="0.3")
        self.p_wms = tk.StringVar(value="24")
        self.p_ts = tk.StringVar(value="256")
        self.p_rt = tk.StringVar(value="{name}_{i}")

        add_param(p, 0, 0, "缩放宽度(px):", self.p_rw)
        add_param(p, 0, 2, "缩放百分比:", self.p_rp)
        add_param(p, 1, 0, "转换格式:", self.p_fmt)
        add_param(p, 1, 2, "质量(1-100):", self.p_q)
        add_param(p, 2, 0, "水印文字:", self.p_wmt)
        add_param(p, 2, 2, "水印位置:", self.p_wmp)
        add_param(p, 3, 0, "水印透明度:", self.p_wmo)
        add_param(p, 3, 2, "水印字号:", self.p_wms)
        add_param(p, 4, 0, "缩略图边长:", self.p_ts)
        add_param(p, 4, 2, "重命名模板:", self.p_rt)
        ttk.Label(p, text="位置: lt/rt/lb/rb/cc；模板: {name}{i}{ext}").grid(row=5, column=0, columnspan=4, sticky="w")

        # 进度 + 日志
        self.prog = ttk.Progressbar(frm, mode="determinate")
        self.prog.pack(fill="x", pady=6)
        self.log = scrolledtext.ScrolledText(frm, height=12, state="disabled")
        self.log.pack(fill="both", expand=True, pady=4)

        ttk.Button(frm, text="开始处理", command=self._run).pack(pady=6)

    def _pick(self):
        d = filedialog.askdirectory(title="选择输入文件夹")
        if d:
            self.folder.set(d)

    def _log(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _collect_ops(self) -> dict:
        ops: dict = {}
        if self.c_resize.get():
            rw = self.p_rw.get().strip()
            rp = self.p_rp.get().strip()
            d = {}
            if rw:
                d["width"] = int(rw)
            elif rp:
                d["scale"] = float(rp) / 100.0
            if d:
                ops["resize"] = d
        if self.c_convert.get():
            ops["convert"] = {"fmt": self.p_fmt.get().strip().lower(),
                              "quality": int(self.p_q.get() or 85)}
        if self.c_wm.get():
            ops["watermark"] = {"text": self.p_wmt.get(),
                                "pos": self.p_wmp.get().strip() or "rb",
                                "opacity": float(self.p_wmo.get() or 0.3),
                                "size": int(self.p_wms.get() or 24)}
        if self.c_gray.get():
            ops["grayscale"] = True
        if self.c_thumb.get():
            ops["thumbnail"] = {"side": int(self.p_ts.get() or 256)}
        if self.c_rename.get():
            ops["rename"] = {"template": self.p_rt.get()}
        return ops

    def _run(self):
        folder = self.folder.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("错误", "请先选择有效的输入文件夹")
            return
        ops = self._collect_ops()
        if not ops:
            messagebox.showwarning("提示", "请至少勾选一个操作")
            return

        files = [os.path.join(folder, f) for f in os.listdir(folder)
                 if os.path.isfile(os.path.join(folder, f))
                 and os.path.splitext(f)[1].lower().lstrip(".") in SUPPORTED]
        if not files:
            messagebox.showinfo("无文件", "文件夹中没有受支持的图像文件")
            return

        self._log(f"找到 {len(files)} 个图像，开始处理…")
        self.prog["maximum"] = len(files)
        self.prog["value"] = 0
        out_dir = os.path.join(folder, "imgproc_out")
        results = batch_process(files, ops, out_dir)
        ok = 0
        for src, dst, success, msg in results:
            self.prog["value"] += 1
            if success:
                ok += 1
                self._log(f"✓ {os.path.basename(src)} -> {os.path.basename(dst)}")
            else:
                self._log(f"✗ {os.path.basename(src)} 失败: {msg}")
        self._log(f"完成：成功 {ok}/{len(files)}，输出目录 {out_dir}")


if __name__ == "__main__":
    App().mainloop()
