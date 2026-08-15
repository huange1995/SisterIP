# -*- coding: utf-8 -*-
"""火山语音 TTS（自包含，可共享）：http 非流式 v1 同步接口，一段旁白 → mp3。

- 鉴权：火山语音 AppID + Access Token（与 ARK_API_KEY 无关）。未配置 → TTSUnavailableError，
  compose 捕获后降级为跳过旁白并明确警告（同 Seedance 未开通的降级模式）。
- 每次合成 reqid 必须唯一（UUID）。
- 成本：个人普通音色免费 1000 次/3 月，后付约 ¥5/万字符。
- 失败会缓存（_fail_reason），同一 compose 内后续旁白不再重复打网。
"""

from __future__ import annotations

import base64
import uuid
from pathlib import Path

import requests

from config import Config
from engine.errors import TTSUnavailableError

TTS_URL = "https://openspeech.bytedance.com/api/v1/tts"


class TTSClient:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._fail_reason: str | None = None
        self.enabled = bool(cfg.tts_appid and cfg.tts_token)

    # ------------------------------------------------------------ 合成
    def synthesize(self, text: str, out_path: Path) -> Path:
        """合成一段旁白 mp3 到 out_path。任何失败抛 TTSUnavailableError（可降级跳过）。"""
        if self._fail_reason:
            raise TTSUnavailableError(self._fail_reason)
        if not self.enabled:
            self._fail_reason = "未配置 ARK_TTS_APPID / ARK_TTS_TOKEN（火山语音控制台申请），跳过旁白"
            raise TTSUnavailableError(self._fail_reason)

        text = text.strip()
        if not text:
            self._fail_reason = "旁白文本为空，跳过"
            raise TTSUnavailableError(self._fail_reason)

        c = self.cfg
        payload = {
            "app": {"appid": c.tts_appid, "token": c.tts_token, "cluster": c.tts_cluster},
            "user": {"uid": "qianmian-yujie"},
            "audio": {
                "voice_type": c.tts_voice,
                "encoding": "mp3",
                "speed_ratio": c.tts_speed_ratio,
                "volume_ratio": c.tts_volume_ratio,
            },
            "request": {
                "reqid": str(uuid.uuid4()),
                "text": text,
                "text_type": "plain",
                "operation": "query",
            },
        }
        headers = {
            "Authorization": f"Bearer;{c.tts_token}",
            "Content-Type": "application/json",
        }

        try:
            resp = requests.post(TTS_URL, json=payload, headers=headers, timeout=c.tts_timeout)
        except requests.RequestException as e:
            self._fail_reason = f"TTS 网络/超时失败（跳过旁白）: {e}"
            raise TTSUnavailableError(self._fail_reason)

        if resp.status_code == 429 or resp.status_code >= 500:
            self._fail_reason = f"TTS 服务暂时不可用（HTTP {resp.status_code}），跳过旁白"
            raise TTSUnavailableError(self._fail_reason)
        if resp.status_code != 200:
            self._fail_reason = f"TTS 鉴权/请求失败（HTTP {resp.status_code}），跳过旁白"
            raise TTSUnavailableError(self._fail_reason)

        try:
            body = resp.json()
        except ValueError:
            self._fail_reason = "TTS 响应非 JSON，跳过旁白"
            raise TTSUnavailableError(self._fail_reason)

        if body.get("code") != 3000:
            self._fail_reason = (
                f"TTS 合成失败 code={body.get('code')}: {body.get('message', '')}，跳过旁白"
            )
            raise TTSUnavailableError(self._fail_reason)

        data = body.get("data")
        if not data:
            self._fail_reason = "TTS 响应缺少音频数据，跳过旁白"
            raise TTSUnavailableError(self._fail_reason)

        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(base64.b64decode(data))
        return out_path
