# -*- coding: utf-8 -*-
"""人不变人脸校验 —— insightface ArcFace（buffalo_l），自包含，可共享。

- 模型：默认 root=None → insightface 首次使用**自动下载** buffalo_l 到 ~/.insightface；
  已有模型时可设 INSIGHTFACE_ROOT 指到**含 models/buffalo_l/ 的目录**（insightface 布局是
  `{root}/models/{name}/`；设成 auto/ 就能复用 auto/models/buffalo_l/，不会触发下载）。
- 取图中最大人脸，用 normed_embedding 做余弦相似度。
- 三档判定：score ≥ pass 归档 ｜ ≥ warn 存疑待人工 ｜ < warn 串味进 rejected；无脸也判拒（人不变无法确认）。
- CPU / GPU 自动；校验线程安全（共享同一模型实例，embedding 互斥）。
- insightface / onnxruntime 未安装时初始化抛 ValidatorError，由调用方降级为「未校验」。
"""

from __future__ import annotations

import os
import threading
from pathlib import Path

import numpy as np

from config import Config


class ValidatorError(Exception):
    pass


class FaceValidator:
    def __init__(self, cfg: Config):
        self._lock = threading.Lock()
        self.app = None
        try:
            import insightface  # noqa: F401
        except ImportError:
            raise ValidatorError(
                "未安装 insightface。先 pip install insightface==0.7.3 --prefer-binary"
            )
        self._init_app(cfg)

    def _init_app(self, cfg: Config) -> None:
        import insightface

        provider_set = self._pick_providers(cfg.provider)
        root = cfg.insightface_root or None  # None → insightface 自动下载到 ~/.insightface
        ctx = 0 if "CUDAExecutionProvider" in provider_set else -1
        try:
            app = insightface.app.FaceAnalysis(
                name="buffalo_l", root=root, providers=provider_set
            )
            app.prepare(ctx_id=ctx, det_size=(640, 640))
            self.app = app
            self.provider = "CUDA" if "CUDAExecutionProvider" in provider_set else "CPU"
        except Exception as e:
            # 兜底 CPU
            try:
                app = insightface.app.FaceAnalysis(
                    name="buffalo_l", root=root, providers=["CPUExecutionProvider"]
                )
                app.prepare(ctx_id=-1, det_size=(640, 640))
                self.app = app
                self.provider = "CPU(兜底)"
            except Exception as e2:
                raise ValidatorError(
                    f"加载 buffalo_l 模型失败: {e2}\n"
                    "首次使用会自动下载；也可设 INSIGHTFACE_ROOT 指向含 models/buffalo_l/ 的"
                    "目录（insightface 布局是 {root}/models/{name}/）"
                )

    @staticmethod
    def _pick_providers(provider: str) -> list:
        if provider == "cpu":
            return ["CPUExecutionProvider"]
        try:
            import onnxruntime as ort

            if "CUDAExecutionProvider" in ort.get_available_providers():
                return ["CUDAExecutionProvider", "CPUExecutionProvider"]
        except Exception:
            pass
        return ["CPUExecutionProvider"]

    # ------------------------------------------------------------ 计算
    def embedding(self, img_bytes: bytes) -> np.ndarray | None:
        """返回 normed 人脸嵌入；无脸 / 坏图返回 None。线程安全。"""
        with self._lock:
            import cv2

            img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                return None
            faces = self.app.get(img)
            if not faces:
                return None
            best = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
            return best.normed_embedding

    def similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b))  # 均为 normed → 点积即余弦

    def score_file(self, img_path: Path, baseline_path: Path) -> float | None:
        """返回候选图对基准图的相似度；任一无脸返回 None。"""
        try:
            emb = self.embedding(Path(img_path).read_bytes())
            base = self.embedding(Path(baseline_path).read_bytes())
        except OSError as e:
            raise ValidatorError(f"读取图片失败 {e}")
        if emb is None or base is None:
            return None
        return self.similarity(emb, base)

    # ------------------------------------------------------------ 视频抽帧（图生视频「人不变」校验）
    def extract_frame(self, video_path: Path, frac: float, out_path: Path) -> Path | None:
        """按播放进度 frac(0~1) 抽一帧存到 out_path（视频「人不变」用）。

        cv2.imwrite 对中文路径会失败，故用 imencode + numpy.tofile 落盘。
        成功返回 out_path，失败返回 None。
        """
        import cv2

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return None
        try:
            total = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            idx = min(int(total * frac), max(int(total) - 1, 0))
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if not ok:
                return None
            ok2, buf = cv2.imencode(".png", frame)
            if not ok2:
                return None
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            buf.tofile(str(out_path))
            return Path(out_path)
        finally:
            cap.release()
