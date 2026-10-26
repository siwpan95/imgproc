# -*- coding: utf-8 -*-
"""imgproc · 无头自检（不启动 tkinter，不写入项目目录）。

验证 core.py 的图像加工链路：
1. 缩放（按宽度）、灰度化、缩略图白底画布、水印叠加、格式转换；
2. batch_process 的多操作串联、模板重命名、输出扩展名与临时文件清理。

全部素材与输出都在系统临时目录，使用后自动删除。
"""

from __future__ import annotations

import os
import sys
import tempfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from PIL import Image  # noqa: E402

import core            # noqa: E402


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def check_single_ops(tmp: str) -> None:
    src = os.path.join(tmp, "source.png")
    base = Image.new("RGB", (200, 100), (30, 120, 200))
    # 画一块对比色，确保后续水印差异检查有非单色底图
    for x in range(50, 150):
        for y in range(25, 75):
            base.putpixel((x, y), (220, 60, 40))
    base.save(src)

    resized = core.resize_image(src, os.path.join(tmp, "resized.png"), width=80)
    check(resized is not None, "按宽度缩放返回 None")
    with Image.open(resized) as im:
        check(im.size == (80, 40), f"按宽度缩放尺寸错误: {im.size}")

    scaled = core.resize_image(src, os.path.join(tmp, "scaled.png"), scale=0.5)
    with Image.open(scaled) as im:
        check(im.size == (100, 50), f"按百分比缩放尺寸错误: {im.size}")
    check(core.resize_image(src, os.path.join(tmp, "none.png")) is None,
          "既无宽度也无百分比时应返回 None")

    gray = core.to_grayscale(src, os.path.join(tmp, "gray.png"))
    with Image.open(gray) as im:
        check(im.mode == "L", f"灰度化输出 mode 错误: {im.mode}")

    thumb = core.make_thumbnail(src, os.path.join(tmp, "thumb.png"), side=64)
    with Image.open(thumb) as im:
        check(im.size == (64, 64), f"缩略图画布尺寸错误: {im.size}")
        check(im.mode == "RGB", f"缩略图画布 mode 错误: {im.mode}")
        check(im.getpixel((0, 0)) == (255, 255, 255), "缩略图白底填充错误")

    watermark = core.add_text_watermark(
        src, os.path.join(tmp, "watermark.png"), "自检",
        pos="cc", opacity=0.5, size=20)
    with Image.open(watermark) as im:
        check(im.size == (200, 100), "水印改变了图像尺寸")
        check(im.convert("RGB").tobytes() != base.tobytes(), "水印未产生像素变化")
    check(core.add_text_watermark(src, os.path.join(tmp, "empty.png"), "") is None,
          "空水印文字应返回 None")

    converted = core.convert_format(src, os.path.join(tmp, "converted.jpg"),
                                    fmt="jpg", quality=80)
    with Image.open(converted) as im:
        check(im.format == "JPEG", f"格式转换结果错误: {im.format}")
        check(im.mode == "RGB", f"JPG 输出 mode 错误: {im.mode}")


def check_batch(tmp: str) -> None:
    src = os.path.join(tmp, "batch_source.png")
    Image.new("RGB", (120, 80), (50, 160, 90)).save(src)
    out_dir = os.path.join(tmp, "batch_out")

    ops = {
        "resize": {"width": 60},
        "grayscale": True,
        "watermark": {"text": "自检", "pos": "rb", "opacity": 0.4, "size": 12},
        "thumbnail": {"side": 32},
        "convert": {"fmt": "jpg", "quality": 80},
        "rename": {"template": "{name}_{i}"},
    }
    results = core.batch_process([src], ops, out_dir)
    check(len(results) == 1, f"batch_process 返回条数错误: {len(results)}")
    _source, dst, ok, msg = results[0]
    check(ok is True, f"batch_process 失败: {msg}")
    check(dst == os.path.join(out_dir, "batch_source_0.jpg"),
          f"模板重命名/扩展名错误: {dst!r}")
    with Image.open(dst) as im:
        check(im.size == (32, 32), f"串联后最终尺寸错误: {im.size}")
        check(im.format == "JPEG", f"串联后最终格式错误: {im.format}")
    leftovers = [name for name in os.listdir(out_dir) if name.startswith("._tmp_")]
    check(leftovers == [], f"临时文件未清理: {leftovers!r}")
    check(os.path.basename(src) == "batch_source.png"
          and os.path.exists(src), "原图被移动或删除")
    check("png" in core.SUPPORTED and "jpg" in core.SUPPORTED,
          "SUPPORTED 格式集合异常")


def main() -> int:
    try:
        with tempfile.TemporaryDirectory(prefix="imgproc_selfcheck_") as tmp:
            check_single_ops(tmp)
            check_batch(tmp)
        print(
            "selfcheck ok: 缩放(宽度/百分比)/灰度/白底缩略图/水印/转 JPG 全部生效；"
            "batch_process 六操作串联、{name}_{i} 重命名、PNG→JPG 输出与临时文件清理正确"
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
