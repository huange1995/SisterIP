# -*- coding: utf-8 -*-
"""成片子命令：compose —— 镜头脚本 → 一条成片（导演层）。

一条脚本 = 一部短片：逐镜产 clip（images/image 本地 montage 零成本 / seedance 付费）
→ 拼帧 → 混音（BGM + 火山 TTS 旁白）→ 封装 mp4 → 导出 SRT → 归档。

- seedance 镜走后置「成片门」：抽帧人不变（50%/90% vs 基准图），不过整批进拒图/视频/。
- 未开通 Seedance / 未配 TTS 凭据都能 --dry-run 全链路验证；真实跑时对应镜降级警告。
- 产物：{title}.mp4 + subtitle.srt + clips/ + manifest.json
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import archive
import shotlist
from config import Config
from engine import ffmpeg
from engine.errors import GeneratorError
from engine.seedance import SeedanceClient
from engine.seedream import SeedreamGenerator
from engine.tts import TTSClient
from media import audio as audio_media
from media import montage, subtitle
from pipeline import (
    cost_video, is_image, prepare_first_frame, ratio_to_px, verdict_label,
)
from validator import FaceValidator

COMPOSE_JSON_HINT = (
    "镜头脚本是 JSON 文件，示例见 references/成片链/09-成片层.md 与 shotlist.py 文档"
)


def _resolve_path(cfg: Config, p: str) -> Path:
    """脚本里的路径先按绝对/当前判断，否则相对 output_root 解析。"""
    cand = Path(p).expanduser()
    if cand.is_file() or cand.is_dir():
        return cand
    return cfg.output_root / p


def _canvas_size(cfg: Config, ratio: str) -> tuple[int, int]:
    """'9:16' → (1080, 1920)：宽固定 montage_width，高按比例算出。"""
    tw, th = ratio_to_px(ratio)
    w = cfg.montage_width
    return w, int(w * th / tw)


def _scene_images(cfg: Config, sc: dict) -> list[Path]:
    """images 源 → 图集文件列表（按文件名排序）。"""
    d = _resolve_path(cfg, sc["dir"])
    if not d.is_dir():
        raise GeneratorError(f"scene {sc['id']} 图集目录不存在: {d}")
    imgs = sorted(p for p in d.iterdir() if p.is_file() and is_image(p))
    if not imgs:
        raise GeneratorError(f"scene {sc['id']} 图集目录无图片: {d}")
    return imgs


# ---------------------------------------------------------------- 镜头 → clip
def _render_local_clip(cfg: Config, sc: dict, out_dir: Path, *,
                       size: tuple[int, int], fps: int) -> Path:
    """images / image 源：本地 montage 渲染（零成本）。"""
    out = out_dir / f"{sc['id']}.mp4"
    texts = [sc.get("text")] * (len(_scene_images(cfg, sc)) if sc["src"] == "images" else 1) \
        if sc.get("text") else None
    if sc["src"] == "images":
        imgs = _scene_images(cfg, sc)
        montage.render_slideshow(
            cfg, imgs, out, per=sc["per"], size=size, fps=fps,
            cuts=sc.get("cuts", "dissolve"), cam=sc.get("cam", "alternate"),
            texts=texts,
        )
    else:  # image：单图单镜
        montage.render_slideshow(
            cfg, [_resolve_path(cfg, sc["base"])], out, per=sc["dur"],
            size=size, fps=fps, cuts="hard", cam=sc.get("cam", "zoom-in"),
            texts=texts,
        )
    return out


def _render_seedance_clip(cfg: Config, sc: dict, out_dir: Path, *,
                          size: tuple[int, int], fps: int,
                          prev_clips: dict[str, Path] | None = None) -> Path:
    """seedance 源：图生视频 → 下载 → 盖字卡。返回 clip 路径。

    continue_from：跨镜末帧接龙——抽上一镜 clip 末帧作首帧参考（脸/姿态延续），
    代替默认的「基准图 derive/crop 首帧」。
    """
    base = _resolve_path(cfg, sc["base"])
    mode = sc.get("firstframe", "derive")
    gen = SeedreamGenerator(cfg) if mode == "derive" else None

    cf = sc.get("continue_from")
    if cf:
        prev = (prev_clips or {}).get(cf)
        if prev is None:
            raise GeneratorError(f"scene {sc['id']} 的 continue_from 无前置 clip: {cf}")
        ff = ffmpeg.last_frame(prev, out_dir / f"{sc['id']}-firstframe.jpg",
                               size=cfg.firstframe_size)
        print(f"    首帧(接龙)：抽 scene {cf} 末帧 → {ff.name}", flush=True)
    else:
        ff = prepare_first_frame(cfg, base, mode, out_dir, gen=gen,
                                 ff_prompt=sc.get("ff_prompt"), size=cfg.firstframe_size)

    duration = -1 if sc.get("auto") else int(sc["dur"])  # auto → 自定时长
    client = SeedanceClient(cfg)
    print(f"  ① scene {sc['id']} 提交 Seedance 任务 …", flush=True)
    task = client.create_task(
        prompt=sc["prompt"], first_frame=ff, model=cfg.video_model,
        duration=duration, ratio=cfg.video_ratio, resolution=cfg.video_resolution,
        watermark=cfg.video_watermark,
    )
    task_id = task["id"]
    print(f"    task_id={task_id}，轮询中 …", flush=True)
    result = client.poll_task(task_id)
    mp4 = out_dir / f"{sc['id']}-raw.mp4"
    client.download_video(client.video_url(result), mp4)

    # 盖字卡（seedance 片字幕在渲染后补；montage 帧渲染时已烧），底部居中
    if sc.get("text"):
        card = subtitle.text_card(sc["text"], cfg, max_w=int(size[0] * cfg.subtitle_max_width_ratio))
        card_png = out_dir / f"{sc['id']}-card.png"
        subtitle.card_to_png(card, card_png)
        cw, ch = card.size
        x = (size[0] - cw) // 2
        y = size[1] - ch - cfg.subtitle_bottom
        overlay = out_dir / f"{sc['id']}.mp4"
        ffmpeg.overlay_card(mp4, card_png, overlay, x=x, y=y)
        mp4.unlink(missing_ok=True)
        return overlay
    mp4.rename(out_dir / f"{sc['id']}.mp4")
    return out_dir / f"{sc['id']}.mp4"


# ---------------------------------------------------------------- 成片门（人不变）
def _verify_seedance(cfg: Config, sc: dict, clips: dict, validator) -> list[dict]:
    """对 seedance 镜抽帧校验（0.5/0.9 vs 基准图）。返回检查记录。"""
    base = _resolve_path(cfg, sc["base"])
    checks = []
    for frac in (0.5, 0.9):
        frame_path = clips[sc["id"]].parent / f"check-{sc['id']}-{int(frac*100):02d}.png"
        try:
            validator.extract_frame(clips[sc["id"]], frac, frame_path)
        except Exception as e:
            print(f"    ⚠ 抽帧失败: {e}")
            continue
        if not frame_path.exists():
            continue
        try:
            score = validator.score_file(frame_path, base)
        except Exception as e:
            print(f"    ⚠ 校验出错: {e}")
            continue
        label, action = verdict_label(score, cfg.threshold_pass, cfg.threshold_warn)
        checks.append({"frac": frac, "file": frame_path.name,
                       "score": round(score, 4) if score is not None else None,
                       "label": label, "action": action})
        mark = {"keep": "✅", "quarantine": "🟡", "reject": "❌"}.get(action, "➖")
        print(f"    {mark} {frame_path.name}: {label}"
              + (f" ({score:.3f})" if score is not None else ""))
    return checks


# ---------------------------------------------------------------- 主流程
def cmd_compose(args, cfg) -> int:
    script_path = Path(args.script)
    if not script_path.is_file():
        print(f"错误：脚本不存在: {script_path}\n{COMPOSE_JSON_HINT}")
        return 2
    try:
        parsed = shotlist.parse(json.loads(script_path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, shotlist.ShotListError) as e:
        print(f"错误：镜头脚本不合法 —— {e}\n{COMPOSE_JSON_HINT}")
        return 2

    title = parsed["title"]
    size = _canvas_size(cfg, parsed["ratio"])
    fps = parsed["fps"]
    run_dir = archive.video_run(cfg, title)
    clips_dir = run_dir / "clips"

    # auto 多镜头镜（dur<=0）：API 用 -1 自定时长，但时间轴需一个估算值 → 用配置时长
    for sc in parsed["scenes"]:
        if sc["src"] == "seedance" and sc["dur"] <= 0:
            sc["auto"] = True
            sc["dur"] = float(cfg.video_duration)

    # 图集镜实际张数 → 时序
    image_counts = {}
    for sc in parsed["scenes"]:
        if sc["src"] == "images":
            image_counts[sc["id"]] = len(_scene_images(cfg, sc))
    plan = shotlist.resolve_timing(parsed, image_counts)

    # 成本
    st = shotlist.cost_stats(parsed, image_counts)
    print(f"[compose] 成片「{title}」· {parsed['ratio']} · {fps}fps · "
          f"画幅 {size[0]}x{size[1]}")
    if st.n_paid:
        print(f"  {cost_video(cfg, int(st.paid_seconds))}（{st.n_paid} 个 seedance 镜；"
              f"{st.n_free} 个本地镜零成本）")
    else:
        print(f"  全本地零成本（{st.n_free} 镜，无 seedance）")

    # 音频轨（dry-run 也算：BGM 解析 + 旁白清单）
    audio_cfg = parsed["audio"]
    bgm = audio_media.resolve_bgm(cfg, audio_cfg.get("bgm"))
    vo_plan = [
        (next(p["start"] for p in plan if p["scene"]["id"] == vo["scene"]), vo["scene"], vo["text"])
        for vo in audio_cfg.get("voiceover", [])
    ]

    print(f"\n  镜头计划：")
    for p in plan:
        sc = p["scene"]
        extra = f"  text={sc.get('text')!r}" if sc.get("text") else ""
        if sc["src"] == "seedance":
            prompt_pre = sc["prompt"].split("Shot")[0].strip()[:28] or "多镜 Seedance"
            cf = f" 接续{sc['continue_from']}" if sc.get("continue_from") else ""
            print(f"    {p['start']:>5.1f}s–{p['start']+p['dur']:>5.1f}s  {sc['id']} "
                  f"[seedance] {prompt_pre}…{cf}{extra}")
        else:
            print(f"    {p['start']:>5.1f}s–{p['start']+p['dur']:>5.1f}s  {sc['id']} "
                  f"[{sc['src']}] {sc.get('dir') or sc.get('base')}{extra}")
    print(f"\n  音频：")
    print(f"    BGM: {bgm or '（无，QYJ_BGM_DIR 未配置/未命中）'}")
    if vo_plan:
        for start, sid, text in vo_plan:
            print(f"    旁白 t={start:.1f}s  scene={sid}: {text}")
    else:
        print(f"    旁白: （无）")
    print(f"\n  字幕（SRT）：")
    cards = shotlist.subtitle_cards(plan)
    if cards:
        for s, e, t in cards:
            print(f"    {s:.1f}s–{e:.1f}s  {t}")
    else:
        print(f"    （无）")

    if parsed.get("grade"):
        print(f"\n  连贯：统一调色 grade={parsed['grade']}（全镜拼帧前套同套，消除跨镜色调漂移）")

    if args.dry_run:
        print(f"\n  [dry-run] 零 API。产物将归档: {run_dir}")
        return 0

    # ① 逐镜产 clip
    clips_dir.mkdir(parents=True, exist_ok=True)
    clips: dict[str, Path] = {}
    print(f"\n  ① 逐镜产 clip → {clips_dir}")
    for p in plan:
        sc = p["scene"]
        try:
            if sc["src"] == "seedance":
                clips[sc["id"]] = _render_seedance_clip(cfg, sc, clips_dir, size=size, fps=fps,
                                                        prev_clips=clips)
            else:
                clips[sc["id"]] = _render_local_clip(cfg, sc, clips_dir, size=size, fps=fps)
            print(f"    ✅ scene {sc['id']} → {clips[sc['id']].name}")
        except GeneratorError as e:
            print(f"    ❌ scene {sc['id']} 失败: {e}")
            return 2

    # ② 成片门：seedance 镜抽帧人不变（纯本地镜无 seedance → 跳过，免加载人脸模型）
    has_seedance = any(sc["src"] == "seedance" for sc in parsed["scenes"])
    validator = None
    checks: dict[str, list[dict]] = {}
    if has_seedance and not args.no_validate:
        try:
            validator = FaceValidator(cfg)
        except Exception as e:
            print(f"  ⚠  未加载人脸校验器，跳过「人不变」校验: {e}")
    if validator is not None:
        print(f"\n  ② 成片门（seedance 镜抽帧人不变）…")
        for p in plan:
            sc = p["scene"]
            if sc["src"] == "seedance":
                checks[sc["id"]] = _verify_seedance(cfg, sc, clips, validator)
        all_bad = [c for chk in checks.values() for c in chk if c["action"] in ("reject", "quarantine")]
        if all_bad:
            rej_dir = archive.bucket(cfg, "拒图", "视频", f"{title}-{archive.stamp()}")
            shutil.move(str(run_dir), str(rej_dir))
            print(f"⚠ 未过人不变：{', '.join(c['label'] for c in all_bad)} → 整批移入 {rej_dir}")
            print("  建议：换 seedance 提示词（动小不动大）/ 缩时长 / 人工复核。")
            return 1

    # ②.5 统一调色（grade）：每镜 clip 拼帧前套同一套，消除跨镜色调漂移
    concat_src: dict[str, Path] = {}
    if parsed.get("grade"):
        print(f"\n  ② 统一调色（grade={parsed['grade']}）…")
        for sc in parsed["scenes"]:
            src = clips[sc["id"]]
            eff = ffmpeg.apply_grade(src, clips_dir / f"{sc['id']}-graded.mp4", parsed["grade"])
            concat_src[sc["id"]] = eff
            if eff != src:
                print(f"    {sc['id']} → {eff.name}")
    else:
        concat_src = clips

    # ③ 拼帧 → 静片
    silent = run_dir / f"{title}-silent.mp4"
    print(f"\n  ③ 拼帧 {len(clips)} 个 clip → 成片画幅 …")
    ffmpeg.concat_clips([concat_src[sc["id"]] for sc in parsed["scenes"]],
                        silent, size=f"{size[0]}x{size[1]}", fps=fps)

    # ④ 音频：旁白轨（TTS）+ BGM → 混音 → 封装
    print(f"\n  ④ 音频轨 …")
    tracks = []
    tts = TTSClient(cfg)
    vo_out = clips_dir
    for start, sid, text in vo_plan:
        track = audio_media.voiceover_track(cfg, tts, text, vo_out, start_sec=start, label=sid)
        if track:
            tracks.append(track)
    if bgm:
        vol = audio_cfg.get("bgm_volume") if audio_cfg.get("bgm_volume") is not None else cfg.bgm_volume
        # 淡出落在视频结尾（BGM 比成片长时 -shortest 才会在音乐末尾前收住，不硬切）
        video_total = plan[-1]["start"] + plan[-1]["dur"] if plan else 0.0
        fade_out_at = max(0.0, video_total - cfg.bgm_fade)
        tracks.append({"path": bgm, "delay": 0.0, "volume": vol,
                       "fade_in": cfg.bgm_fade, "fade_out": cfg.bgm_fade,
                       "fade_out_at": fade_out_at})
        print(f"    BGM → {bgm.name}（vol={vol}，淡入 {cfg.bgm_fade}s，淡出至 {fade_out_at:.1f}s）")
    mixed = audio_media.build_mix(cfg, tracks, clips_dir)

    final = run_dir / archive.compose_name(title)
    if mixed is not None:
        ffmpeg.mux(silent, mixed, final)
        silent.unlink(missing_ok=True)
    else:
        silent.rename(final)
    print(f"    ✅ {final}")

    # ⑤ 字幕 SRT
    srt = run_dir / archive.subtitle_name()
    if cards:
        subtitle.export_srt(cards, srt)
        print(f"\n  ⑤ 字幕 → {srt}（供剪映花字精修）")

    archive.write_json(run_dir / archive.manifest_name(), {
        "phase": "成片 compose",
        "title": title,
        "script": str(script_path),
        "ratio": parsed["ratio"],
        "fps": fps,
        "size": f"{size[0]}x{size[1]}",
        "timing": [{"id": p["scene"]["id"], "src": p["scene"]["src"],
                    "start": p["start"], "dur": p["dur"],
                    **({"continue_from": p["scene"]["continue_from"]} if p["scene"].get("continue_from") else {}),
                    } for p in plan],
        "grade": parsed.get("grade"),
        "audio": {"bgm": str(bgm) if bgm else None, "voiceover": vo_plan},
        "subtitle": [{"start": s, "end": e, "text": t} for s, e, t in cards],
        "frame_checks": checks,
        "clips": [c.name for c in clips.values()],
        "final": final.name,
        "srt": srt.name if cards else None,
        "created": archive.stamp(),
    })
    print(f"\n✅ 成片完成：{final}（{final.stat().st_size / 1024 / 1024:.1f} MB）")
    print("  下一步：人工看片 → 满意则精选进 作品集/，不足则回改脚本重跑。")
    return 0


def register(sub) -> None:
    p = sub.add_parser("compose", help="成片：镜头脚本 → 一条短片（多镜头 + 音频 + 字幕 + 成片门）")
    p.add_argument("--script", required=True, help="镜头脚本 JSON 路径")
    p.add_argument("--no-validate", action="store_true", help="跳过 seedance 镜抽帧人不变校验")
    p.add_argument("--dry-run", action="store_true", help="只打印镜头计划/成本/音频/字幕，零 API")
    p.set_defaults(fn=cmd_compose)
