# -*- coding: utf-8 -*-
"""视频子命令：video —— Seedance 图生视频（异步两段式，可选增强）。

流程：基准图 → 9:16 竖版首帧 → 提交 Seedance 任务 → 轮询 → 下载 MP4
     → 抽帧「人不变」校验（50%/90% 帧 vs 基准图）→ 归档 / 进拒图。

- 未开通 Seedance 也能 `--dry-run` 验证全部前置（首帧准备 + 参数组装）。
- 动作提示词遵循「动小不动大」：轻抬眼帘 / 发丝微扬 / 指尖拂发 / 回眸。
"""

from __future__ import annotations

import shutil
from pathlib import Path

import archive
from engine.seedance import SeedanceClient
from engine.seedream import SeedreamGenerator
from pipeline import cost_video, prepare_first_frame, verdict_label
from validator import FaceValidator


def cmd_video(args, cfg) -> int:
    base = Path(args.base)
    if not base.is_file():
        print(f"错误：基准图不存在: {base}")
        return 2
    prompt = args.prompt.strip()
    if not prompt:
        print("错误：--prompt 不能为空")
        return 2

    tag = args.tag or "video"
    duration = args.duration if args.duration is not None else cfg.video_duration
    ratio = args.ratio or cfg.video_ratio
    resolution = args.resolution or cfg.video_resolution
    model = args.model or cfg.video_model
    mode = args.firstframe or cfg.firstframe_mode
    run_dir = archive.bucket(cfg, "视频", f"{tag}-{archive.stamp()}")

    api_duration = duration if duration > 0 else -1  # -1 → auto（多镜头 2.0 自定时长）
    print(f"[video] Seedance 图生视频 · {tag}")
    print(f"  {cost_video(cfg, duration if duration > 0 else cfg.video_duration)}")
    print(f"  model={model}  {ratio} {resolution} {duration}s{' (auto 多镜头)' if duration <= 0 else ''}  首帧={mode}")
    if mode == "derive" and not args.ff_prompt and not args.dry_run:
        print("错误：--firstframe derive 需要 --ff-prompt（竖版写真图片提示词，非动作提示词）")
        return 2

    # ① 竖版首帧
    gen = None
    if mode == "derive" and not args.dry_run:
        gen = SeedreamGenerator(cfg)
    try:
        ff = prepare_first_frame(cfg, base, mode, run_dir, gen=gen,
                                 ff_prompt=args.ff_prompt, size=cfg.firstframe_size,
                                 dry_run=args.dry_run)
    except Exception as e:
        print(f"错误：首帧准备失败: {e}")
        return 2

    if args.dry_run:
        print(f"  [dry-run] 将提交 Seedance 任务：动作提示词={prompt}")
        print(f"    → 产物将归档: {run_dir}")
        return 0

    # ② 提交 → 轮询 → 下载
    client = SeedanceClient(cfg)
    print("  ① 提交视频任务 …", flush=True)
    task = client.create_task(prompt=prompt, first_frame=ff, model=model,
                              duration=api_duration, ratio=ratio,
                              resolution=resolution, watermark=cfg.video_watermark)
    task_id = task["id"]
    print(f"    task_id={task_id}，轮询中（每 {cfg.video_poll_interval}s）…", flush=True)
    result = client.poll_task(task_id)
    video_url = client.video_url(result)
    mp4 = run_dir / f"{tag}-01.mp4"
    print("  ② 下载视频 …", flush=True)
    client.download_video(video_url, mp4)
    print(f"    ✅ {mp4} ({mp4.stat().st_size // 1024 // 1024} MB)")

    # ③ 抽帧「人不变」校验（best-effort）
    validator = None
    if not args.no_validate:
        try:
            validator = FaceValidator(cfg)
        except Exception as e:
            print(f"⚠  未加载人脸校验器，跳过「人不变」校验: {e}")

    frame_checks = []
    if validator is not None:
        print("  ③ 抽帧人不变校验（50% / 90% 处 vs 基准图）…")
        for frac in (0.5, 0.9):
            frame_path = run_dir / f"check-{int(frac * 100):02d}.png"
            try:
                validator.extract_frame(mp4, frac, frame_path)
            except Exception as e:
                print(f"    ⚠ 抽帧失败: {e}")
                frame_path = None
            if frame_path is not None and frame_path.exists():
                try:
                    score = validator.score_file(frame_path, base)
                except Exception as e:
                    print(f"    ⚠ 校验出错: {e}")
                    score = None
                label, action = verdict_label(score, cfg.threshold_pass, cfg.threshold_warn)
                frame_checks.append({
                    "frac": frac, "file": frame_path.name,
                    "score": round(score, 4) if score is not None else None,
                    "label": label, "action": action,
                })
                mark = {"keep": "✅", "quarantine": "🟡", "reject": "❌"}.get(action, "➖")
                print(f"    {mark} {frame_path.name}: {label}"
                      + (f" ({score:.3f})" if score is not None else ""))

    # ④ 归档 / 拒图
    bad = [c for c in frame_checks if c["action"] in ("reject", "quarantine")]
    if bad:
        rej_dir = archive.bucket(cfg, "拒图", "视频", f"{tag}-{archive.stamp()}")
        shutil.move(str(run_dir), str(rej_dir))
        print(f"⚠ 抽帧未过人不变：{', '.join(c['label'] for c in bad)} → 整批移入 {rej_dir}")
        print("  建议：缩短时长 / 动作改轻 / 加大固定机位后重出，或人工复核。")
    else:
        archive.write_json(run_dir / "manifest.json", {
            "phase": "视频 video（Seedance 图生视频）",
            "base": str(base),
            "prompt": prompt,
            "model": model,
            "duration": duration,
            "ratio": ratio,
            "resolution": resolution,
            "firstframe_mode": mode,
            "firstframe": str(ff),
            "task_id": task_id,
            "mp4": mp4.name,
            "frame_checks": frame_checks,
            "created": archive.stamp(),
        })
        print(f"✅ 完成：{mp4}（首帧/校验图/清单在同一目录）")
        print("  想要多镜头/配乐/旁白/字幕成片 → 用 compose 镜头脚本一键成片。")
    return 0


def register(sub) -> None:
    p = sub.add_parser("video", help="视频：Seedance 图生视频（基准图当首帧，人不变；可选增强）")
    p.add_argument("--base", required=True, help="基准图路径（定妆照）")
    p.add_argument("--prompt", required=True,
                   help="动作描述（动小不动大；多镜头 2.0 可写 Shot 1: … / Shot 2: … 一次出 2-3 镜）")
    p.add_argument("--tag", default=None, help="产物 tag，如 深夜爵士")
    p.add_argument("--duration", type=int, default=None,
                   help="时长秒数 4–15（默认 5；0 或负数 = auto，多镜头 2.0 自定时长）")
    p.add_argument("--ratio", default=None, help="比例 9:16 / 16:9 / 1:1（默认 9:16）")
    p.add_argument("--resolution", default=None, help="分辨率 720p（默认）")
    p.add_argument("--model", default=None, help="视频模型 ID（默认取 config / 环境）")
    p.add_argument("--firstframe", choices=["crop", "derive"], default=None,
                   help="首帧方式：crop 中心裁剪（默认）| derive Seedream 竖版衍生（需 --ff-prompt）")
    p.add_argument("--ff-prompt", default=None,
                   help="derive 首帧的竖版写真图片提示词（非动作提示词）")
    p.add_argument("--no-validate", action="store_true", help="跳过抽帧人不变校验")
    p.add_argument("--dry-run", action="store_true", help="只预览，不调用 API")
    p.set_defaults(fn=cmd_video)
