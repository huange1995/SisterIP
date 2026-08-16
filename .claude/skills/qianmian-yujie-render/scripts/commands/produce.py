# -*- coding: utf-8 -*-
"""企划子命令：produce —— 企划书 → 创意预览 / 逐镜prompt / 渲染契约（策划层）。

三层骨架的「① 策划层」入口。企划书 = 创意产物（AI 编辑生成 + 手工可精修），
本命令把它**纯本地零 API** 展开成导演层能消费的东西：
- --dry-run   创意预览（文案/镜头/音乐/连贯）——评审用
- --prompts   逐镜完整 image/seedance prompt（黄金公式）——审查提示词
- --emit      展开成渲染契约 shotlist.json → 交给 compose 执行
- --inventory 列出形象库可用资产（服装集/定妆照/曲目）——编辑找料用
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import planning
from config import Config
from pipeline import is_image

INVENTORY_HINT = (
    "策划案是 JSON 文件，schema 见 references/策划/01-策划.md 与 planning.py 文档"
)


def _inventory(cfg: Config) -> str:
    """列出形象库可用资产：栏目图/服装集、定妆照/角色、音乐库/曲目。"""
    root = cfg.output_root
    L = [f"形象库（{root}）："]
    outfits = sorted(p for p in (root / "栏目图").iterdir() if p.is_dir()) \
        if (root / "栏目图").is_dir() else []
    L.append("  服装集（栏目图/）：" + ("、".join(p.name for p in outfits) or "（无）"))
    chars = sorted(p for p in (root / "定妆照").iterdir() if p.is_dir()) \
        if (root / "定妆照").is_dir() else []
    L.append("  角色（定妆照/）：" + ("、".join(p.name for p in chars) or "（无）"))
    bgm = sorted(p.name for p in Path(cfg.bgm_dir).iterdir()
                 if p.is_file() and p.suffix.lower() in (".mp3", ".wav", ".m4a", ".flac")) \
        if cfg.bgm_dir and Path(cfg.bgm_dir).is_dir() else []
    L.append("  曲目（音乐库/）：" + ("、".join(bgm) or "（无）"))
    return "\n".join(L)


def _prompts_text(plan: dict) -> str:
    L = [f"逐镜 prompt「{plan['title']}」："]
    for sh in plan["shots"]:
        L.append(f"  [{sh['id']}] {sh['src']}：")
        L.append(f"    设计: {planning.build_design_prompt(plan, sh)}")
        if sh["src"] == "seedance":
            action, ff = planning.build_seedance_prompts(plan, sh)
            L.append(f"    动作: {action}")
            L.append(f"    首帧: {ff}")
    return "\n".join(L)


def cmd_produce(args, cfg) -> int:
    if args.inventory:
        print(_inventory(cfg))
        return 0
    if not args.brief:
        print(f"错误：需要 --brief <企划书.json>（或 --inventory）\n{INVENTORY_HINT}")
        return 2
    brief_path = Path(args.brief)
    if not brief_path.is_file():
        print(f"错误：企划书不存在: {brief_path}\n{INVENTORY_HINT}")
        return 2
    try:
        plan = planning.parse(json.loads(brief_path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, planning.BriefError) as e:
        print(f"错误：企划书不合法 —— {e}\n{INVENTORY_HINT}")
        return 2

    if args.prompts:
        print(_prompts_text(plan))
        return 0
    if args.emit:
        contract = planning.expand_contract(plan)
        out = Path(args.emit)
        out.write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
        n = len(contract["scenes"])
        seed = sum(1 for s in contract["scenes"] if s["src"] == "seedance")
        print(f"渲染契约 → {out}（{n} 镜，其中 seedance {seed} 镜；"
              f"{'含统一调色 grade' if contract.get('grade') else '无 grade'}）")
        print("下一步：compose --script <该契约> 出片")
        return 0
    print(planning.creative_preview(plan))
    return 0


def register(sub) -> None:
    p = sub.add_parser("produce", help="企划：企划书 → 创意预览 / 逐镜prompt / 渲染契约（纯本地零 API）")
    p.add_argument("--brief", metavar="企划书.json", help="企划书 JSON 路径（--inventory 时忽略）")
    p.add_argument("--dry-run", action="store_true", help="打印创意预览（文案/镜头/音乐/连贯）")
    p.add_argument("--prompts", action="store_true", help="打印逐镜完整 prompt（黄金公式）")
    p.add_argument("--emit", metavar="渲染契约.json", help="展开企划书 → 渲染契约 shotlist.json")
    p.add_argument("--inventory", action="store_true", help="列出形象库可用资产（服装集/定妆照/曲目）")
    p.set_defaults(fn=cmd_produce)
