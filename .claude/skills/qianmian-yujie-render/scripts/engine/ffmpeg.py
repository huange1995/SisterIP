# -*- coding: utf-8 -*-
"""ffmpeg 封装（自包含，可共享）：基于 imageio-ffmpeg 自带的静态二进制，不依赖系统 ffmpeg。

设计：
- 统一「构造参数列表 + run() 执行」模式；失败抛 FFmpegError（附 stderr 尾部）。
- 所有滤镜走 filter_complex、用 [i] 索引引用输入，**路径不进滤镜字符串**，
  中文/空格路径天然安全（subprocess list 参数，无 shell 转义）。
- 成片统一画幅：不同源 clip（montage 1080x1920 / seedance 720p）先 scale+pad 归一再拼接。
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from engine.errors import FFmpegError


def ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:
        raise FFmpegError(f"找不到 ffmpeg 二进制：{e}（先 pip install imageio-ffmpeg）")


def run(args: list[str]) -> str:
    """执行 ffmpeg，成功返回 stdout；失败抛 FFmpegError（附 stderr 尾部）。"""
    proc = subprocess.run(
        [ffmpeg_exe(), *args], capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()[-6:]
        raise FFmpegError("ffmpeg 执行失败:\n" + "\n".join(tail))
    return proc.stdout


def probe_duration(path: Path) -> float:
    """返回媒体时长（秒）；探测失败返回 0.0。ffmpeg -i 的 Duration 行在 stderr。"""
    proc = subprocess.run(
        [ffmpeg_exe(), "-i", str(path)], capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", proc.stderr)
    if not m:
        return 0.0
    h, mn, s = m.groups()
    return int(h) * 3600 + int(mn) * 60 + float(s)


def _parse_size(size: str) -> tuple[int, int]:
    try:
        w, h = (int(v) for v in size.lower().split("x"))
    except ValueError:
        raise FFmpegError(f"无效画幅: {size}（应为 宽x高，如 1080x1920）")
    return w, h


def _pad_scale_chain(idx: int, w: int, h: int, fps: int) -> str:
    """把第 idx 路输入归一为 w x h、fps 的 clip：等比缩放→黑边补全→固定比例/帧率。"""
    return (
        f"[{idx}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}[v{idx}]"
    )


def normalize_clip(video: Path, out: Path, *, size: str, fps: int) -> Path:
    """单段视频转码归一（画幅/fps/h264/yuv420p），供拼接或成片用。"""
    w, h = _parse_size(size)
    run([
        "-i", str(video),
        "-filter_complex", _pad_scale_chain(0, w, h, fps),
        "-map", "[v0]", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", str(fps), "-y", str(out),
    ])
    return out


def concat_clips(clips: list[Path], out: Path, *, size: str, fps: int) -> Path:
    """按序拼接若干 clip 为统一画幅成片（自动归一不同尺寸的输入）。

    单段也走 normalize_clip，保证产物画幅/编码与多段一致。
    """
    clips = [Path(c) for c in clips]
    if len(clips) == 1:
        return normalize_clip(clips[0], out, size=size, fps=fps)

    w, h = _parse_size(size)
    n = len(clips)
    fc = "".join(_pad_scale_chain(i, w, h, fps) + ";" for i in range(n))
    fc += "".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[outv]"

    args: list[str] = []
    for c in clips:
        args += ["-i", str(c)]
    args += [
        "-filter_complex", fc,
        "-map", "[outv]", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", str(fps), "-y", str(out),
    ]
    run(args)
    return out


def mix_tracks(tracks: list[dict], out: Path, *, normalize: bool = False) -> Path:
    """把多路音频轨按序混合为 .m4a（AAC 192k）。

    tracks 每项：{"path": Path|str, "delay": 秒(相对视频起点),
                  "volume": 音量(1.0), "fade_in": 秒, "fade_out": 秒}
    每路先统一立体声（aformat），再 adelay 对齐、volume 调音量、afade 淡入淡出，
    最后 amix 混合（默认 normalize=0，避免整体音量忽大忽小）。
    """
    tracks = [dict(t) for t in tracks]
    if not tracks:
        raise FFmpegError("混音输入为空")
    n = len(tracks)
    args: list[str] = []
    for t in tracks:
        args += ["-i", str(t["path"])]

    fc = []
    for i, t in enumerate(tracks):
        delay_ms = int(float(t.get("delay", 0.0)) * 1000)
        chain = (
            f"[{i}:a]aformat=channel_layouts=stereo,"
            f"adelay={delay_ms}:all=1,volume={float(t.get('volume', 1.0))}"
        )
        fin = float(t.get("fade_in", 0.0))
        fout = float(t.get("fade_out", 0.0))
        if fout > 0:
            dur = probe_duration(t["path"])
            st = max(0.0, dur - fout)
            chain += f",afade=t=in:st=0:d={fin},afade=t=out:st={st:.3f}:d={fout}"
        elif fin > 0:
            chain += f",afade=t=in:st=0:d={fin}"
        fc.append(chain + f"[a{i}];")
    fc.append(
        "".join(f"[a{i}]" for i in range(n))
        + f"amix=inputs={n}:duration=longest:normalize={1 if normalize else 0}[outa]"
    )
    args += [
        "-filter_complex", "".join(fc),
        "-map", "[outa]", "-c:a", "aac", "-b:a", "192k", "-y", str(out),
    ]
    run(args)
    return out


def mux(video: Path, audio: Path, out: Path) -> Path:
    """视频 + 音频轨 → 成片 mp4（视频流 copy 不重编码，音频转 AAC，以视频长度为准）。"""
    run([
        "-i", str(video), "-i", str(audio),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-y", str(out),
    ])
    return out


def overlay_card(video: Path, card_png: Path, out: Path, *, x: int, y: int) -> Path:
    """在视频上盖一张透明字卡 PNG（seedance 片补字幕用；montage 帧在渲染时已烧字）。"""
    fc = f"[1:v]format=rgba[o];[0:v][o]overlay=x={x}:y={y}[v]"
    run([
        "-i", str(video), "-loop", "1", "-i", str(card_png),
        "-filter_complex", fc,
        "-map", "[v]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "copy", "-y", str(out),
    ])
    return out
