# -*- coding: utf-8 -*-
"""技能自带配置（自包含，可共享）。

所有参数默认值内置；除 ARK_API_KEY 外，均可通过环境变量 / .env 覆盖：
  ARK_API_KEY             必填，火山方舟密钥
  ARK_BASE_URL            默认 https://ark.cn-beijing.volces.com/api/v3/images/generations
  ARK_MODEL               默认 doubao-seedream-5-0-lite-260128（开通的是别的模型就设这个）
  ARK_VIDEO_MODEL         默认 doubao-seedance-2-0-260128（视频模型，未开通则回退 1.0-lite-i2v）
  ARK_VIDEO_RATIO         默认 9:16（视频比例）
  ARK_VIDEO_RESOLUTION    默认 720p（视频分辨率）
  ARK_FIRSTFRAME_MODE     默认 derive（首帧方式：derive | crop）
  QYJ_OUTPUT_DIR          默认 <工作区>/qianmian-yujie-render（产物根目录，可重定向）
  INSIGHTFACE_PROVIDER    默认 cpu（cpu | auto | cuda）
  INSIGHTFACE_ROOT        默认空 → insightface 自动下载 buffalo_l 到 ~/.insightface；
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


def _env(name: str, default: str) -> str:
    """读环境变量；空串视为未设，回落默认。"""
    v = os.environ.get(name)
    return v.strip() if v else default


def _detect_insightface_root() -> str:
    """未设 INSIGHTFACE_ROOT 时，自动探测工作区已有的 buffalo_l 模型。

    insightface 布局是 {root}/models/{name}/；仓库常见布局是
    <工作区>/models/buffalo_l/ → root 应指到 <工作区>。命中即返回，未命中返回空串
    （回落到 insightface 自动下载到 ~/.insightface）。
    """
    for cand in (WORKSPACE_ROOT, WORKSPACE_ROOT.parent):
        if (cand / "models" / "buffalo_l").is_dir():
            return str(cand)
    return ""


@dataclass
class Config:
    api_key: str
    base_url: str
    model: str
    timeout: int = 120
    max_retries: int = 3
    retry_backoff: float = 2.0
    size: str = "2048x2048"          # 5.0-lite 最小要求约 1920x1920（3.69MP），1K 会被 400 拒
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

    # ---- 视频（Seedance 图生视频，异步两段式）----
    video_api_base: str = "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"
    video_model: str = "doubao-seedance-2-0-260128"
    video_fallback_model: str = "doubao-seedance-1-0-lite-i2v-250428"
    video_duration: int = 5          # 秒，API 支持 4–15
    video_ratio: str = "9:16"
    video_resolution: str = "720p"   # 图生视频 1080p 不支持参考图场景，720p 稳妥
    video_watermark: bool = False
    video_poll_interval: float = 10.0
    video_poll_max: float = 900.0    # 单任务轮询上限（秒）
    video_download_timeout: int = 120
    firstframe_mode: str = "derive"  # derive=Seedream 竖版衍生(构图完整, 需 ff-prompt) | crop=中心裁剪(零成本)
    firstframe_size: str = "1440x2560"  # 9:16 竖版（Seedream derive 首帧用）
    price_per_video_second: float = 1.0  # ¥/秒成本估算（720p；开通后以实际计费为准）

    # ---- 合成（montage，图集 → 视频）----
    montage_fps: int = 24
    montage_per_image: float = 2.5   # 每张停留秒数
    montage_zoom: float = 0.06       # Ken Burns 推近/拉远幅度
    montage_fade: float = 0.8        # 交叉淡入淡出时长（秒）
    montage_width: int = 1080
    montage_height: int = 1920       # 9:16 竖版


def load_config() -> Config:
    return Config(
        api_key=os.environ.get("ARK_API_KEY", "").strip(),
        base_url=_env("ARK_BASE_URL",
                      "https://ark.cn-beijing.volces.com/api/v3/images/generations"),
        model=_env("ARK_MODEL", "doubao-seedream-5-0-lite-260128"),
        provider=_env("INSIGHTFACE_PROVIDER", "cpu"),
        insightface_root=os.environ.get("INSIGHTFACE_ROOT", "").strip()
        or _detect_insightface_root(),
        video_model=_env("ARK_VIDEO_MODEL", "doubao-seedance-2-0-260128"),
        video_ratio=_env("ARK_VIDEO_RATIO", "9:16"),
        video_resolution=_env("ARK_VIDEO_RESOLUTION", "720p"),
        firstframe_mode=_env("ARK_FIRSTFRAME_MODE", "derive"),
    )
