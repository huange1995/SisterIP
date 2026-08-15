# -*- coding: utf-8 -*-
"""镜头脚本 shotlist（导演层，自包含，可共享）：声明式镜头单 + 校验 + 确定性时序。

一个脚本 = 一条成片。三种镜头源：
- images   本地图集目录 → montage 连帧（零成本；每镜时长 per × 张数）
- image    单张图 → 单镜 Ken Burns（零成本）
- seedance Seedance 图生视频（付费；prompt 内可写 "Shot 1: … / Shot 2: …" 一次出 2-3 镜）

audio 段：bgm 曲目 + 每镜旁白（voiceover，引用 scene id）。

示例：
  {"title":"深夜爵士","ratio":"9:16","fps":24,
   "scenes":[
     {"id":"s1","src":"images","dir":"栏目图/换装秀","per":2.5,"cuts":"hard","cam":"pan","text":"夜晚归她管"},
     {"id":"s2","src":"seedance","base":"定妆照/A-黛眉/A-黛眉.png",
      "prompt":"Shot 1: 侧身回眸 发丝微扬 / Shot 2: 指尖划过杯沿 眼神上挑","dur":10,
      "firstframe":"derive","ff_prompt":"9:16 竖版写真","text":"三点后的爵士"}],
   "audio":{"bgm":"深夜爵士.mp3","bgm_volume":0.5,
     "voiceover":[{"scene":"s2","text":"夜晚归她管，酒杯映着眼里的灯"}]}}
"""

from __future__ import annotations

from dataclasses import dataclass

SCENE_SRCS = ("images", "image", "seedance")


class ShotListError(ValueError):
    """镜头脚本不合法（缺字段 / 引用不存在 / src 非法）。"""


# ---------------------------------------------------------------- 解析 + 校验
def parse(data: dict) -> dict:
    """校验并规范化脚本（补默认值）；非法抛 ShotListError。"""
    title = str(data.get("title") or "").strip()
    if not title:
        raise ShotListError("镜头脚本缺 title")
    raw_scenes = data.get("scenes") or []
    if not raw_scenes:
        raise ShotListError("镜头脚本 scenes 为空")

    seen: set[str] = set()
    scenes = []
    for i, sc in enumerate(raw_scenes, 1):
        if not isinstance(sc, dict):
            raise ShotListError(f"第 {i} 个 scene 不是对象")
        sid = str(sc.get("id") or f"s{i}")
        if sid in seen:
            raise ShotListError(f"scene id 重复: {sid}")
        seen.add(sid)

        src = sc.get("src")
        if src not in SCENE_SRCS:
            raise ShotListError(f"scene {sid} 的 src 必须是 {'/'.join(SCENE_SRCS)}")
        s = dict(sc)
        s["id"] = sid
        if src == "images":
            if not s.get("dir"):
                raise ShotListError(f"scene {sid}（images）缺 dir")
            s.setdefault("per", 2.5)
            s.setdefault("cuts", "dissolve")
            s.setdefault("cam", "alternate")
        elif src == "image":
            if not s.get("base"):
                raise ShotListError(f"scene {sid}（image）缺 base")
            s.setdefault("dur", 5.0)
        else:  # seedance
            if not s.get("base"):
                raise ShotListError(f"scene {sid}（seedance）缺 base")
            if not s.get("prompt"):
                raise ShotListError(f"scene {sid}（seedance）缺 prompt（动作；多镜写 Shot N:）")
            s.setdefault("dur", 5.0)
            s.setdefault("firstframe", "derive")
        scenes.append(s)

    audio = data.get("audio") or {}
    voiceover = []
    for vo in audio.get("voiceover") or []:
        if vo.get("scene") not in seen:
            raise ShotListError(f"voiceover 引用不存在的 scene: {vo.get('scene')}")
        voiceover.append({"scene": vo["scene"], "text": str(vo.get("text") or "")})

    return {
        "title": title,
        "ratio": str(data.get("ratio") or "9:16"),
        "fps": int(data.get("fps") or 24),
        "scenes": scenes,
        "audio": {
            "bgm": audio.get("bgm"),
            "bgm_volume": audio.get("bgm_volume"),
            "voiceover": voiceover,
        },
    }


# ---------------------------------------------------------------- 时序（确定性）
def scene_duration(sc: dict, images: int | None = None) -> float:
    """单镜默认时长（秒）。images 源 = per × 张数（需给定 images 数量）。"""
    if sc["src"] == "images":
        return max(0.0, sc["per"] * (images or 1))
    return float(sc["dur"])


def resolve_timing(parsed: dict, image_counts: dict[str, int]) -> list[dict]:
    """按场景顺序排时间轴，返回 [{"scene":…, "start": 秒, "dur": 秒}, …]。

    image_counts: scene_id → 该镜 images 源实际张数（images 镜时长依赖它）。
    结果确定性：同脚本 + 同图集 → 同一时间轴（SRT / 旁白 delay 都基于它）。
    """
    t = 0.0
    plan = []
    for sc in parsed["scenes"]:
        d = scene_duration(sc, images=image_counts.get(sc["id"]))
        plan.append({"scene": sc, "start": t, "dur": d})
        t += d
    return plan


# ---------------------------------------------------------------- 派生
def subtitle_cards(plan: list[dict]) -> list[tuple[float, float, str]]:
    """plan → [(开始, 结束, 文案)]，只取带 text 的镜。"""
    return [
        (p["start"], p["start"] + p["dur"], p["scene"]["text"])
        for p in plan if p["scene"].get("text")
    ]


@dataclass
class SceneStats:
    """成本统计（seedance 镜才计费，images/image 零成本）。"""
    n_paid: int = 0
    paid_seconds: float = 0.0
    n_free: int = 0


def cost_stats(parsed: dict, image_counts: dict[str, int]) -> SceneStats:
    st = SceneStats()
    for sc in parsed["scenes"]:
        if sc["src"] == "seedance":
            st.n_paid += 1
            st.paid_seconds += scene_duration(sc)
        else:
            st.n_free += 1
    return st
