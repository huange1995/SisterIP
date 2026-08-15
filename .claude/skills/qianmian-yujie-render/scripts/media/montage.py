# -*- coding: utf-8 -*-
"""图集 → 9:16 动态视频（多镜头路线 C，纯本地、零成本、确定性）。

从旧 commands/montage.py 迁移并升级：
- 每图独立时长（per / 或逐图 per 列表）
- cuts: dissolve 交叉淡入淡出 ｜ hard 硬切
- cam : zoom-in / zoom-out / pan / alternate（相邻图交替推近拉远）
- text: 每图可选字幕字卡（PIL 烧进帧，不依赖 ffmpeg libass）

对外只暴露 render_slideshow()；命令层（montage / compose）调用它。
"""

from __future__ import annotations

from collections import deque
from pathlib import Path

from config import Config
from pipeline import read_image

# 相机运动：zoom-in / zoom-out / pan / alternate（按图序交替推近/拉远）
CAM_MODES = ("zoom-in", "zoom-out", "pan", "alternate")
CUT_MODES = ("dissolve", "hard")


def _window(img, w: int, h: int) -> tuple[int, int, int, int]:
    """源图内取目标比例 (w:h) 的中心窗口 (x, y, cw, ch)。"""
    H, W = img.shape[:2]
    r = w / h
    if W / H > r:
        cw, ch = int(H * r), H
    else:
        cw, ch = W, int(W / r)
    return max(0, (W - cw) // 2), max(0, (H - ch) // 2), cw, ch


def _zoom_frame(img, win, scale: float, w: int, h: int):
    """Ken Burns：在窗口内取更小裁窗并缩放到目标尺寸。scale>1 推近，<1 拉远。"""
    import cv2

    x, y, cw, ch = win
    s = max(0.05, 1.0 / scale)
    ow, oh = max(1, int(cw * s)), max(1, int(ch * s))
    cx, cy = x + cw / 2, y + ch / 2
    x0 = min(max(0, int(cx - ow / 2)), img.shape[1] - ow)
    y0 = min(max(0, int(cy - oh / 2)), img.shape[0] - oh)
    crop = img[y0:y0 + oh, x0:x0 + ow]
    return cv2.resize(crop, (w, h), interpolation=cv2.INTER_AREA)


def _pan_frame(img, win, scale: float, t: float, w: int, h: int):
    """横移机位：窗口内从一端平移到另一端。t∈[0,1]。"""
    import cv2

    x, y, cw, ch = win
    s = max(0.05, 1.0 / scale)
    ow, oh = max(1, int(cw * s)), max(1, int(ch * s))
    if ow < cw:  # 横向有平移空间
        x0 = int(x + (cw - ow) * t)
        y0 = int(y + (ch - oh) / 2)
    else:  # 纵向平移（极少见）
        x0 = int(x + (cw - ow) / 2)
        y0 = int(y + (ch - oh) * t)
    crop = img[y0:y0 + oh, x0:x0 + ow]
    return cv2.resize(crop, (w, h), interpolation=cv2.INTER_AREA)


def _bake_text(cfg, frame, text: str, w: int, h: int):
    """把字幕字卡烧进单帧（PIL 字卡合成到 BGR 帧）。Pillow 缺失时明确报错。"""
    from media import subtitle

    max_w = int(w * cfg.subtitle_max_width_ratio)
    card = subtitle.text_card(text, cfg, max_w=max_w)
    return subtitle.overlay_on_frame(frame, card, cfg, frame_w=w, frame_h=h)


def render_slideshow(cfg: Config, image_paths: list[Path], out_path: Path, *,
                     per: float, size: tuple[int, int], fps: int,
                     cuts: str = "dissolve", cam: str = "alternate",
                     texts: list[str | None] | None = None,
                     fade: float | None = None) -> Path:
    """把图集按序合成 9:16 视频。

    - per   ：每张停留秒数
    - size  ：(w, h) 画幅（1080, 1920）
    - cuts  ：dissolve 交叉淡入淡出（默认）| hard 硬切
    - cam   ：相机运动（见 CAM_MODES）
    - texts ：与图一一对应的字卡文案（None → 该图无字卡）
    - fade  ：淡入淡出秒数（默认取 cfg.montage_fade）
    """
    import cv2

    w, h = size
    fade_frames = max(1, int((fade if fade is not None else cfg.montage_fade) * fps))
    zoom = cfg.montage_zoom
    dissolve = cuts == "dissolve"

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (w, h))
    prev_tail = deque(maxlen=fade_frames) if dissolve else None
    try:
        for idx, p in enumerate(image_paths):
            img = read_image(p)
            win = _window(img, w, h)
            n_frames = max(int(per * fps), 1)
            zoom_in = cam == "zoom-in" or (cam == "alternate" and idx % 2 == 0)
            tail = deque(maxlen=fade_frames) if dissolve else None
            text = texts[idx] if texts and idx < len(texts) else None
            for f in range(n_frames):
                t = f / max(n_frames - 1, 1)
                if cam == "pan":
                    scale = 1.0 + zoom / 2
                    frame = _pan_frame(img, win, scale, t, w, h)
                else:
                    scale = 1.0 + zoom * (t if zoom_in else (1 - t))
                    frame = _zoom_frame(img, win, scale, w, h)
                if dissolve and prev_tail and f < fade_frames:
                    prev = prev_tail[f] if f < len(prev_tail) else prev_tail[-1]
                    alpha = (f + 1) / fade_frames
                    frame = cv2.addWeighted(prev, 1 - alpha, frame, alpha, 0)
                if text:
                    frame = _bake_text(cfg, frame, text, w, h)
                writer.write(frame)
                if tail is not None:
                    tail.append(frame)
            prev_tail = tail
    finally:
        writer.release()
    return out_path
