# -*- coding: utf-8 -*-
"""技能自带配置（自包含，可共享）。

设计原则：
- **Config dataclass 默认值是唯一真源**；load_config() 用 ENV_MAP 全量覆盖，
  不再在 dataclass 与 load_config 里各写一份默认值（旧版双写易漏）。
- 除 ARK_API_KEY 外，**所有字段均可通过环境变量 / .env 覆盖**，字段名→env 见 ENV_MAP。
- output_root 在 load_config() 内求值（QYJ_OUTPUT_DIR），保证 .env 加载后生效。
- 产物存放原则：产物属于用户作品，放用户工作区，不进技能包。
  工作区 = 技能目录上溯 3 层（<工作区>/.claude/skills/qianmian-yujie-render/）。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, fields
from pathlib import Path

# 技能根：.claude/skills/qianmian-yujie-render/
SKILL_ROOT = Path(__file__).resolve().parent.parent
# 用户工作区：skill 所在 <工作区>/.claude/skills/<name>/ 上溯 3 层
WORKSPACE_ROOT = SKILL_ROOT.parents[2]

# 方舟图片 / 视频端点与模型默认值（集中在顶部，便于改）
_IMAGE_URL = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
_IMAGE_MODEL = "doubao-seedream-5-0-lite-260128"
_VIDEO_URL = "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"
_VIDEO_MODEL = "doubao-seedance-2-0-260128"
_VIDEO_FALLBACK = "doubao-seedance-1-0-lite-i2v-250428"


def _env(name: str, default: str) -> str:
    """读环境变量；空串视为未设，回落默认。"""
    v = os.environ.get(name)
    return v.strip() if v else default


def _coerce(name: str, raw: str, typ: str):
    """把环境变量字符串转成字段类型；解析失败打印警告并回落默认。"""
    try:
        if typ == "bool":
            return raw.strip().lower() in ("1", "true", "yes", "on")
        if typ == "int":
            return int(raw.strip())
        if typ == "float":
            return float(raw.strip())
        if typ == "Path":
            return Path(raw.strip())
        return raw
    except ValueError:
        print(f"⚠  环境变量 {name} 解析失败，忽略该值: {raw}")
        return None


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


# 字段名 → 环境变量。不在这里的字段（skill_root/workspace_root 等）保持默认值。
ENV_MAP = {
    # 图片 / 通用
    "base_url": "ARK_BASE_URL",
    "model": "ARK_MODEL",
    "timeout": "ARK_TIMEOUT",
    "max_retries": "ARK_MAX_RETRIES",
    "retry_backoff": "ARK_RETRY_BACKOFF",
    "size": "ARK_SIZE",
    "watermark": "ARK_WATERMARK",
    "response_format": "ARK_RESPONSE_FORMAT",
    "n": "ARK_N",
    "threshold_pass": "INSIGHTFACE_PASS",
    "threshold_warn": "INSIGHTFACE_WARN",
    "price_per_image": "ARK_PRICE_PER_IMAGE",
    "provider": "INSIGHTFACE_PROVIDER",
    # 视频
    "video_api_base": "ARK_VIDEO_API_BASE",
    "video_model": "ARK_VIDEO_MODEL",
    "video_fallback_model": "ARK_VIDEO_FALLBACK_MODEL",
    "video_duration": "ARK_VIDEO_DURATION",
    "video_ratio": "ARK_VIDEO_RATIO",
    "video_resolution": "ARK_VIDEO_RESOLUTION",
    "video_watermark": "ARK_VIDEO_WATERMARK",
    "video_poll_interval": "ARK_VIDEO_POLL_INTERVAL",
    "video_poll_max": "ARK_VIDEO_POLL_MAX",
    "video_download_timeout": "ARK_VIDEO_DOWNLOAD_TIMEOUT",
    "firstframe_mode": "ARK_FIRSTFRAME_MODE",
    "firstframe_ratio": "ARK_FIRSTFRAME_RATIO",
    "firstframe_size": "ARK_FIRSTFRAME_SIZE",
    "price_per_video_second": "ARK_PRICE_PER_VIDEO_SECOND",
    # 合成 montage
    "montage_fps": "MONTAGE_FPS",
    "montage_per_image": "MONTAGE_PER_IMAGE",
    "montage_zoom": "MONTAGE_ZOOM",
    "montage_fade": "MONTAGE_FADE",
    "montage_width": "MONTAGE_WIDTH",
    "montage_height": "MONTAGE_HEIGHT",
    # 音频（BGM + 火山 TTS）
    "tts_appid": "ARK_TTS_APPID",
    "tts_token": "ARK_TTS_TOKEN",
    "tts_cluster": "ARK_TTS_CLUSTER",
    "tts_voice": "ARK_TTS_VOICE",
    "tts_speed_ratio": "ARK_TTS_SPEED",
    "tts_volume_ratio": "ARK_TTS_VOLUME",
    "tts_timeout": "ARK_TTS_TIMEOUT",
    "bgm_dir": "QYJ_BGM_DIR",
    "bgm_volume": "QYJ_BGM_VOLUME",
    "bgm_fade": "QYJ_BGM_FADE",
    "voice_volume": "QYJ_VOICE_VOLUME",
    "mix_normalize": "QYJ_MIX_NORMALIZE",
    # 字幕
    "subtitle_font": "QYJ_SUBTITLE_FONT",
    "subtitle_size": "QYJ_SUBTITLE_SIZE",
    "subtitle_bottom": "QYJ_SUBTITLE_BOTTOM",
    "subtitle_bg_alpha": "QYJ_SUBTITLE_BG_ALPHA",
    "subtitle_max_width_ratio": "QYJ_SUBTITLE_MAX_WIDTH_RATIO",
    # 成片 compose
    "compose_temp": "QYJ_COMPOSE_TEMP",
}


@dataclass
class Config:
    # ---- 图片 / 通用 ----
    api_key: str = ""                      # 火山方舟密钥（必填）
    base_url: str = _IMAGE_URL
    model: str = _IMAGE_MODEL
    timeout: int = 120
    max_retries: int = 3
    retry_backoff: float = 2.0
    size: str = "2048x2048"                # 5.0-lite 最小要求约 1920x1920（3.69MP），1K 会被 400 拒
    watermark: bool = False
    response_format: str = "b64_json"
    n: int = 1
    threshold_pass: float = 0.45           # 人不变相似度 ≥ 此值 → 归档
    threshold_warn: float = 0.35           # < 此值 → 串味进 rejected；中间 → 存疑待人工
    price_per_image: float = 0.25          # ¥/张，仅供成本预估
    provider: str = "cpu"
    insightface_root: str = ""             # 空 → insightface 自动下载到 ~/.insightface
    skill_root: Path = SKILL_ROOT
    workspace_root: Path = WORKSPACE_ROOT
    output_root: Path = WORKSPACE_ROOT / "qianmian-yujie-render"

    # ---- 视频（Seedance 图生视频，异步两段式）----
    video_api_base: str = _VIDEO_URL
    video_model: str = _VIDEO_MODEL
    video_fallback_model: str = _VIDEO_FALLBACK
    video_duration: int = 5                # 秒，API 支持 4–15
    video_ratio: str = "9:16"
    video_resolution: str = "720p"         # 图生视频 1080p 不支持参考图场景，720p 稳妥
    video_watermark: bool = False
    video_poll_interval: float = 10.0
    video_poll_max: float = 900.0          # 单任务轮询上限（秒）
    video_download_timeout: int = 120
    firstframe_mode: str = "derive"        # derive=Seedream 竖版衍生(构图完整, 需 ff-prompt) | crop=中心裁剪(零成本)
    firstframe_ratio: str = "9:16"         # 首帧目标比例（独立于 montage 画幅）
    firstframe_size: str = "1440x2560"     # Seedream derive 首帧像素（9:16 竖版）
    price_per_video_second: float = 1.0    # ¥/秒成本估算（720p；开通后以实际计费为准）

    # ---- 合成（montage，图集 → 视频）----
    montage_fps: int = 24
    montage_per_image: float = 2.5         # 每张停留秒数
    montage_zoom: float = 0.06             # Ken Burns 推近/拉远幅度
    montage_fade: float = 0.8              # 交叉淡入淡出时长（秒）
    montage_width: int = 1080
    montage_height: int = 1920             # 9:16 竖版

    # ---- 音频（BGM 混音 + 火山 TTS 旁白）----
    tts_appid: str = ""                    # 火山语音 APP ID（开通后填；空 → compose 跳过旁白）
    tts_token: str = ""                    # 火山语音 Access Token（非 ARK key）
    tts_cluster: str = "volcano_tts"
    tts_voice: str = "BV700_streaming"     # 通用女声音色（个人实名可开普通音色）
    tts_speed_ratio: float = 1.0
    tts_volume_ratio: float = 1.0
    tts_timeout: int = 60
    bgm_dir: str = ""                      # 背景音乐曲库目录（QYJ_BGM_DIR，可选）
    bgm_volume: float = 0.5                # BGM 默认音量（相对旁白自动压低）
    bgm_fade: float = 1.0                  # BGM 淡入淡出秒数
    voice_volume: float = 1.0              # 旁白音量
    mix_normalize: bool = False            # amix 是否 normalize（False 更稳，避免整体忽大忽小）

    # ---- 字幕（字卡烧录 + SRT）----
    subtitle_font: str = ""                # 空 → 自动探测 Windows 微软雅黑（C:/Windows/Fonts/msyh.ttc）
    subtitle_size: int = 48                # 字卡字号（9:16 1080 宽）
    subtitle_bottom: int = 120             # 字卡距底边像素
    subtitle_bg_alpha: float = 0.55        # 字卡半透明底不透明度
    subtitle_max_width_ratio: float = 0.86  # 字卡最大宽度占画幅比例

    # ---- 成片 compose ----
    compose_temp: str = ""                 # 中间 clip 临时目录（空 → 系统临时目录）


def load_config() -> Config:
    """构造 Config：默认值打底 + ENV_MAP 全量覆盖 + 特殊项（key/模型根/产物根）。"""
    data: dict = {}
    for f in fields(Config):
        env = ENV_MAP.get(f.name)
        if env and os.environ.get(env):
            val = _coerce(env, os.environ[env], f.type)
            if val is not None:
                data[f.name] = val

    # 特殊项：api_key 必填（空串可，由引擎报错）；insightface_root 自动探测；output_root 支持重定向
    data["api_key"] = os.environ.get("ARK_API_KEY", "").strip()
    data["insightface_root"] = os.environ.get("INSIGHTFACE_ROOT", "").strip() or _detect_insightface_root()
    qyj = os.environ.get("QYJ_OUTPUT_DIR", "").strip()
    if qyj:
        data["output_root"] = Path(qyj)
    return Config(**data)
