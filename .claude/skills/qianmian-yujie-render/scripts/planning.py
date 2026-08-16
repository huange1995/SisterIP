# -*- coding: utf-8 -*-
"""企划书 planning（策划层，自包含，可共享）：企划书 → 渲染契约 + 逐镜 prompt。

三层骨架的「① 策划层」。企划书 = 创意产物（AI 编辑生成 + 手工精修），produce 命令
读它，**纯本地零 API** 展开成：
- 渲染契约（shotlist，compose 消费）   expand_contract()
- 逐镜完整 prompt（黄金公式拼装，供审查） build_design_prompt() / build_seedance_prompts()
- 创意预览（文案/镜头/音乐/连贯规则）   creative_preview()

企划书 schema 一句话：概念(concept) + 角色服装(cast) + 文案原子(copy) + 镜头原子(shots)
+ 音乐(music) + 连贯性(coherence)。每镜的姿势/场景/质量等原子文本**自包含**在企划书里，
不解析配方库 markdown（编辑器负责从配方库挑好原子文本填进来）。
"""

from __future__ import annotations

SCENE_SRCS = ("images", "image", "seedance")
COPY_MODES = ("subtitle", "voiceover")
SHOT_ROLES = ("establish", "detail", "hook")  # 镜头功能：定调 / 细节 / 收尾钩子
DEFAULT_NEGATIVE = "低质量，模糊，五官变形，多余手指，文字水印"


class BriefError(ValueError):
    """企划书不合法（缺字段 / 引用不存在 / src 非法）。"""


# ---------------------------------------------------------------- 解析 + 校验
def parse(data: dict) -> dict:
    """校验并规范化企划书（补默认值）；非法抛 BriefError。"""
    title = str(data.get("title") or "").strip()
    if not title:
        raise BriefError("企划书缺 title")

    cast = data.get("cast") or {}
    outfits = []
    for i, o in enumerate(cast.get("outfits") or [], 1):
        if not isinstance(o, dict) or not o.get("name"):
            raise BriefError(f"cast.outfits 第 {i} 项缺 name")
        if not o.get("dir") and not o.get("prompt"):
            raise BriefError(f"服装 {o['name']} 至少要给 dir 或 prompt 之一")
        outfits.append({"name": o["name"], "dir": o.get("dir"), "prompt": o.get("prompt")})
    cast = {
        "anchor": cast.get("anchor"),
        "anchor_prompt": str(cast.get("anchor_prompt") or ""),
        "outfits": outfits,
        "light": cast.get("light"),
    }

    concept = data.get("concept") or {}
    concept = {
        "pitch": concept.get("pitch"),
        "mood": concept.get("mood") or [],
        "audience": concept.get("audience"),
        "style_ref": concept.get("style_ref"),
        "negative": concept.get("negative"),
    }

    shot_ids: set[str] = set()
    raw_shots = data.get("shots") or []
    if not raw_shots:
        raise BriefError("企划书 shots 为空")
    shots = []
    for i, sh in enumerate(raw_shots, 1):
        if not isinstance(sh, dict):
            raise BriefError(f"第 {i} 个 shot 不是对象")
        sid = str(sh.get("id") or f"s{i}")
        if sid in shot_ids:
            raise BriefError(f"shot id 重复: {sid}")
        shot_ids.add(sid)
        src = sh.get("src")
        if src not in SCENE_SRCS:
            raise BriefError(f"shot {sid} 的 src 必须是 {'/'.join(SCENE_SRCS)}")
        if sh.get("role") and sh["role"] not in SHOT_ROLES:
            raise BriefError(f"shot {sid} 的 role 必须是 {'/'.join(SHOT_ROLES)}")
        if src == "images" and not sh.get("dir") and not sh.get("outfit"):
            raise BriefError(f"shot {sid}（images）缺 dir 或 outfit")
        if src in ("image", "seedance") and not sh.get("base"):
            raise BriefError(f"shot {sid}（{src}）缺 base")
        if src == "seedance" and not (sh.get("pose") or sh.get("motion") or sh.get("action")):
            raise BriefError(f"shot {sid}（seedance）缺 pose/motion/action（动作）")
        shots.append(dict(sh))

    copy = []
    copy_ids: set[str] = set()
    for i, c in enumerate(data.get("copy") or [], 1):
        cid = str(c.get("id") or f"c{i}")
        if cid in copy_ids:
            raise BriefError(f"copy id 重复: {cid}")
        copy_ids.add(cid)
        mode = c.get("mode", "subtitle")
        if mode not in COPY_MODES:
            raise BriefError(f"copy {cid} 的 mode 必须是 {'/'.join(COPY_MODES)}")
        if c.get("scene") and c["scene"] not in shot_ids:
            raise BriefError(f"copy {cid} 引用不存在的 shot: {c['scene']}")
        copy.append({"id": cid, "text": str(c.get("text") or ""), "mode": mode,
                     "tone": c.get("tone"), "scene": c.get("scene")})
    for sh in shots:
        if sh.get("copy") and sh["copy"] not in copy_ids:
            raise BriefError(f"shot {sh['id']} 引用不存在的 copy: {sh['copy']}")
        if sh.get("continue_from") and sh["continue_from"] not in shot_ids:
            raise BriefError(f"shot {sh['id']} 的 continue_from 引用不存在的 shot: {sh['continue_from']}")

    music = data.get("music") or {}
    coherence = data.get("coherence") or {}
    return {
        "title": title,
        "ratio": str(data.get("ratio") or "9:16"),
        "fps": int(data.get("fps") or 24),
        "concept": concept,
        "cast": cast,
        "copy": copy,
        "shots": shots,
        "music": {"bgm": music.get("bgm"), "volume": music.get("volume"), "mood": music.get("mood")},
        "coherence": {"face": coherence.get("face"), "grade": coherence.get("grade")},
    }


# ---------------------------------------------------------------- 原子引用
def _outfit(plan: dict, sh: dict) -> dict | None:
    """按 shot.outfit 名字查 cast.outfits；未命中抛 BriefError。"""
    if not sh.get("outfit"):
        return None
    for o in plan["cast"]["outfits"]:
        if o["name"] == sh["outfit"]:
            return o
    raise BriefError(f"shot {sh['id']} 引用的服装不在 cast.outfits: {sh['outfit']}")


def _copy(plan: dict, cid: str) -> dict:
    for c in plan["copy"]:
        if c["id"] == cid:
            return c
    raise BriefError(f"copy 引用不存在: {cid}")


# ---------------------------------------------------------------- 逐镜 prompt（黄金公式）
def build_design_prompt(plan: dict, sh: dict) -> str:
    """完整画面设计提示词（审查用）：[服装]+[姿势]+[场景]+[质量]+[风格基调]+[光线]+[负面词]。

    衍生（成片渲染路径）用基准图提供脸，不拼形象锚点；仅 sh.use_anchor=true 时前置锚点。
    """
    cast, concept = plan["cast"], plan["concept"]
    chunk: list[str] = []
    if sh.get("use_anchor") and cast["anchor_prompt"]:
        chunk.append(cast["anchor_prompt"])
    if sh.get("outfit"):
        o = _outfit(plan, sh)
        if o and o.get("prompt"):
            chunk.append(o["prompt"])
    for k in ("pose", "scene", "quality"):
        if sh.get(k):
            chunk.append(sh[k])
    if concept.get("style_ref"):
        chunk.append(concept["style_ref"])
    if cast.get("light"):
        chunk.append(cast["light"])
    neg = sh.get("negative") or concept.get("negative") or DEFAULT_NEGATIVE
    return "，".join(chunk) + f"；9:16 竖版写真；{neg}"


def build_seedance_prompts(plan: dict, sh: dict) -> tuple[str, str]:
    """seedance 镜 → (动作 prompt, 首帧 ff_prompt)。

    - 动作：优先 sh.action 原样透传；否则拼 `Shot 1: {pose}，{motion}`（多镜可手写 Shot N:）。
    - 首帧（derive）：黄金公式描述该镜画面，供 Seedream 以 base 为参考生成竖版首帧。
    """
    action = (sh.get("action") or "").strip()
    if not action:
        parts = [p for p in (sh.get("pose"), sh.get("motion")) if p]
        action = "，".join(parts) if parts else sh["base"]
        if parts:
            action = "Shot 1: " + action
    return action, build_design_prompt(plan, sh)


# ---------------------------------------------------------------- 展开 → 渲染契约
def expand_contract(plan: dict) -> dict:
    """企划书 → 渲染契约 shotlist（compose 直接消费；现有 shotlist.parse 兼容）。"""
    scenes = []
    vo = []
    for sh in plan["shots"]:
        text = None
        if sh.get("copy"):
            c = _copy(plan, sh["copy"])
            if c["mode"] == "voiceover":
                vo.append({"scene": sh["id"], "text": c["text"]})
            else:
                text = c["text"]
        if sh["src"] == "images":
            outfit = _outfit(plan, sh)
            scenes.append({
                "id": sh["id"], "src": "images",
                "dir": sh.get("dir") or outfit["dir"],
                "per": sh.get("per", 2.5), "cuts": sh.get("cuts", "dissolve"),
                "cam": sh.get("cam", "alternate"),
                **({"text": text} if text else {}),
            })
        elif sh["src"] == "image":
            scenes.append({
                "id": sh["id"], "src": "image", "base": sh["base"],
                "dur": sh.get("dur", 5.0), "cam": sh.get("cam", "zoom-in"),
                **({"text": text} if text else {}),
            })
        else:  # seedance
            action, ff = build_seedance_prompts(plan, sh)
            sc = {
                "id": sh["id"], "src": "seedance", "base": sh["base"],
                "prompt": action, "dur": sh.get("dur", 5.0),
                "firstframe": "derive", "ff_prompt": ff,
                **({"text": text} if text else {}),
            }
            if sh.get("continue_from"):
                sc["continue_from"] = sh["continue_from"]
            scenes.append(sc)

    contract = {
        "title": plan["title"],
        "ratio": plan["ratio"],
        "fps": plan["fps"],
        "scenes": scenes,
        "audio": {"bgm": plan["music"]["bgm"], "bgm_volume": plan["music"]["volume"],
                  "voiceover": vo},
    }
    grade = plan["coherence"].get("grade")
    if grade:
        contract["grade"] = grade
    return contract


# ---------------------------------------------------------------- 创意预览（评审）
def creative_preview(plan: dict) -> str:
    """企划书 → 多行创意预览（文案全文 / 镜头表 / 音乐 / 连贯规则）。"""
    c, cast, music, co = plan["concept"], plan["cast"], plan["music"], plan["coherence"]
    L = [f"企划「{plan['title']}」· {plan['ratio']} · {plan['fps']}fps · 角色 {cast.get('anchor')}"]
    if c["pitch"]:
        L.append(f"  立意：{c['pitch']}")
    if c["mood"] or c["audience"]:
        L.append(f"  情绪：{'/'.join(c['mood']) if c['mood'] else '-'}　受众：{c['audience'] or '-'}")
    if c["style_ref"]:
        L.append(f"  风格基调：{c['style_ref']}")
    L.append("  文案：")
    if plan["copy"]:
        for cp in plan["copy"]:
            L.append(f"    [{cp['id']}] {cp['mode']}·{cp['tone'] or '-'} → scene {cp['scene'] or '-'}：{cp['text']}")
    else:
        L.append("    （无）")
    L.append("  镜头：")
    for sh in plan["shots"]:
        loc = sh.get("outfit") or sh.get("base") or sh.get("dir") or ""
        cf = f" 接续{sh['continue_from']}" if sh.get("continue_from") else ""
        L.append(f"    [{sh['id']}] {sh.get('role') or '-'} {sh['src']} {loc}"
                 f" cam={sh.get('cam') or '-'} dur={sh.get('dur') or sh.get('per')}s{cf}"
                 f"（{sh.get('pose') or sh.get('motion') or ''}）")
    L.append(f"  音乐：{music['bgm'] or '（无）'} vol={music['volume'] or '-'} mood={music['mood'] or '-'}")
    L.append(f"  连贯：{co['face'] or '-'}　统一调色：{co['grade'] or '无'}")
    return "\n".join(L)
