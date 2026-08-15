# -*- coding: utf-8 -*-
"""火山方舟 HTTP 客户端基类（图片 / 视频引擎共用，自包含，可共享）。

收敛三处重复：Bearer+JSON headers 与 requests.Session、错误分类 _classify、
指数退避 _sleep。新接方舟能力（如 TTS/ASR）时继承本类即可。
"""

from __future__ import annotations

import base64
import mimetypes
import random
import time
from pathlib import Path

import requests

from config import Config
from engine.errors import FatalError, GeneratorError, RetryableError

# 参考图 Data URI 上限（火山方舟要求本地文件转 base64 引用）
MAX_REF_IMAGE_BYTES = 30 * 1024 * 1024


def to_data_uri(path: Path) -> str:
    """本地图片 → data:image/xxx;base64,...（火山方舟用 Data URI 引用参考图）。"""
    p = Path(path)
    raw = p.read_bytes()
    if len(raw) > MAX_REF_IMAGE_BYTES:
        raise GeneratorError(f"参考图超过 30MB: {p}")
    mime = mimetypes.guess_type(p.name)[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(raw).decode()


class ArkClientBase:
    """方舟 HTTP 客户端基类：统一鉴权、请求、错误分类、退避。"""

    # service_name 用于错误文案（如「图片」「视频」）
    def __init__(self, cfg: Config, service_name: str = "方舟"):
        self.cfg = cfg
        self.service_name = service_name
        if not cfg.api_key:
            raise GeneratorError(
                "未设置 ARK_API_KEY：把 scripts/.env.example 复制为 scripts/.env 并填入你的火山方舟密钥"
            )
        self.session = requests.Session()
        self.headers = {
            "Authorization": f"Bearer {cfg.api_key}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------ 请求
    def _post(self, url: str, payload: dict, timeout: float | None = None) -> requests.Response:
        try:
            return self.session.post(
                url, json=payload, headers=self.headers,
                timeout=timeout or self.cfg.timeout,
            )
        except requests.RequestException as e:
            raise RetryableError(f"{self.service_name}网络错误: {e}")

    def _get(self, url: str, timeout: float | None = None) -> requests.Response:
        try:
            return self.session.get(
                url, headers=self.headers, timeout=timeout or self.cfg.timeout,
            )
        except requests.RequestException as e:
            raise RetryableError(f"{self.service_name}网络错误: {e}")

    # ------------------------------------------------------------ 错误分类 / 退避
    def _classify(self, resp: requests.Response, model_kind: str = "模型") -> GeneratorError:
        """把 HTTP 状态码转成 GeneratorError（429/5xx→可重试，其余→致命）。"""
        body = resp.text[:300]
        code = resp.status_code
        if code == 429:
            return RetryableError(f"429 限流: {body}")
        if code == 401:
            return FatalError(f"401 认证失败，检查 ARK_API_KEY: {body}")
        if code == 404:
            return FatalError(
                f"404 端点/模型不存在，检查 {model_kind} 是否已开通: {body}"
            )
        if code == 400:
            return FatalError(f"400 请求参数错误: {body}")
        if 500 <= code < 600:
            return RetryableError(f"{code} 服务端错误: {body}")
        return FatalError(f"{code} 未知错误: {body}")

    def _sleep(self, attempt: int, fixed: float | None = None) -> None:
        """指数退避；fixed 优先（如 429 的 Retry-After）。"""
        if fixed is not None:
            time.sleep(min(fixed, 60.0))
        else:
            base = self.cfg.retry_backoff * (2 ** attempt)
            time.sleep(min(base + random.uniform(0, 1.0), 60.0))

    def _retry_after(self, resp: requests.Response | None, attempt: int) -> bool:
        """重试前 sleep。返回 True=已 sleep（可重试），False=已达上限（应放弃）。"""
        if attempt >= self.cfg.max_retries:
            return False
        fixed = None
        if resp is not None and resp.status_code == 429:
            v = resp.headers.get("Retry-After")
            if v and v.isdigit():
                fixed = float(v)
        self._sleep(attempt, fixed)
        return True
