# -*- coding: utf-8 -*-
"""生成器通用错误（图片 / 视频引擎共用，自包含，可共享）。"""


class GeneratorError(Exception):
    """生成失败基类。"""


class RetryableError(GeneratorError):
    """可重试：429 限流 / 5xx / 网络 / 超时。"""


class FatalError(GeneratorError):
    """不可重试：401 / 404 / 400 / 配额。"""


class FFmpegError(GeneratorError):
    """本地 ffmpeg 加工失败（concat / 混音 / 封装 / 盖字卡）。"""


class TTSUnavailableError(GeneratorError):
    """TTS 未配置或调用失败；compose 捕获后降级为跳过旁白并警告。"""
