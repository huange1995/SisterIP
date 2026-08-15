# -*- coding: utf-8 -*-
"""Seedream 图片生成引擎（自包含，可共享）。

已核实的接口事实（2026-08，火山方舟 ark.cn-beijing.volces.com）：
- 端点 POST {base_url}，Authorization: Bearer {KEY}，OpenAI Images 兼容
- 参考图本地文件必须转 Data URI（见 engine/ark.to_data_uri）
- 官方无 negative_prompt 字段 → 负面约束已在提示词里拼进文本（SKILL.md 组装阶段完成）
- seed 为遗留参数，新版模型会忽略；此处仅用于跟踪 / 换种重试
- size 支持显式像素（如 2048x2048 / 1440x2560 竖版）；1K（约 1024x1024）会被 400 拒
"""

from __future__ import annotations

import base64
from pathlib import Path

from config import Config
from engine.ark import ArkClientBase
from engine.errors import FatalError, RetryableError


class SeedreamGenerator(ArkClientBase):
    def __init__(self, cfg: Config):
        super().__init__(cfg, service_name="图片")

    def generate_one(self, prompt: str, reference: Path | None = None,
                     seed: int | None = None, size: str | None = None) -> bytes:
        """生成一张图，返回图片 bytes（PNG/JPEG）。

        reference 为基准图路径（图生图）；size 覆盖默认尺寸（如竖版首帧 1440x2560）。
        """
        payload = {
            "model": self.cfg.model,
            "prompt": prompt,
            "size": size or self.cfg.size,
            "n": self.cfg.n,
            "response_format": self.cfg.response_format,
            "watermark": self.cfg.watermark,
        }
        if seed is not None:
            payload["seed"] = int(seed)
        if reference is not None:
            from engine.ark import to_data_uri
            payload["image"] = to_data_uri(reference)

        last: RetryableError | None = None
        resp = None
        for attempt in range(self.cfg.max_retries + 1):
            try:
                resp = self._post(self.cfg.base_url, payload)
            except RetryableError as e:
                last = e
            else:
                if resp.status_code == 200:
                    return self._parse_b64(resp)
                err = self._classify(resp, model_kind="ARK_MODEL")
                if isinstance(err, FatalError):
                    raise err
                last = err  # type: ignore[assignment]
            if not self._retry_after(resp, attempt):
                break
        raise last or FatalError("图片生成失败（内部错误）")

    # ------------------------------------------------------------ 内部
    def _parse_b64(self, resp) -> bytes:
        try:
            data = resp.json()
            b64 = data["data"][0]["b64_json"]
        except (ValueError, KeyError, IndexError, TypeError):
            raise FatalError(f"响应缺少 b64_json，响应原文: {resp.text[:300]}")
        return base64.b64decode(b64)
