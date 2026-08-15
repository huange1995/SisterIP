# -*- coding: utf-8 -*-
"""音频轨（自包含，可共享）：BGM 曲库解析 + 旁白轨 + 混音调度。

compose 用它把 shotlist 的 audio 段翻译成 engine.ffmpeg.mix_tracks 的输入：
- resolve_bgm()      ：显式路径 / 文件名 / QYJ_BGM_DIR 曲库扫描 → Path 或 None
- voiceover_track()  ：TTS 合成一段旁白 mp3 → 轨描述（含 delay=该镜起始秒）
- build_mix()        ：零轨返回 None（保持纯视频）；单轨无特效直接用；多轨 amix
"""

from __future__ import annotations

from pathlib import Path

from config import Config
from engine import ffmpeg
from engine.errors import TTSUnavailableError
from engine.tts import TTSClient

AUDIO_EXTS = frozenset({".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg"})


def resolve_bgm(cfg: Config, spec: str | None) -> Path | None:
    """解析 BGM：spec 可为显式路径或文件名；未命中/未给则扫 QYJ_BGM_DIR 曲库。"""
    if spec:
        p = Path(spec)
        if p.is_file():
            return p
        if cfg.bgm_dir:
            cand = Path(cfg.bgm_dir) / p
            if cand.is_file():
                return cand
            for f in sorted(Path(cfg.bgm_dir).iterdir()):
                if f.is_file() and f.stem == p.stem and f.suffix.lower() in AUDIO_EXTS:
                    return f
    if cfg.bgm_dir:
        files = sorted(
            f for f in Path(cfg.bgm_dir).iterdir()
            if f.is_file() and f.suffix.lower() in AUDIO_EXTS
        )
        if files:
            return files[0]
    return None


def voiceover_track(cfg: Config, tts: TTSClient, text: str, out_dir: Path,
                    *, start_sec: float, label: str) -> dict | None:
    """合成一段旁白 mp3 到 out_dir 并返回轨描述；TTS 不可用返回 None 并警告。"""
    out = Path(out_dir) / f"voice-{label}.mp3"
    try:
        tts.synthesize(text, out)
    except TTSUnavailableError as e:
        print(f"    ⚠ 旁白「{label}」跳过: {e}")
        return None
    print(f"    ✅ 旁白「{label}」→ {out.name}")
    return {"path": out, "delay": start_sec, "volume": cfg.voice_volume}


def build_mix(cfg: Config, tracks: list[dict], out_dir: Path,
              *, normalize: bool | None = None) -> Path | None:
    """把轨列表混音为 .m4a；零轨 → None（保持纯视频）。

    单轨且无 delay/fade 时直接复用原文件（避免无谓重编码）；
    否则走 engine.ffmpeg.mix_tracks（应用 adelay/volume/fade）。
    """
    if not tracks:
        return None
    only = tracks[0]
    if len(tracks) == 1 and not any(only.get(k) for k in ("delay", "fade_in", "fade_out")):
        return Path(only["path"])
    out = Path(out_dir) / "audio.m4a"
    ffmpeg.mix_tracks(tracks, out, normalize=cfg.mix_normalize if normalize is None else normalize)
    return out
