# -*- coding: utf-8 -*-
"""Seedance 视频生成引擎 —— 异步两段式（自包含，可共享）。

已核实的接口事实（2026-08，火山方舟 ark.cn-beijing.volces.com）：
- 提交：POST {video_api_base}，body={model, content:[{type:text,text:...},{type:image_url,image_url:{url, role:first_frame}}]}
- 轮询：GET {video_api_base}/{task_id}，status ∈ queued/running/succeeded/failed/expired
- 成功：content.video_url（MP4），24h 内必须下载，过期 403
- 图生视频建议 --ratio 跟随首帧比例；本技能默认 9:16，首帧已按 9:16 准备
- 文本参数（拼进 text）：--duration 4-15 --ratio 9:16 --resolution 720p --watermark false
- 多镜头（2.0）：prompt 里用 "Shot 1: ... / Shot 2: ..."（或【时间轴】0-3s: ...）即可单次生成 2-3 镜
- 接龙：content 里加 video_url 元素 role=last_frame，用上一段尾帧续接
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from config import Config
from engine.ark import ArkClientBase, to_data_uri
from engine.errors import FatalError, GeneratorError, RetryableError


class SeedanceClient(ArkClientBase):
    def __init__(self, cfg: Config):
        super().__init__(cfg, service_name="视频")

    # ------------------------------------------------------------ 提交任务
    def create_task(self, prompt: str, first_frame: Path, model: str,
                    duration: int, ratio: str, resolution: str,
                    watermark: bool = False, *,
                    last_frame: Path | None = None,
                    json_extra: dict | None = None) -> dict:
        """提交图生视频任务，返回 {"id": task_id}。

        duration 传 -1 表示 auto（让模型按内容自定时长，多镜头常用）。
        last_frame：可选接龙尾帧（上一段视频的最后一帧图），续接下一镜头。
        json_extra：可选透传的顶层字段（如 {"generate_audio": True}），扩展用。
        """
        params = f" --duration {duration} --ratio {ratio} --resolution {resolution}"
        if not watermark:
            params += " --watermark false"
        first_url = to_data_uri(first_frame)

        def _build(use_role: bool) -> dict:
            img = {"url": first_url}
            if use_role:
                img["role"] = "first_frame"
            content = [
                {"type": "text", "text": prompt + params},
                {"type": "image_url", "image_url": img},
            ]
            if last_frame is not None:
                content.append({
                    "type": "video_url",
                    "video_url": {"url": to_data_uri(last_frame), "role": "last_frame"},
                })
            payload = {"model": model, "content": content}
            if json_extra:
                payload.update(json_extra)
            return payload

        # 2.0 用 role=first_frame；若该模型不认 role，400 报错会带 role → 去掉重试一次
        last: GeneratorError | None = None
        for use_role in (True, False):
            resp = self._post(self.cfg.video_api_base, _build(use_role))
            if resp.status_code == 200:
                data = resp.json()
                task_id = data.get("id")
                if not task_id:
                    raise FatalError(f"响应无 task id: {resp.text[:300]}")
                return {"id": task_id, "raw": data}
            err = self._classify(resp, model_kind="视频模型")
            if resp.status_code == 400 and "role" in resp.text:
                last = err
                continue
            raise err
        raise last or FatalError("创建视频任务失败")

    # ------------------------------------------------------------ 轮询
    def poll_task(self, task_id: str, interval: float | None = None,
                  max_wait: float | None = None) -> dict:
        """轮询任务直到 succeeded；failed/expired/超时抛错。成功返回任务数据。"""
        cfg = self.cfg
        interval = interval or cfg.video_poll_interval
        max_wait = max_wait or cfg.video_poll_max
        url = f"{cfg.video_api_base.rstrip('/')}/{task_id}"
        start = time.monotonic()
        while True:
            resp = self._get(url)
            if resp.status_code != 200:
                raise self._classify(resp, model_kind="视频模型")
            data = resp.json()
            status = data.get("status", "unknown")
            if status == "succeeded":
                return data
            if status in ("failed", "error", "expired"):
                detail = ""
                content = data.get("content")
                if isinstance(content, dict):
                    detail = content.get("description") or content.get("error") or ""
                detail = detail or data.get("message") or data.get("error") or ""
                raise GeneratorError(f"视频生成失败 status={status}：{detail}")
            if time.monotonic() - start > max_wait:
                raise GeneratorError(
                    f"轮询超时（>{max_wait:.0f}s）。任务可能仍在进行，task_id={task_id}"
                )
            time.sleep(interval)

    # ------------------------------------------------------------ 取址 / 下载
    @staticmethod
    def video_url(data: dict) -> str:
        """从成功任务响应里取 MP4 下载地址。"""
        content = data.get("content")
        if isinstance(content, dict):
            for key in ("video_url", "video"):
                if content.get(key):
                    return str(content[key])
        for key in ("video_url", "url"):
            if data.get(key):
                return str(data[key])
        raise FatalError(f"任务成功但无视频 URL: {json.dumps(data, ensure_ascii=False)[:300]}")

    def download_video(self, video_url: str, dest: Path) -> None:
        """下载 MP4 到 dest。URL 24h 后过期。"""
        resp = self.session.get(video_url, timeout=self.cfg.video_download_timeout)
        if resp.status_code != 200:
            raise GeneratorError(
                f"下载视频失败 HTTP {resp.status_code}（URL 24h 后过期，请尽早下载）"
            )
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        Path(dest).write_bytes(resp.content)
