# -*- coding: utf-8 -*-
"""合成子命令：montage —— 图集 → 9:16 动态视频（零成本，零新模型）。

- 复用 opencv（已在依赖里，自带 mp4v 编码，无需装 ffmpeg）
- Ken Burns 缓慢推近/拉远（相邻图交替方向）+ 交叉淡入淡出
- 配乐 / 字幕 / 文案叠加建议到剪映等工具里做（脚本不处理音频）
"""

from __future__ import annotations

from collections import deque
from pathlib import Path

import archive
from pipeline import read_image

_IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def render_montage(cfg, image_paths: list[Path], out_path: Path,
                   per: float | None = None) -> None:
    """把图集按顺序合成 9:16 视频。per=每张停留秒数。"""
    import cv2

    fps = cfg.montage_fps
    per = per or cfg.montage_per_image
    fade_frames = max(1, int(cfg.montage_fade * fps))
    zoom = cfg.montage_zoom
    w, h = cfg.montage_width, cfg.montage_height

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (w, h))
    prev_tail = deque(maxlen=fade_frames)  # 上一张的尾部帧，用于淡入淡出
    try:
        for idx, p in enumerate(image_paths):
            img = read_image(p)
            win = _window(img, w, h)
            n_frames = max(int(per * fps), 1)
            zoom_in = idx % 2 == 0  # 相邻图交替推近/拉远
            tail = deque(maxlen=fade_frames)
            for f in range(n_frames):
                t = f / max(n_frames - 1, 1)
                scale = 1.0 + zoom * (t if zoom_in else (1 - t))
                frame = _zoom_frame(img, win, scale, w, h)
                if prev_tail and f < fade_frames:
                    prev = prev_tail[f] if f < len(prev_tail) else prev_tail[-1]
                    alpha = (f + 1) / fade_frames
                    frame = cv2.addWeighted(prev, 1 - alpha, frame, alpha, 0)
                writer.write(frame)
                tail.append(frame)
            prev_tail = tail
    finally:
        writer.release()


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
    """按 scale 在窗口内取更小裁窗并缩放到目标尺寸（Ken Burns）。"""
    import cv2

    x, y, cw, ch = win
    s = max(0.05, 1.0 / scale)
    ow, oh = max(1, int(cw * s)), max(1, int(ch * s))
    cx, cy = x + cw / 2, y + ch / 2
    x0 = min(max(0, int(cx - ow / 2)), img.shape[1] - ow)
    y0 = min(max(0, int(cy - oh / 2)), img.shape[0] - oh)
    crop = img[y0:y0 + oh, x0:x0 + ow]
    return cv2.resize(crop, (w, h), interpolation=cv2.INTER_AREA)


def cmd_montage(args, cfg) -> int:
    src = Path(args.dir)
    if not src.is_dir():
        print(f"错误：图集目录不存在: {src}")
        return 2
    imgs = sorted(p for p in src.iterdir() if p.is_file() and p.suffix.lower() in _IMG_EXTS)
    if not imgs:
        print(f"错误：{src} 下没有图片（png/jpg/webp/bmp）")
        return 2

    tag = args.tag or src.name
    run_dir = archive.bucket(cfg, "视频", f"{tag}-{archive.stamp()}")
    out = run_dir / f"{tag}-montage.mp4"
    per = args.per or cfg.montage_per_image

    print(f"[montage] 图集 → 视频 · {len(imgs)} 张 · {cfg.montage_width}x{cfg.montage_height}@{cfg.montage_fps}fps")
    for p in imgs:
        print(f"    {p.name}")
    if args.dry_run:
        print(f"  [dry-run] 将合成: {out}")
        return 0

    try:
        render_montage(cfg, imgs, out, per=per)
    except ImportError:
        print("错误：缺少 opencv-python。先 uv pip install -r scripts/requirements.txt")
        return 2

    size_mb = out.stat().st_size / 1024 / 1024
    print(f"  ✅ {out} ({size_mb:.1f} MB)")
    archive.write_json(run_dir / "manifest.json", {
        "phase": "合成 montage（图集 → 视频）",
        "images": [str(p) for p in imgs],
        "tag": tag,
        "fps": cfg.montage_fps,
        "per_image_sec": per,
        "size": f"{cfg.montage_width}x{cfg.montage_height}",
        "created": archive.stamp(),
    })
    print("  配乐/字幕/文案建议到剪映等工具叠加（脚本不处理音频）。")
    return 0


def register(sub) -> None:
    p = sub.add_parser("montage", help="合成：图集 → 9:16 动态视频（Ken Burns + 淡入淡出，零成本）")
    p.add_argument("--dir", required=True, help="图集目录（含按顺序命名的图片）")
    p.add_argument("--tag", default=None, help="产物 tag（默认取目录名）")
    p.add_argument("--per", type=float, default=None, help="每张停留秒数（默认 2.5）")
    p.add_argument("--dry-run", action="store_true", help="只预览，不合成")
    p.set_defaults(fn=cmd_montage)
