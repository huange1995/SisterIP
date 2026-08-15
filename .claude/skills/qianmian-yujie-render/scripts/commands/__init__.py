# -*- coding: utf-8 -*-
"""子命令包：每模块一个 register(sub)，向 argparse 注册一个或多个子命令。

新增子命令三步：
  1. 在 commands/ 新建 <name>.py，实现 cmd_*(args, cfg)->int 与 register(sub)
  2. 在 cli.py main() 的 import 列表里加入该模块（或用下方 ALL 自动收集）
  3. 产物桶如需新类型 → archive.py bucket + references/产物.md
"""
