"""imgproc 冒烟测试：用 tempfile 造图，验证核心纯函数与 batch_process。

运行：
    managed_python tests/smoke_test.py
退出码 0 表示全部通过，非 0 表示有失败。
"""

import os
import sys
import tempfile

# 让测试能导入项目根的 core 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core
from PIL import Image

FAILURES = []


def check(cond, name, extra=""):
    status = "OK " if cond else "FAIL"
    print(f"[{status}] {name} {extra}")
    if not cond:
        FAILURES.append(name)


def main():
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "sample.png")
        # 造一张 400x300 的彩色测试图
        Image.new("RGB", (400, 300), (120, 200, 80)).save(src)
        out = os.path.join(d, "out")
        os.makedirs(out, exist_ok=True)

        # 1) resize
        r = core.resize_image(src, os.path.join(out, "r.png"), width=200)
        with Image.open(r) as im:
            check(im.size[0] == 200 and im.size[1] == 150, "resize_image", f"-> {im.size}")

        # 2) convert -> jpg, 验证格式与质量
        c = core.convert_format(src, os.path.join(out, "c.jpg"), "jpg", quality=80)
        check(c.lower().endswith(".jpg"), "convert_format ext", f"-> {c}")
        with Image.open(c) as im:
            check(im.format == "JPEG", "convert_format fmt", f"-> {im.format}")

        # 3) grayscale
        g = core.to_grayscale(src, os.path.join(out, "g.png"))
        with Image.open(g) as im:
            check(im.mode == "L", "to_grayscale", f"-> {im.mode}")

        # 4) watermark
        w = core.add_text_watermark(src, os.path.join(out, "w.png"), "测试",
                                    pos="rb", opacity=0.4, size=28)
        check(os.path.exists(w) and os.path.getsize(w) > 0, "add_text_watermark", f"-> {w}")

        # 5) thumbnail
        t = core.make_thumbnail(src, os.path.join(out, "t.png"), side=128)
        with Image.open(t) as im:
            check(max(im.size) <= 128, "make_thumbnail", f"-> {im.size}")

        # 6) batch_process 组合
        res = core.batch_process([src], {
            "resize": {"width": 150},
            "watermark": {"text": "全哥", "pos": "rb", "opacity": 0.5, "size": 20},
            "grayscale": True,
            "thumbnail": {"side": 64},
            "convert": {"fmt": "webp", "quality": 90},
            "rename": {"template": "{name}_{i}"},
            "_out_dir": out,
        })
        check(len(res) == 1, "batch_process count", f"-> {len(res)}")
        src_out, dst_out, ok, msg = res[0]
        check(ok, "batch_process ok", f"-> {msg}")
        check(dst_out is not None and os.path.exists(dst_out), "batch_process dst", f"-> {dst_out}")
        if dst_out and os.path.exists(dst_out):
            with Image.open(dst_out) as im:
                check(im.format == "WEBP", "batch_process webp", f"-> {im.format}")
                check(max(im.size) <= 64, "batch_process thumb", f"-> {im.size}")

        # 7) 空输入友好处理：不存在的文件
        bad = core.batch_process(["__not_exist__.png"], {})
        check(len(bad) == 1 and bad[0][2] is False, "batch_process missing file friendly",
              f"-> {bad[0][3]}")

        # 8) 原图未被覆盖
        with Image.open(src) as im:
            check(im.size == (400, 300), "original untouched", f"-> {im.size}")

    print("\n结果：", "全部通过" if not FAILURES else f"失败 {len(FAILURES)} 项：{FAILURES}")
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()
