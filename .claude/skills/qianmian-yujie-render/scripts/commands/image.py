# -*- coding: utf-8 -*-
"""图片子命令：candidates / pick / derive / status（从旧 generate.py 迁入，行为不变）。"""

from __future__ import annotations

import shutil
from pathlib import Path

import archive
from engine.seedream import SeedreamGenerator
from pipeline import cost_image, is_image, seeds, verdict_label
from validator import FaceValidator


# ---------------------------------------------------------------- 选型：出候选
def cmd_candidates(args, cfg) -> int:
    prompt = args.prompt.strip()
    if not prompt:
        print("错误：--prompt 不能为空")
        return 2

    n = args.n
    seeds_list = seeds(n, args.seed)
    tag = args.tag or "candidate"
    run_dir = archive.bucket(cfg, "候选", f"{tag}-{archive.stamp()}")

    print(f"[candidates] 出 {n} 张候选 · 形象/栏目 tag={tag}")
    print(f"  {cost_image(cfg, n)}")
    print(f"  model={cfg.model}  size={cfg.size}")
    if args.dry_run:
        print(f"  [dry-run] 不调用 API。将写入: {run_dir}")
        for i, s in enumerate(seeds_list, 1):
            print(f"    {archive.candidate_name(i)}  seed={s}")
        print(f"  提示词预览:\n{prompt}")
        return 0

    gen = SeedreamGenerator(cfg)
    files = []
    for i, s in enumerate(seeds_list, 1):
        print(f"  生成第 {i}/{n} 张 (seed={s}) …", flush=True)
        img = gen.generate_one(prompt, seed=s)
        fname = archive.candidate_name(i)
        archive.write(run_dir / fname, img)
        files.append({"file": fname, "seed": s})
        print(f"    ✅ {run_dir / fname}")

    archive.write_json(run_dir / "manifest.json", {
        "phase": "选型 candidates",
        "prompt": prompt,
        "model": cfg.model,
        "size": cfg.size,
        "n": n,
        "tag": tag,
        "seeds": seeds_list,
        "created": archive.stamp(),
        "files": files,
    })
    print(f"\n全部候选已出。人工挑 1 张最好的，然后锁基准：")
    print(f'  python scripts/generate.py pick "{run_dir}" <文件名> --name <形象>')
    print("锁定后基准图就是该形象的「这张脸」，之后所有衍生（换装/换风格/三视图）都以它为参考。")
    return 0


# ---------------------------------------------------------------- 确认：锁基准
def cmd_pick(args, cfg) -> int:
    target = Path(args.target)
    if target.is_dir():
        if not args.file:
            print(f"错误：{target} 是目录，请给出 <文件名>")
            print(f"{target} 下现有:")
            for p in sorted(target.iterdir()):
                print(f"  {p.name}")
            return 2
        target = target / args.file

    if not target.is_file():
        print(f"错误：候选文件不存在: {target}")
        if target.parent.exists():
            print(f"{target.parent} 下现有:")
            for p in sorted(target.parent.iterdir()):
                print(f"  {p.name}")
        return 2

    if not is_image(target):
        print(f"错误：不是图片文件: {target.suffix}")
        return 2

    name = args.name or target.stem
    dest = archive.bucket(cfg, "定妆照", name, f"{name}.png")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, dest)
    print(f"✅ 已锁基准图: {dest}")
    print("  这张图从此是「这张脸」。之后所有衍生都基于它：")
    print(f'  python scripts/generate.py derive --base "{dest}" --prompt "<衍生提示词>" [--n 2] [--tag 女仆装]')
    return 0


# ---------------------------------------------------------------- 衍生：图生图 + 人不变
def cmd_derive(args, cfg) -> int:
    base = Path(args.base)
    if not base.is_file():
        print(f"错误：基准图不存在: {base}")
        return 2
    prompt = args.prompt.strip()
    if not prompt:
        print("错误：--prompt 不能为空")
        return 2

    n = args.n
    seeds_list = seeds(n, args.seed)
    tag = args.tag or "derive"
    kind = args.kind  # 三视图 → 三视图/<形象>/；栏目图（默认）→ 栏目图/<tag>/
    if kind == "三视图":
        out_dir = archive.bucket(cfg, "三视图", base.stem, tag)
    else:
        out_dir = archive.bucket(cfg, "栏目图", tag)
    rej_dir = archive.bucket(cfg, "拒图", base.stem, tag)
    pass_t = cfg.threshold_pass
    warn_t = cfg.threshold_warn

    print(f"[derive] 以基准图「{base.name}」图生图 · {kind} · {n} 张 · tag={tag}")
    print(f"  {cost_image(cfg, n)}")
    print(f"  model={cfg.model}  size={cfg.size}  reference=基准图(Data URI)")
    if args.dry_run:
        print(f"  [dry-run] 不调用 API。将写入: {out_dir}")
        for i, s in enumerate(seeds_list, 1):
            print(f"    {tag}-{i:02d}.png  seed={s}")
        print(f"  衍生提示词预览:\n{prompt}")
        return 0

    # 校验器（best-effort：没装 insightface / 缺模型 → 跳过并明确警告）
    # 放在 dry-run 之后：dry-run 零依赖、不加载人脸模型
    validator = None
    if not args.no_validate:
        try:
            validator = FaceValidator(cfg)
        except Exception as e:
            print(f"⚠  未加载人脸校验器，跳过「人不变」校验: {e}")

    gen = SeedreamGenerator(cfg)
    results = []
    for i, s in enumerate(seeds_list, 1):
        print(f"  生成第 {i}/{n} 张 (seed={s}) …", flush=True)
        img = gen.generate_one(prompt, reference=base, seed=s)
        fname = archive.derive_name(tag, i)

        # 先落盘才能对图做校验
        archive.write(out_dir / fname, img)

        if validator is None:
            label = "未校验(--no-validate)" if args.no_validate else "未校验(未装insightface)"
            action = "keep"
            score = None
        else:
            try:
                score = validator.score_file(out_dir / fname, base)
            except Exception as e:
                print(f"    ⚠ 校验出错: {e}")
                score = None
                label, action = "校验出错", "keep"
            if score is not None:
                label, action = verdict_label(score, pass_t, warn_t)
            else:
                label, action = "无脸", "quarantine"

        score_s = f" ({score:.3f})" if score is not None else ""
        if action == "reject" or action == "quarantine":
            archive.write(rej_dir / fname, img)
            (out_dir / fname).unlink(missing_ok=True)
            mark = "❌" if action == "reject" else "🟡"
            print(f"    {mark} 第 {i} 张 {label}{score_s} → 移入 {rej_dir / fname}")
        else:
            mark = "✅" if action == "keep" and validator is not None else "➖"
            print(f"    {mark} 第 {i} 张 {label}{score_s} → {out_dir / fname}")
        results.append({
            "file": fname,
            "seed": s,
            "label": label,
            "action": action,
            "score": round(score, 4) if score is not None else None,
        })

    archive.write_json(out_dir / "manifest.json", {
        "phase": "衍生 derive",
        "kind": kind,
        "base": str(base),
        "prompt": prompt,
        "model": cfg.model,
        "size": cfg.size,
        "n": n,
        "tag": tag,
        "seeds": seeds_list,
        "pass_t": pass_t,
        "warn_t": warn_t,
        "created": archive.stamp(),
        "results": results,
    })

    # 用 action 字段统计（旧版用 label 中文前缀判断，文案一改就错）
    kept = [r for r in results if r.get("action", "keep") == "keep"]
    print(f"\n完成：通过/存疑 {len(kept)} 张 → {out_dir}")
    rej = [r for r in results if r.get("action", "keep") in ("reject", "quarantine")]
    if rej:
        print(f"      串味/无脸 {len(rej)} 张 → {rej_dir}（人不变是硬前提，请人工复核）")
    print("下一步：按 references/校验.md 核对「脸 + 媚 + 封面三要素」后归档。")
    return 0


# ---------------------------------------------------------------- 状态
def cmd_status(args, cfg) -> int:
    print(f"== 定妆照 / 基准图（{cfg.output_root / '定妆照'}）==")
    base_dir = cfg.output_root / "定妆照"
    bases = sorted(base_dir.rglob("*.png")) if base_dir.exists() else []
    if not bases:
        print("  （无。先 candidates 出候选 → pick 锁基准）")
    for p in bases:
        print(f"  ✅ {p.relative_to(base_dir)}  ({p.stat().st_size // 1024} KB)")

    print(f"\n== 候选批次（{cfg.output_root / '候选'}）==")
    cand_dir = cfg.output_root / "候选"
    runs = sorted(cand_dir.iterdir()) if cand_dir.exists() else []
    if not runs:
        print("  （无）")
    for d in runs:
        imgs = sorted(d.glob("*.png"))
        print(f"  · {d.name}: {len(imgs)} 张候选")

    print(f"\n== 衍生（{cfg.output_root / '三视图'} / {cfg.output_root / '栏目图'}）==")
    any_der = False
    for root in (cfg.output_root / "三视图", cfg.output_root / "栏目图"):
        if not root.exists():
            continue
        for sub in sorted(root.iterdir()):
            imgs = sorted(sub.rglob("*.png"))
            if imgs:
                any_der = True
                print(f"  · {root.name}/{sub.name}: {len(imgs)} 张")
    if not any_der:
        print("  （无。有基准图后 derive 出衍生）")

    print(f"\n== 视频（{cfg.output_root / '视频'}）==")
    vid_dir = cfg.output_root / "视频"
    any_vid = False
    if vid_dir.exists():
        for sub in sorted(vid_dir.iterdir()):
            mp4s = sorted(sub.rglob("*.mp4"))
            if mp4s:
                any_vid = True
                print(f"  · {sub.name}: {len(mp4s)} 支视频")
    if not any_vid:
        print("  （无。有基准图后：montage 图集合成 或 video 图生视频）")

    print(f"\n== 拒图（{cfg.output_root / '拒图'}）==")
    rej_dir = cfg.output_root / "拒图"
    rejs = sorted(rej_dir.rglob("*.png")) + sorted(rej_dir.rglob("*.mp4")) if rej_dir.exists() else []
    print("  无" if not rejs else f"  {len(rejs)} 个文件，人工复核后定去留")
    return 0


# ---------------------------------------------------------------- 注册
def register(sub) -> None:
    p_cand = sub.add_parser("candidates", help="选型：出 N 张候选")
    p_cand.add_argument("--prompt", required=True, help="完整提示词（黄金公式）")
    p_cand.add_argument("--n", type=int, default=4, help="候选张数（默认 4）")
    p_cand.add_argument("--tag", default="candidate", help="批次 tag，如 形象A / 深夜爵士")
    p_cand.add_argument("--seed", type=int, default=None, help="首种子（不传则随机）")
    p_cand.add_argument("--dry-run", action="store_true", help="只预览，不调用 API")
    p_cand.set_defaults(fn=cmd_candidates)

    p_pick = sub.add_parser("pick", help="确认：锁基准图")
    p_pick.add_argument("target", help="候选文件路径；或候选目录（此时再给 <文件>）")
    p_pick.add_argument("file", nargs="?", default=None, help="候选文件名（target 为目录时必填）")
    p_pick.add_argument("--name", default=None, help="基准图命名（默认取文件主干名）")
    p_pick.set_defaults(fn=cmd_pick)

    p_der = sub.add_parser("derive", help="衍生：以基准图图生图 + 人不变校验")
    p_der.add_argument("--base", required=True, help="基准图路径（如 <工作区>/qianmian-yujie-render/定妆照/<形象>/<形象>.png）")
    p_der.add_argument("--prompt", required=True, help="衍生提示词（只动服装/姿势/场景/质量）")
    p_der.add_argument("--n", type=int, default=1, help="衍生张数（默认 1）")
    p_der.add_argument("--tag", default="derive", help="衍生 tag，如 女仆装 / 三视图 / 霓虹风")
    p_der.add_argument("--kind", choices=["三视图", "栏目图"], default="栏目图",
                       help="产物类型：三视图 → 三视图/<形象>/；栏目图（默认）→ 栏目图/<tag>/")
    p_der.add_argument("--seed", type=int, default=None, help="首种子")
    p_der.add_argument("--no-validate", action="store_true",
                       help="跳过人脸校验（三视图背面等本就没脸的镜头）")
    p_der.add_argument("--dry-run", action="store_true", help="只预览，不调用 API")
    p_der.set_defaults(fn=cmd_derive)

    p_st = sub.add_parser("status", help="查看已出图/视频清单")
    p_st.set_defaults(fn=cmd_status)
