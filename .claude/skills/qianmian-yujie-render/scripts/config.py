# -*- coding: utf-8 -*-
"""技能自带配置（自包含，可共享）。

所有参数默认值内置；除 ARK_API_KEY 外，均可通过环境变量 / .env 覆盖：
  ARK_API_KEY      必填，火山方舟密钥
  ARK_BASE_URL     默认 https://ark.cn-beijing.volces.com/api/v3/images/generations
  ARK_MODEL        默认 doubao-seedream-5-0-lite-260128（开通的是别的模型就设这个）
  QYJ_OUTPUT_DIR   默认 <工作区>/qianmian-yujie-render（产物根目录，可重定向）
  INSIGHTFACE_PROVIDER  默认 cpu（cpu | auto | cuda）
  INSIGHTFACE_ROOT      默认空 → insightface 自动下载 buffalo_l 到 ~/.insightface；
                        否则指向含 models/buffalo_l/ 的目录（布局 {root}/models/{name}/）

产物存放原则：**产物属于用户作品，放用户工作区，不进技能包**。
工作区 = 技能目录上溯 3 层（<工作区>/.claude/skills/qianmian-yujie-render/），
分享给谁装进谁的工作区，产物自动落到对方工作区，无需改代码。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# 技能根：.claude/skills/qianmian-yujie-render/
SKILL_ROOT = Path(__file__).resolve().parent.parent
# 用户工作区：skill 所在 <工作区>/.claude/skills/<name>/ 上溯 3 层
WORKSPACE_ROOT = SKILL_ROOT.parents[2]
# 产物根：工作区根下独立目录（不进 assets/），语义桶结构见 references/产物.md
OUTPUT_ROOT = Path(os.environ.get(
    "QYJ_OUTPUT_DIR",
    str(WORKSPACE_ROOT / "qianmian-yujie-render"),
))


@dataclass
class Config:
    api_key: str
    base_url: str
    model: str
    timeout: int = 120
    max_retries: int = 3
    retry_backoff: float = 2.0
    size: str = "2048x2048"          # 5.0-lite 最小要求 1920x1920，1K 会被 400 拒
    watermark: bool = False
    response_format: str = "b64_json"
    n: int = 1
    threshold_pass: float = 0.45     # 人不变相似度 ≥ 此值 → 归档
    threshold_warn: float = 0.35     # < 此值 → 串味进 rejected；中间 → 存疑待人工
    price_per_image: float = 0.25    # ¥/张，仅供成本预估
    provider: str = "cpu"
    insightface_root: str = ""       # 空 → insightface 自动下载到 ~/.insightface
    skill_root: Path = SKILL_ROOT
    workspace_root: Path = WORKSPACE_ROOT
    output_root: Path = OUTPUT_ROOT


def load_config() -> Config:
    return Config(
        api_key=os.environ.get("ARK_API_KEY", "").strip(),
        base_url=os.environ.get(
            "ARK_BASE_URL",
            "https://ark.cn-beijing.volces.com/api/v3/images/generations",
        ).strip(),
        model=os.environ.get("ARK_MODEL", "doubao-seedream-5-0-lite-260128").strip(),
        provider=os.environ.get("INSIGHTFACE_PROVIDER", "cpu").strip(),
        insightface_root=os.environ.get("INSIGHTFACE_ROOT", "").strip(),
    )
