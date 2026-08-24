"""imgproc 核心逻辑：批量图像加工纯函数（依赖 Pillow）。

所有函数接收源路径、目标路径，出错时返回 None 或在 batch_process 中记录 msg，
不抛未捕获异常导致 GUI 崩溃。
"""
from __future__ import annotations

import os
import sys
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

# 支持的输入/输出格式
SUPPORTED = {"png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff"}
_FMT_EXT = {"jpg": "jpg", "jpeg": "jpg", "png": "png", "webp": "webp",
            "bmp": "bmp", "gif": "gif", "tiff": "tiff"}


def _safe_font(size: int):
    """尽力拿到一个可用字体，失败则用默认位图字体。"""
    candidates = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def resize_image(src: str, dst: str, width: Optional[int] = None,
                 scale: Optional[float] = None) -> Optional[str]:
    """按目标宽度或百分比缩放。二者都给时 width 优先。"""
    if width is None and scale is None:
        return None
    with Image.open(src) as im:
        w, h = im.size
        if width:
            nw = int(width)
        else:
            nw = max(1, int(w * float(scale)))
        nh = max(1, int(h * nw / w))
        im = im.resize((nw, nh), Image.LANCZOS)
        im.save(dst)
    return dst


def convert_format(src: str, dst: str, fmt: str = "jpg", quality: int = 85) -> Optional[str]:
    """格式转换（png/jpg/webp 等）。jpg 走有损 quality。"""
    fmt = fmt.lower()
    if fmt not in _FMT_EXT:
        raise ValueError(f"不支持的格式: {fmt}")
    with Image.open(src) as im:
        if im.mode in ("RGBA", "P") and fmt in ("jpg", "jpeg", "bmp"):
            im = im.convert("RGB")
        save_kwargs = {}
        if fmt in ("jpg", "jpeg"):
            save_kwargs["quality"] = int(quality)
        elif fmt == "webp":
            save_kwargs["quality"] = int(quality)
        im.save(dst, **save_kwargs)
    return dst


def to_grayscale(src: str, dst: str) -> Optional[str]:
    with Image.open(src) as im:
        im = im.convert("L")
        im.save(dst)
    return dst


def make_thumbnail(src: str, dst: str, side: int = 256) -> Optional[str]:
    """生成边长 side 的缩略图（保持比例，居中）。"""
    with Image.open(src) as im:
        im.thumbnail((side, side), Image.LANCZOS)
        # 居中贴到 side x side 画布
        canvas = Image.new("RGB", (side, side), (255, 255, 255))
        canvas.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
        canvas.save(dst)
    return dst


def add_text_watermark(src: str, dst: str, text: str, pos: str = "rb",
                       opacity: float = 0.3, size: int = 24) -> Optional[str]:
    """在图上叠加半透明文字水印。

    pos: lt/rt/lb/rb/cc（左上/右上/左下/右下/居中）
    opacity: 0~1 透明度
    """
    if not text:
        return None
    with Image.open(src) as im:
        base = im.convert("RGBA")
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        font = _safe_font(size)
        if font:
            bbox = font.getbbox(text)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        else:
            tw, th = len(text) * size // 2, size
        m = 12
        w, h = base.size
        pos_map = {
            "lt": (m, m), "rt": (w - tw - m, m),
            "lb": (m, h - th - m), "rb": (w - tw - m, h - th - m),
            "cc": ((w - tw) // 2, (h - th) // 2),
        }
        xy = pos_map.get(pos, pos_map["rb"])
        alpha = int(255 * max(0.0, min(1.0, opacity)))
        draw.text(xy, text, font=font, fill=(255, 255, 255, alpha))
        out = Image.alpha_composite(base, overlay).convert("RGB")
        out.save(dst)
    return dst


def batch_process(paths: list[str], ops: dict, out_dir: Optional[str] = None
                  ) -> list[tuple[str, Optional[str], bool, str]]:
    """对一批图片执行勾选的操作组合。

    ops 例：
    {
      'resize': {'width': 800},
      'convert': {'fmt': 'jpg', 'quality': 85},
      'watermark': {'text': '全哥', 'pos': 'rb', 'opacity': 0.3, 'size': 24},
      'grayscale': True,
      'thumbnail': {'side': 256},
      'rename': {'template': '{name}_{i}'},
    }
    只处理 ops 中存在的键。返回 [(src, dst, ok, msg), ...]
    """
    if not paths:
        return []
    if out_dir is None:
        out_dir = os.path.join(os.path.dirname(paths[0]), "imgproc_out")
    os.makedirs(out_dir, exist_ok=True)

    results = []
    for i, src in enumerate(paths):
        try:
            stem, ext = os.path.splitext(os.path.basename(src))
            ext = ext.lower().lstrip(".")
            cur = src
            tmp_files = []

            # 重命名模板
            tpl = ops.get("rename", {}).get("template") if isinstance(ops.get("rename"), dict) else None
            if tpl:
                new_stem = (tpl.replace("{name}", stem)
                                .replace("{i}", str(i))
                                .replace("{ext}", ext))
            else:
                new_stem = stem

            # 格式转换决定最终扩展名
            fmt = None
            if ops.get("convert"):
                fmt = ops["convert"].get("fmt", "jpg").lower()
            out_ext = _FMT_EXT.get(fmt, ext if ext in _FMT_EXT else "png")

            # 逐步处理（用临时文件串联，最后落到 out_dir）
            step_paths = [src]
            # 1) resize
            if ops.get("resize"):
                r = ops["resize"]
                d = os.path.join(out_dir, f"._tmp_{i}_resize.png")
                resize_image(cur, d, r.get("width"), r.get("scale"))
                cur, step_paths = d, step_paths + [d]
            # 2) grayscale
            if ops.get("grayscale"):
                d = os.path.join(out_dir, f"._tmp_{i}_gray.png")
                to_grayscale(cur, d)
                cur, step_paths = d, step_paths + [d]
            # 3) watermark
            if ops.get("watermark") and ops["watermark"].get("text"):
                d = os.path.join(out_dir, f"._tmp_{i}_wm.png")
                add_text_watermark(cur, d, **{k: v for k, v in ops["watermark"].items()})
                cur, step_paths = d, step_paths + [d]
            # 4) thumbnail（应用到主流程：缩到指定边长，作为最终输出）
            if ops.get("thumbnail"):
                side = ops["thumbnail"].get("side", 256)
                d = os.path.join(out_dir, f"._tmp_{i}_thumb.png")
                make_thumbnail(cur, d, side)
                cur = d
                step_paths.append(d)
            # 最终转换/落盘
            final = os.path.join(out_dir, f"{new_stem}.{out_ext}")
            if fmt and fmt != ext:
                convert_format(cur, final, fmt, ops["convert"].get("quality", 85))
            else:
                # 同格式直接保存（避免丢失）
                with Image.open(cur) as im:
                    im.save(final)

            # 清临时
            for t in step_paths[1:]:
                try:
                    os.remove(t)
                except OSError:
                    pass
            results.append((src, final, True, "ok"))
        except Exception as e:
            results.append((src, None, False, f"{type(e).__name__}: {e}"))
    return results


if __name__ == "__main__":
    print("imgproc core loaded; Pillow", getattr(sys.modules.get("PIL"), "__version__", "?") if False else "ok")
