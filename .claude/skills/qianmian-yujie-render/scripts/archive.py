# -*- coding: utf-8 -*-
"""产物归档（自包含，可共享）：桶路径 + 命名 + 写入，全部单点维护。

语义桶（对齐 references/产物.md，新增产物类型只需在此登记 + 更新产物.md）：
  候选/<tag>-<时间戳>/      选型候选批次
  定妆照/<形象>/<形象>.png   锁定的基准图
  三视图/<形象>/<tag>-NN.png  三视图衍生
  栏目图/<tag>/<tag>-NN.png   栏目/换装/换风格衍生
  拒图/…                     未过人不变校验（串味/无脸）
  视频/<tag>-<时间戳>/       视频产物（视频/首帧/抽帧校验图/清单）
  作品集/                    成品精选（人工整理，脚本不写）

所有路径都以 cfg.output_root 为根；分享给谁、产物就落在谁的工作区。
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


def write(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def write_json(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
