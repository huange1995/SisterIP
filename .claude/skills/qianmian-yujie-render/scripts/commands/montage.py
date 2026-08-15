# -*- coding: utf-8 -*-
"""合成子命令：montage —— 图集 → 9:16 动态视频（零成本，路线 C 多镜头）。

薄壳：参数解析 + 归档，渲染逻辑在 media/montage.render_slideshow。
多镜头升级：--cuts（溶解/硬切）、--cam（机位方向）、--text（烧字卡）。
"""

from __future__ import annotations

from pathlib import Path

import archive
from media.montage import CAM_MODES, CUT_MODES, render_slideshow
from pipeline import is_image


def cmd_montage(args, cfg) -> int:
    src = Path(args.dir)
    if not src.is_dir():
        print(f"错误：图集目录不存在: {src}")
        return 2
    imgs = sorted(p for p in src.iterdir() if p.is_file() and is_image(p))
    if not imgs:
        print(f"错误：{src} 下没有图片（png/jpg/webp/bmp）")
        return 2

    texts: list[str | None] = []
    if args.text:
        parts = [t.strip() for t in args.text.split("|")] if "|" in args.text else [args.text]
        for i in range(len(imgs)):
            texts.append(parts[i] if i < len(parts) else None)
        print("  ⚠ --text 只对前 N 张逐张烧字卡，后续图无字卡（多镜字幕建议用 compose 镜头脚本）")

    tag = args.tag or src.name
    run_dir = archive.bucket(cfg, "视频", f"{tag}-{archive.stamp()}")
    out = run_dir / f"{tag}-montage.mp4"
    per = args.per or cfg.montage_per_image
    cam = args.cam or "alternate"
    cuts = args.cuts or "dissolve"
    w, h = cfg.montage_width, cfg.montage_height

    print(f"[montage] 图集 → 视频 · {len(imgs)} 张 · {w}x{h}@{cfg.montage_fps}fps"
          f" · cuts={cuts} cam={cam}")
    for p in imgs:
        print(f"    {p.name}")
    if args.dry_run:
        print(f"  [dry-run] 将合成: {out}")
        if texts:
            print(f"  字卡: {texts}")
        return 0

    try:
        render_slideshow(cfg, imgs, out, per=per, size=(w, h), fps=cfg.montage_fps,
                         cuts=cuts, cam=cam, texts=texts or None)
    except ImportError:
        print("错误：缺少依赖（opencv-python / Pillow）。先 uv pip install -r scripts/requirements.txt")
        return 2

    size_mb = out.stat().st_size / 1024 / 1024
    print(f"  ✅ {out} ({size_mb:.1f} MB)")
    archive.write_json(run_dir / "manifest.json", {
        "phase": "合成 montage（图集 → 视频）",
        "images": [str(p) for p in imgs],
        "tag": tag,
        "fps": cfg.montage_fps,
        "per_image_sec": per,
        "cuts": cuts,
        "cam": cam,
        "size": f"{w}x{h}",
        "texts": texts or None,
        "created": archive.stamp(),
    })
    print("  配乐/字幕/多镜台词建议用 compose 镜头脚本一键成片。")
    return 0


def register(sub) -> None:
    p = sub.add_parser("montage", help="合成：图集 → 9:16 动态视频（Ken Burns / 硬切·溶解 / 烧字卡，零成本）")
    p.add_argument("--dir", required=True, help="图集目录（含按顺序命名的图片）")
    p.add_argument("--tag", default=None, help="产物 tag（默认取目录名）")
    p.add_argument("--per", type=float, default=None, help="每张停留秒数（默认 2.5）")
    p.add_argument("--cuts", choices=CUT_MODES, default=None, help="镜头切换：dissolve 溶解（默认）| hard 硬切")
    p.add_argument("--cam", choices=CAM_MODES, default=None, help="机位：zoom-in/zoom-out/pan/alternate（默认 alternate）")
    p.add_argument("--text", default=None, help="字卡文案，多图用 | 分隔，如 '开场|高潮'")
    p.add_argument("--dry-run", action="store_true", help="只预览，不合成")
    p.set_defaults(fn=cmd_montage)
