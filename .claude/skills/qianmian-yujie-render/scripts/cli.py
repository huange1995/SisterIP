# -*- coding: utf-8 -*-
"""CLI 装配与分发：子命令注册表 + argparse + 统一错误处理。

新增子命令：在 scripts/commands/ 下加模块（实现 cmd_* + register），
并在下方 import 列表登记即可，不改本文件其它部分。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from config import load_config
from engine.errors import GeneratorError

# 技能根：.claude/skills/qianmian-yujie-render/
SKILL_ROOT = Path(__file__).resolve().parent.parent


def _setup_utf8_console() -> None:
    """Windows 控制台默认 GBK/cp936，直接 print 中文/emoji/¥ 会 UnicodeEncodeError；
    统一把 stdout/stderr 重配置为 UTF-8，并 errors=replace 兜底。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _load_env() -> None:
    """加载 scripts/.env（ARK_API_KEY 等）。没装 python-dotenv 就靠系统环境变量。"""
    try:
        from dotenv import load_dotenv

        load_dotenv(SKILL_ROOT / "scripts" / ".env", override=False)
    except ImportError:
        pass


def main() -> int:
    _setup_utf8_console()
    _load_env()
    parser = argparse.ArgumentParser(
        prog="generate.py",
        description="千面御姐·顾遥 出图/出视频：选型(候选)→确认(锁基准)→衍生(图生图·人不变)→视频(montage 合成 / Seedance 图生视频)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # 子命令注册：commands/ 每模块一个 register(sub)
    from commands import image, montage, video
    for mod in (image, montage, video):
        mod.register(sub)

    args = parser.parse_args()
    try:
        cfg = load_config()
        return args.fn(args, cfg)
    except GeneratorError as e:
        print(f"错误：{e}")
        return 2
    except Exception as e:
        print(f"未预期错误（{type(e).__name__}）：{e}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
