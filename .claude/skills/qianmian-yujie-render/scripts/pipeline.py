# -*- coding: utf-8 -*-
"""共享编排（自包含，可共享）：成本预估 / 校验档位 / 读图解码 / 裁剪 / 9:16 竖版首帧准备。

图片与视频子命令共用这些帮手；跨子命令复用，避免各命令各写一份。
Windows 中文路径安全统一走 decode_image / imwrite_safe。
"""

from __future__ import annotations

import random
from pathlib import Path

import archive
from config import Config

# 图片扩展名统一集合（候选 / 衍生 / montage / 首帧共用）
IMG_EXTS = frozenset({".png", ".jpg", ".jpeg", ".webp", ".bmp"})


def is_image(path: Path) -> bool:
    return Path(path).suffix.lower() in IMG_EXTS


# ---------------------------------------------------------------- 种子 / 成本
def seeds(n: int, start: int | None) -> list[int]:
    """确定性种子序列：给 start 则 start, start+1, …；否则每次随机。"""
    if start is not None:
        return [start + i for i in range(n)]
    return [random.randint(0, 2**31 - 1) for _ in range(n)]


def cost(cfg: Config, n: float, unit: str, price: float, note: str = "") -> str:
    """统一成本文案：n 个/秒 × 单价。"""
    suffix = f"（{note}）" if note else ""
    return f"预计成本 ≈ {n:g} × ¥{price:.2f} ≈ ¥{n * price:.2f}{suffix}"


def cost_image(cfg: Config, n: int) -> str:
    return cost(cfg, n, "张", cfg.price_per_image)


def cost_video(cfg: Config, seconds: int) -> str:
    return cost(cfg, seconds, "s", cfg.price_per_video_second, note="720p 估算，开通后以实际计费为准")


# ---------------------------------------------------------------- 校验档位
def verdict_label(score: float | None, pass_t: float, warn_t: float) -> tuple[str, str]:
    """(档位标签, 处置动作)。score=None → 未检出人脸。"""
    if score is None:
        return "无脸", "quarantine"   # 人不变无法确认 → 进 rejected
    if score >= pass_t:
        return f"通过(≥{pass_t:g})", "keep"
    if score >= warn_t:
        return f"存疑({warn_t:g}–{pass_t:g})", "keep"
    return f"串味(<{warn_t:g})", "reject"


# ---------------------------------------------------------------- 读图 / 解码（Windows 中文路径安全）
def decode_image(data: bytes):
    """bytes → BGR ndarray（cv2.imread 对中文路径会失败，统一用 imdecode）。"""
    import cv2
    import numpy as np

    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("图片解码失败")
    return img


def read_image(path: Path):
    """文件 → BGR ndarray（np.fromfile 绕开 cv2 中文路径问题）。"""
    p = Path(path)
    import numpy as np
    return decode_image(np.fromfile(str(p), dtype=np.uint8))


def imwrite_safe(path: Path, img, ext: str | None = None) -> Path:
    """BGR ndarray → 文件（imencode + tofile，中文路径安全）。ext 决定编码格式。"""
    import cv2

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fmt = ext or p.suffix or ".png"
    ok, buf = cv2.imencode(fmt, img)
    if not ok:
        raise ValueError(f"图片编码失败: {p}")
    buf.tofile(str(p))
    return p


# ---------------------------------------------------------------- 裁剪（9:16 等目标比例）
def center_window(img, tw: int, th: int) -> tuple[int, int, int, int]:
    """源图内取目标比例 (tw:th) 的中心窗口，返回 (x, y, cw, ch)。"""
    H, W = img.shape[:2]
    r = tw / th
    if W / H > r:
        cw, ch = int(H * r), H
    else:
        cw, ch = W, int(W / r)
    return max(0, (W - cw) // 2), max(0, (H - ch) // 2), cw, ch


def center_crop(img, cw: int, ch: int):
    H, W = img.shape[:2]
    x, y = max(0, (W - cw) // 2), max(0, (H - ch) // 2)
    return img[y:y + ch, x:x + cw]


def ratio_to_px(ratio: str, max_px: int = 4000) -> tuple[int, int]:
    """'9:16' → (900, 1600) 整数比例（用于裁剪 target 与首帧）。"""
    try:
        tw, th = (int(v) for v in ratio.lower().replace(" ", "").split(":"))
    except ValueError:
        raise ValueError(f"无效比例: {ratio}（应为 宽:高，如 9:16）")
    g = _gcd(tw, th) or 1
    return tw // g, th // g


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


# ---------------------------------------------------------------- 9:16 竖版首帧准备
def prepare_first_frame(cfg: Config, base: Path, mode: str, out_dir: Path, *,
                        gen=None, ff_prompt: str | None = None,
                        size: str | None = None, dry_run: bool = False) -> Path:
    """生成 9:16 竖版首帧图，返回路径。

    crop   ：中心裁剪基准图（零成本，保脸，可能切构图）
    derive ：以基准图为脸参考，Seedream 图生图出竖版写真（构图完整，需 gen + ff_prompt，约 ¥0.25/次）
    """
    out_dir = Path(out_dir)
    tw, th = ratio_to_px(cfg.firstframe_ratio)
    if mode == "crop":
        out = out_dir / "firstframe.jpg"
        if dry_run:
            print(f"    首帧(crop)：{base.name} → {out.name}（{cfg.firstframe_ratio} 中心裁剪）")
            return out
        img = read_image(base)
        x, y, cw, ch = center_window(img, tw, th)
        cropped = center_crop(img, cw, ch)
        import cv2
        return imwrite_safe(out, cropped, ext=".jpg")  # JPEG 质量走 cv2 默认（95）

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
