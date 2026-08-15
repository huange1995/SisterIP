# -*- coding: utf-8 -*-
"""产物归档（自包含，可共享）：桶路径 + 命名 + 写入，全部单点维护。

语义桶（对齐 references/产物.md，新增产物类型只需在此登记 + 更新产物.md）：
  候选/<tag>-<时间戳>/       选型候选批次
  定妆照/<形象>/<形象>.png   锁定的基准图
  三视图/<形象>/<tag>-NN.png  三视图衍生
  栏目图/<tag>/<tag>-NN.png   栏目/换装/换风格衍生
  拒图/<kind>/…               未过人不变校验（串味/无脸）
  视频/<tag>-<时间戳>/        视频产物（montage/video/compose 成片）
  作品集/                    成品精选（人工整理，脚本不写）

所有路径都以 cfg.output_root 为根；分享给谁、产物就落在谁的工作区。
命名模板集中在此，命令内不再手写文件名。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def bucket(cfg, kind: str, *parts: str) -> Path:
    """产物桶路径：<output_root>/<kind>/<parts...>。"""
    return cfg.output_root.joinpath(kind, *parts)


# ---------------------------------------------------------------- 批次目录
def run_dir(cfg, kind: str, tag: str, ts: str | None = None) -> Path:
    """带时间戳的批次目录：<kind>/<tag>-<时间戳>/。"""
    return bucket(cfg, kind, f"{tag}-{ts or stamp()}")


def video_run(cfg, tag: str, ts: str | None = None) -> Path:
    """视频批次目录：视频/<tag>-<时间戳>/（montage / video / compose 共用）。"""
    return run_dir(cfg, "视频", tag, ts)


def reject_dir(cfg, kind: str, *parts: str) -> Path:
    """拒图桶：拒图/<kind>/<parts...>。kind 用产物类型（栏目图/视频/成片）。"""
    return bucket(cfg, "拒图", kind, *parts)


# ---------------------------------------------------------------- 命名模板（集中维护）
def candidate_name(i: int) -> str:
    return f"candidate-{i:02d}.png"


def derive_name(tag: str, i: int) -> str:
    return f"{tag}-{i:02d}.png"


def firstframe_name(mode: str) -> str:
    return "firstframe.jpg" if mode == "crop" else "firstframe.png"


def check_name(frac: float) -> str:
    return f"check-{int(frac * 100):02d}.png"


def montage_name(tag: str) -> str:
    return f"{tag}-montage.mp4"


def video_name(tag: str, i: int) -> str:
    return f"{tag}-{i:02d}.mp4"


def compose_name(title: str) -> str:
    return f"{title}.mp4"


def subtitle_name() -> str:
    return "subtitle.srt"


def manifest_name() -> str:
    return "manifest.json"


# ---------------------------------------------------------------- 写入
def write(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def write_json(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
