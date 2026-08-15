#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""千面御姐·顾遥 脚本入口（自包含，可共享）。

真实实现见 scripts/cli.py（CLI 装配/注册表）、scripts/commands/（各子命令）、
scripts/engine/（图片 Seedream / 视频 Seedance 引擎）。本文件只负责把本目录
放进 sys.path 并调用 cli.main()，保证从任何 CWD 运行都能 import 到包内模块。

用法：
  python scripts/generate.py candidates --prompt "<完整提示词>" --n 4 [--tag 形象A] [--dry-run]
  python scripts/generate.py pick <候选文件或目录> [<文件名>] [--name 形象A-黛眉]
  python scripts/generate.py derive --base <基准图.png> --prompt "<衍生提示词>" [--kind 三视图|栏目图] [--tag 女仆装] [--n 1] [--no-validate] [--dry-run]
  python scripts/generate.py montage --dir <图集目录> [--tag 换装秀] [--per 2.5] [--dry-run]
  python scripts/generate.py video --base <基准图.png> --prompt "<动作描述>" [--tag 深夜爵士] [--ratio 9:16] [--firstframe crop|derive] [--dry-run]
  python scripts/generate.py status
"""

from __future__ import annotations

import sys
from pathlib import Path

# 让本文件能 import 同目录的 config/archive/pipeline/engine/commands（无论从哪个 CWD 运行）
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
