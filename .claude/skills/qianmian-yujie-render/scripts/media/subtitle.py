# -*- coding: utf-8 -*-
"""字幕字卡（自包含，可共享）：PIL + 微软雅黑 画半透明字卡，SRT 导出。

不依赖 ffmpeg libass：montage 帧在渲染时直接合成字卡；seedance 片用透明字卡 PNG
交给 engine.ffmpeg.overlay_card 盖。SRT 导出供剪映等精修。

Pillow 未装时绘制函数抛 ImportError，由调用方提示装依赖（pip install Pillow）。
"""

from __future__ import annotations

from pathlib import Path

from config import Config


def _resolve_font_path(cfg: Config) -> str | None:
    if cfg.subtitle_font and Path(cfg.subtitle_font).exists():
        return cfg.subtitle_font
    for cand in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/msyhbd.ttc"):
        if Path(cand).exists():
            return cand
    return None  # 回落 PIL 默认字体（无中文字形，仅兜底）


def _font(cfg: Config, px: int):
    from PIL import ImageFont

    p = _resolve_font_path(cfg)
    if p:
        return ImageFont.truetype(p, px)
    return ImageFont.load_default()


def _wrap_lines(text: str, font, max_w: int) -> list[str]:
    """按 max_w 逐字换行（中文为主，无空格分词）。"""
    from PIL import Image, ImageDraw

    probe = Image.new("RGBA", (10, 10))
    d = ImageDraw.Draw(probe)
    lines, cur = [], ""
    for ch in text:
        if d.textlength(cur + ch, font=font) <= max_w:
            cur += ch
        else:
            if cur:
                lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines or [text]


def text_card(text: str, cfg: Config, *, max_w: int) -> "Image.Image":
    """绘制字幕字卡（半透明圆角底 + 居中白字描边），返回 RGBA 图。

    max_w 为字卡最大宽度像素（画幅宽 × subtitle_max_width_ratio）。
    文本超宽自动逐字换行（中文为主）。
    """
    from PIL import Image, ImageDraw

    size = cfg.subtitle_size
    font = _font(cfg, size)
    lines = _wrap_lines(text, font, max_w - int(size * 0.8))
    line_h = int(size * 1.4)
    pad_x, pad_y = int(size * 0.5), int(size * 0.35)

    probe = Image.new("RGBA", (10, 10))
    d = ImageDraw.Draw(probe)
    tw = max(int(d.textlength(ln, font=font)) for ln in lines)
    card_w = min(max_w, tw + 2 * pad_x)
    card_h = line_h * len(lines) - int(size * 0.4) + 2 * pad_y

    card = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    dc = ImageDraw.Draw(card)
    alpha = int(255 * cfg.subtitle_bg_alpha)
    dc.rounded_rectangle([0, 0, card_w - 1, card_h - 1], radius=int(size * 0.3),
                         fill=(0, 0, 0, alpha))
    stroke = max(1, size // 24)
    for i, ln in enumerate(lines):
        lw = int(dc.textlength(ln, font=font))
        tx = (card_w - lw) // 2
        ty = pad_y + i * line_h
        dc.text((tx, ty), ln, font=font, fill=(255, 255, 255, 255),
                stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
    return card


def overlay_on_frame(frame, card, cfg: Config, *, frame_w: int, frame_h: int):
    """把 RGBA 字卡合成到 BGR 帧底部居中（只算字卡区域，快），返回新 BGR 帧。"""
    import numpy as np

    cw, ch = card.size
    x = max(0, (frame_w - cw) // 2)
    y = max(0, frame_h - ch - cfg.subtitle_bottom)
    card_bgr = np.asarray(card)[:, :, :3][..., ::-1].astype(np.float32)  # RGBA→BGR
    alpha = np.asarray(card)[:, :, 3:4].astype(np.float32) / 255.0
    roi = frame[y:y + ch, x:x + cw].astype(np.float32)
    frame[y:y + ch, x:x + cw] = (roi * (1 - alpha) + card_bgr * alpha).astype(np.uint8)
    return frame


def card_to_png(card, out_path: Path) -> Path:
    """RGBA 字卡 → 透明 PNG（seedance 片 overlay 用）。"""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    card.save(out_path)
    return out_path


def _srt_time(sec: float) -> str:
    sec = max(0.0, sec)
    ms = int(round(sec * 1000))
    h, rem = divmod(ms, 3600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def export_srt(cards: list[tuple[float, float, str]], out_path: Path) -> Path:
    """cards: [(开始秒, 结束秒, 文案)] → SRT 字幕文件（供剪映花字精修）。"""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for i, (s, e, t) in enumerate(cards, 1):
        lines += [str(i), f"{_srt_time(s)} --> {_srt_time(e)}", t, ""]
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path
