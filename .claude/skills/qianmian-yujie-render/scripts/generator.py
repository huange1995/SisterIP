# -*- coding: utf-8 -*-
"""Seedream 生成器（自包含，可共享）。

已核实的接口事实（2026-08，火山方舟 ark.cn-beijing.volces.com）：
- 端点 POST {base_url}，Authorization: Bearer {KEY}，OpenAI Images 兼容
- 参考图本地文件必须转 Data URI：data:image/png;base64,...（格式须小写）
- 官方无 negative_prompt 字段 → 负面约束已在提示词里拼进文本（SKILL.md 组装阶段完成）
- seed 为遗留参数，新版模型会忽略；此处仅用于跟踪 / 换种重试
"""

from __future__ import annotations

import base64
import mimetypes
import os
import random
import time
from pathlib import Path

from config import Config


class GeneratorError(Exception):
    """生成失败基类。"""


class RetryableError(GeneratorError):
    """可重试：429 限流 / 5xx / 网络 / 超时。"""


class FatalError(GeneratorError):
    """不可重试：401 / 404 / 400 / 配额。"""


class SeedreamGenerator:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        if not cfg.api_key:
            raise GeneratorError(
                "未设置 ARK_API_KEY：把 scripts/.env.example 复制为 scripts/.env 并填入你的火山方舟密钥"
            )

    def generate_one(self, prompt: str, reference: Path | None = None,
                     seed: int | None = None) -> bytes:
        """生成一张图，返回图片 bytes（PNG/JPEG）。reference 为基准图路径（图生图）。"""
        # 延迟导入：没装 requests 时也能 import 本模块（dry-run / status 可用）
        import requests

        payload = {
            "model": self.cfg.model,
            "prompt": prompt,
            "size": self.cfg.size,
            "n": self.cfg.n,
            "response_format": self.cfg.response_format,
            "watermark": self.cfg.watermark,
        }
        if seed is not None:
            payload["seed"] = int(seed)
        if reference is not None:
            payload["image"] = self._data_uri(reference)

        headers = {
            "Authorization": f"Bearer {self.cfg.api_key}",
            "Content-Type": "application/json",
        }

        last: GeneratorError | None = None
        session = requests.Session()
        for attempt in range(self.cfg.max_retries + 1):
            try:
                resp = session.post(
                    self.cfg.base_url, json=payload, headers=headers,
                    timeout=self.cfg.timeout,
                )
            except requests.RequestException as e:
                last = RetryableError(f"网络错误: {e}")
            else:
                if resp.status_code == 200:
                    return self._parse_b64(resp)
                last = self._classify(resp)
                if isinstance(last, FatalError):
                    raise last

            if attempt < self.cfg.max_retries:
                retry_after = None
                if "resp" in locals() and resp.status_code == 429:
                    ra = resp.headers.get("Retry-After")
                    if ra and ra.isdigit():
                        retry_after = float(ra)
                self._sleep(attempt, retry_after)
                continue
            raise last  # type: ignore[misc]

        raise last  # 不可达，防御

    # ------------------------------------------------------------ 内部
    def _parse_b64(self, resp) -> bytes:
        try:
            data = resp.json()
            b64 = data["data"][0]["b64_json"]
        except (ValueError, KeyError, IndexError, TypeError):
            raise FatalError(f"响应缺少 b64_json，响应原文: {resp.text[:300]}")
        return base64.b64decode(b64)

    def _classify(self, resp) -> GeneratorError:
        body = resp.text[:300]
        code = resp.status_code
        if code == 429:
            return RetryableError(f"429 限流: {body}")
        if code == 401:
            return FatalError(f"401 认证失败，检查 ARK_API_KEY: {body}")
        if code == 404:
            return FatalError(
                f"404 端点/模型不存在，检查 ARK_MODEL 是否已开通: {body}"
            )
        if code == 400:
            return FatalError(f"400 请求参数错误: {body}")
        if 500 <= code < 600:
            return RetryableError(f"{code} 服务端错误: {body}")
        return FatalError(f"{code} 未知错误: {body}")

    def _sleep(self, attempt: int, fixed: float | None = None) -> None:
        if fixed is not None:
            time.sleep(min(fixed, 60.0))
        else:
            base = self.cfg.retry_backoff * (2 ** attempt)
            time.sleep(min(base + random.uniform(0, 1.0), 60.0))

    def _data_uri(self, path: Path) -> str:
        p = Path(path)
        raw = p.read_bytes()
        if len(raw) > 30 * 1024 * 1024:
            raise GeneratorError(f"参考图超过 30MB: {p}")
        mime = mimetypes.guess_type(p.name)[0] or "image/png"
        return f"data:{mime};base64," + base64.b64encode(raw).decode()
