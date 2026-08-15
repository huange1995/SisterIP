# -*- coding: utf-8 -*-
"""共享编排（自包含，可共享）：成本预估 / 校验档位 / 读图裁剪 / 9:16 竖版首帧准备。

图片与视频子命令共用这些帮手；跨子命令复用，避免各命令各写一份。
"""

from __future__ import annotations

import random
from pathlib import Path

import archive
from config import Config


# ---------------------------------------------------------------- 通用
def seeds(n: int, start: int | None) -> list[int]:
    if start is not None:
        return [start + i for i in range(n)]
    return [random.randint(0, 2**31 - 1) for _ in range(n)]


def cost_image(cfg: Config, n: int) -> str:
    p = cfg.price_per_image
    return f"预计成本 ≈ {n} × ¥{p:.2f} = ¥{n * p:.2f}"


def cost_video(cfg: Config, seconds: int) -> str:
    p = cfg.price_per_video_second
    return f"预计成本 ≈ {seconds}s × ¥{p:.2f} ≈ ¥{seconds * p:.2f}（720p 估算，开通后以实际计费为准）"


def verdict_label(score: float | None, pass_t: float, warn_t: float) -> tuple[str, str]:
    """(档位标签, 处置动作)。score=None → 未检出人脸。"""
    if score is None:
        return "无脸", "quarantine"   # 人不变无法确认 → 进 rejected
    if score >= pass_t:
        return f"通过(≥{pass_t:g})", "keep"
    if score >= warn_t:
        return f"存疑({warn_t:g}–{pass_t:g})", "keep"
    return f"串味(<{warn_t:g})", "reject"


# ---------------------------------------------------------------- 读图 / 裁剪（Windows 中文路径安全）
def read_image(path: Path):
    """cv2.imread 对中文路径会失败，用 np.fromfile + imdecode。"""
    import cv2
    import numpy as np

    data = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"读图失败: {path}")
    return img


def ratio_window_size(img, tw: int, th: int) -> tuple[int, int]:
    """在源图内取目标比例 (tw:th) 的中心窗口尺寸。"""
    H, W = img.shape[:2]
    r = tw / th
    if W / H > r:
        return int(H * r), H
    return W, int(W / r)


def center_crop(img, cw: int, ch: int):
    H, W = img.shape[:2]
    x, y = max(0, (W - cw) // 2), max(0, (H - ch) // 2)
    return img[y:y + ch, x:x + cw]


# ---------------------------------------------------------------- 9:16 竖版首帧准备
def prepare_first_frame(cfg: Config, base: Path, mode: str, out_dir: Path, *,
                        gen=None, ff_prompt: str | None = None,
                        size: str | None = None, dry_run: bool = False) -> Path:
    """生成 9:16 竖版首帧图，返回路径。

    crop   ：中心裁剪基准图（零成本，保脸，可能切构图）
    derive ：以基准图为脸参考，Seedream 图生图出竖版写真（构图完整，需 gen + ff_prompt，约 ¥0.25/次）
    """
    out_dir = Path(out_dir)
    if mode == "crop":
        out = out_dir / "firstframe.jpg"
        if dry_run:
            print(f"    首帧(crop)：{base.name} → {out.name}（9:16 中心裁剪）")
            return out
        import cv2
        img = read_image(base)
        cw, ch = ratio_window_size(img, cfg.montage_width, cfg.montage_height)
        cropped = center_crop(img, cw, ch)
        ok, buf = cv2.imencode(".jpg", cropped, [cv2.IMWRITE_JPEG_QUALITY, 95])
        if not ok:
            raise ValueError("首帧编码失败")
        out.parent.mkdir(parents=True, exist_ok=True)
        buf.tofile(str(out))
        return out

    if mode == "derive":
        out = out_dir / "firstframe.png"
        if dry_run:
            print(f"    首帧(derive)：Seedream 图生图(竖版 {size or cfg.firstframe_size}) 以基准图 {base.name} 为脸参考")
            return out
        if gen is None:
            raise ValueError("derive 首帧需要 Seedream 生成器（内部错误）")
        if not ff_prompt:
            raise ValueError("derive 首帧需要 --ff-prompt（竖版写真图片提示词，非动作提示词）")
        print("    首帧(derive)：Seedream 图生图出竖版写真 …", flush=True)
        img = gen.generate_one(ff_prompt, reference=base, size=size or cfg.firstframe_size)
        archive.write(out, img)
        return out

    raise ValueError(f"未知首帧模式: {mode}")
